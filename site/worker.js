// Systems from Zero: static site on Cloudflare Workers.
// Every path is served straight from the static assets in web/. Only /video/* runs this script first,
// to answer HTTP range requests: Safari (macOS and iOS) plays an MP4 only from a server that returns
// 206 Partial Content, and range support is what lets every browser seek without downloading the file.

function parseRange(header, size) {
  const m = /^bytes=(\d*)-(\d*)$/.exec((header || "").trim());
  if (!m || (m[1] === "" && m[2] === "")) return null;
  let start, end;
  if (m[1] === "") {
    // suffix range: the last N bytes
    start = Math.max(0, size - Number(m[2]));
    end = size - 1;
  } else {
    start = Number(m[1]);
    end = m[2] === "" ? size - 1 : Math.min(Number(m[2]), size - 1);
  }
  return { start, end };
}

export default {
  async fetch(request, env) {
    if (request.method !== "GET" && request.method !== "HEAD") return env.ASSETS.fetch(request);
    // ask the asset store for the whole file; the slicing happens here
    const res = await env.ASSETS.fetch(new Request(request.url, { method: "GET" }));
    if (res.status !== 200) return res;

    const headers = new Headers(res.headers);
    headers.set("Accept-Ranges", "bytes");
    headers.set("Cache-Control", "public, max-age=86400");
    const range = request.headers.get("Range");
    if (!range) return new Response(request.method === "HEAD" ? null : res.body, { status: 200, headers });

    // the asset store streams without a Content-Length, so read the (at most ~8 MB) video to know its size
    const buf = await res.arrayBuffer();
    const size = buf.byteLength;
    const r = parseRange(range, size);
    if (!r || r.start >= size || r.start > r.end) {
      return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}`, "Accept-Ranges": "bytes" } });
    }
    headers.set("Content-Range", `bytes ${r.start}-${r.end}/${size}`);
    headers.set("Content-Length", String(r.end - r.start + 1));
    if (request.method === "HEAD") return new Response(null, { status: 206, headers });
    return new Response(r.start === 0 && r.end === size - 1 ? buf : buf.slice(r.start, r.end + 1), { status: 206, headers });
  },
};
