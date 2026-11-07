#!/bin/bash
# Render one narrated scene in high resolution and publish it to web/video/.
#   ./render.sh scenes/<file>.py <SceneClass> <slug>        full quality: 2560x1440 at 30 fps
#   QUICK=1 ./render.sh scenes/<file>.py <SceneClass> <slug> a fast 854x480 draft to check timing and layout
# Writes web/video/<slug>.mp4 (H.264, CRF 18, loudness-normalised AAC), <slug>.jpg (poster) and <slug>.vtt (captions).
set -euo pipefail
cd "$(dirname "$0")"
F=$1; S=$2; SLUG=$3
OUT=../web/video
mkdir -p "$OUT" media
if [ -n "${QUICK:-}" ]; then RES=854,480; FPS=15; else RES=2560,1440; FPS=30; fi
log=media/render_$SLUG.log
PYTHONPATH="$PWD" .venv/bin/manim --resolution "$RES" --frame_rate "$FPS" --disable_caching --media_dir media "$F" "$S" > "$log" 2>&1 \
  || { echo "FAIL $SLUG (see videos/$log)"; tail -20 "$log"; exit 1; }
base=$(basename "$F" .py)
H=${RES#*,}
SRC=$(ls -t media/videos/$base/${H}p${FPS}/$S.mp4)
if [ -n "${QUICK:-}" ]; then
  cp "$SRC" "media/$SLUG-draft.mp4"
  echo "draft media/$SLUG-draft.mp4 $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC" | cut -d. -f1)s"
  exit 0
fi
# Crisp text needs a generous bitrate: CRF 18 with the animation tune. Narration is mono speech,
# normalised to -16 LUFS so every video plays at the same loudness.
ffmpeg -loglevel error -y -i "$SRC" \
  -c:v libx264 -preset slow -crf 18 -tune animation -pix_fmt yuv420p -profile:v high -movflags +faststart \
  -af "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000" -c:a aac -b:a 128k -ac 1 "$OUT/$SLUG.mp4"
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/$SLUG.mp4")
# poster: POSTER=<seconds> picks a calm frame with the whole diagram on screen; the default is 82% of the way in
ffmpeg -loglevel error -y -ss "${POSTER:-$(python3 -c "print(round($D*0.82,2))")}" -i "$OUT/$SLUG.mp4" -frames:v 1 -vf scale=1280:-1 -q:v 3 "$OUT/$SLUG.jpg"
cp "captions/$S.vtt" "$OUT/$SLUG.vtt"
echo "$SLUG ${D%.*}s $(du -k "$OUT/$SLUG.mp4" | cut -f1)KB"
