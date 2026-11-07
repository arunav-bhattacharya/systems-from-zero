# Narrated animations

Short narrated videos for the key concepts of the course, in the style of the site's figures: a black
stage, CMU Serif, the Manim palette, and one calm voice explaining one mechanism as it moves. Each video is
60 to 120 seconds and sits at the top of the lesson section it explains.

- **Picture:** 2560x1440 (QHD) at 30 fps, H.264 CRF 18 with the animation tune, so text stays sharp on any screen.
- **Sound:** the Kokoro `af_heart` voice, mono AAC 128 kbps at 48 kHz, loudness-normalised to -16 LUFS.
- **Captions:** a WebVTT file per video, written from the narration as the scene renders.

## Set up once (macOS, Apple Silicon)

```bash
brew install pkgconf cairo ffmpeg
cd videos
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python manim kokoro-onnx soundfile fonttools brotli faster-whisper
mkdir -p models && cd models
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.fp16.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

## Make a video

1. Write `scenes/<name>.py` with one `VoiceScene` subclass (see `scenes/kafka_log.py`). `beat(text, *animations)`
   speaks one line and plays the animations inside it. `sfz.py` has the helpers: `box`, `mbox`, `chip`,
   `arrow`, `edge_arrow`, `travel`, `tick`, `fit`, and the colours `BLUE_M`, `TEAL_M`, `GREEN_M`, `YELLOW_M`,
   `GOLD_M`, `RED_M`, `PURPLE_M`, `GREY_M`.
2. Draft it fast and look at it:

   ```bash
   QUICK=1 ./render.sh scenes/<name>.py <Scene> <slug>
   ffmpeg -loglevel error -y -i media/<slug>-draft.mp4 -vf "fps=1/6,scale=640:-1,tile=3x4:padding=6:color=gray" -frames:v 1 /tmp/<slug>-sheet.png
   ```

3. Render it for real. This writes `../web/video/<slug>.mp4`, `.jpg` (poster) and `.vtt` (captions):

   ```bash
   ./render.sh scenes/<name>.py <Scene> <slug>
   ```

4. Listen to it the way a learner would. Whisper transcribes the narration and compares it with the script;
   anything it hears differently is a word the voice got wrong:

   ```bash
   .venv/bin/python check_audio.py <slug>
   ```

5. List it in `../content/videos.json` (slug, scene, lesson, section index, title). The site build puts the
   player at the top of that section.

## How a good video works

- **One mechanism, built from the problem.** Open on the need ("one consumer handles 500 payments a second; the
  peak is 3,000"), show the simplest idea and where it breaks, then the real design. End on the one sentence the
  learner should keep. Same first-principles rules as the lessons (`../brief/BRIEF.md`).
- **The voice.** Very simple spoken English, short sentences, one idea per line. Say numbers the way people say
  them. Name the actor ("the leader copies the record"). No jargon before its meaning. 10 to 16 beats.
- **The picture.** One persistent diagram that changes, never a slideshow. Highlight what just changed
  (colour or `Indicate`), dim what doesn't matter now. At most about six things on screen at once.
- **Layout.** The frame is about 14.2 by 8 units; keep everything 0.5 units inside it. Text never touches or
  overlaps a line, a box edge or other text. Labels sit on clear space. Check every draft frame.
- **Pronunciation.** `sfz.SAY` maps jargon to how it should be spoken. For a new word, add a rule at the top
  of your scene file (`SAY.insert(0, (r"\bfoo\b", "foo said right"))`) rather than editing `sfz.py`.
