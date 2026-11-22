"""Set new titles in content/videos.json (keeping its 1-space indent) and print every file a video ships with.
Usage: python3 tools/set_video_titles.py '{"slug": "New title", ...}'   (an empty title keeps the old one)"""
import json, sys
from pathlib import Path
T = json.loads(sys.argv[1])
p = Path("content/videos.json"); raw = p.read_text(); d = json.loads(raw)
files = ["content/videos.json"]
for v in d["videos"]:
    if v["slug"] in T:
        if T[v["slug"]]: v["title"] = T[v["slug"]]
        scene, cls = v["scene"].split(":")
        files += [f"web/video/{v['slug']}.{e}" for e in ("mp4", "jpg", "vtt")]
        files += [f"videos/{scene}", f"videos/captions/{cls}.vtt", f"videos/scripts/{v['slug']}.md"]
missing = [f for f in files if not Path(f).exists()]
if missing: sys.exit("missing: " + " ".join(missing))
p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + ("\n" if raw.endswith("\n") else ""))
print("\n".join(files))
