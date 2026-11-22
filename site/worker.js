// Systems from Zero: static site on Cloudflare Workers.
// Every path is served straight from the static assets in web/. Only /video/* runs this script first.
//
// The MP4s live on GitHub, as files on the "videos" release of the public repo, not in Cloudflare's asset
// store (web/.assetsignore keeps them out of every deploy). GitHub answers range requests but labels every
// download application/octet-stream and as an attachment, and Safari (macOS and iOS) won't play a video
// labelled that way. So this script fetches the video from GitHub, passes the browser's Range header through,
// and answers with the right type. Posters (.jpg) and captions (.vtt) are small and stay in web/video/, so
// captions come from the site's own origin, which <track> needs.

// A remade video replaces its release file under the same URL, so never let Cloudflare cache GitHub's answer
// (it cached an old redirect once and kept serving the replaced file).
const NO_CACHE = { cacheTtl: -1 };
const RELEASE = "https://github.com/arunav-bhattacharya/systems-from-zero/releases/download/videos/";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const name = url.pathname.split("/").pop();
    if (!name.endsWith(".mp4") || !/^[a-z0-9-]+\.mp4$/.test(name)) return env.ASSETS.fetch(request);
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response(null, { status: 405, headers: { Allow: "GET, HEAD" } });
    }

    const upstreamHeaders = {};
    let range = request.headers.get("Range");
    // GitHub's storage refuses suffix ranges ("the last N bytes"), which some players use to read the end of an
    // MP4. Ask for one byte to learn the size, then turn the suffix into an explicit range.
    const suffix = /^bytes=-(\d+)$/.exec((range || "").trim());
    if (suffix) {
      const probe = await fetch(RELEASE + name, { headers: { Range: "bytes=0-0" }, redirect: "follow", cf: NO_CACHE });
      const total = Number((probe.headers.get("Content-Range") || "").split("/")[1]);
      if (!total) return new Response("Video unavailable", { status: 502 });
      range = `bytes=${Math.max(0, total - Number(suffix[1]))}-${total - 1}`;
    }
    if (range) upstreamHeaders["Range"] = range;
    // GitHub redirects to a signed storage URL that changes on every request, so there's nothing to cache by URL.
    const upstream = await fetch(RELEASE + name, { method: request.method, headers: upstreamHeaders, redirect: "follow", cf: NO_CACHE });
    if (upstream.status === 416) {
      const h = { "Accept-Ranges": "bytes" };
      if (upstream.headers.get("Content-Range")) h["Content-Range"] = upstream.headers.get("Content-Range");
      return new Response(null, { status: 416, headers: h });
    }
    if (upstream.status !== 200 && upstream.status !== 206) {
      return new Response(upstream.status === 404 ? "No such video" : "Video unavailable", { status: upstream.status === 404 ? 404 : 502 });
    }

    const headers = new Headers();
    headers.set("Content-Type", "video/mp4");
    headers.set("Accept-Ranges", "bytes");
    // a remade video keeps its URL, so let browsers keep a copy for an hour, not a day
    headers.set("Cache-Control", "public, max-age=3600");
    for (const h of ["Content-Length", "Content-Range", "ETag", "Last-Modified"]) {
      const v = upstream.headers.get(h);
      if (v) headers.set(h, v);
    }
    return new Response(request.method === "HEAD" ? null : upstream.body, { status: upstream.status, headers });
  },
};
