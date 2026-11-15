# Brief for video makers

Repo root: the folder that holds this `videos/` folder. Paths below are relative to the repo root.

## Read first

- `videos/README.md`: the pipeline and what a good video is.
- `videos/sfz.py`: helpers, colours, the `SAY` pronunciation table.
- Two recent scenes as the bar: `videos/scenes/raft.py` and `videos/scenes/cache_stampede.py`.
- `brief/BRIEF.md`, the first-principles and voice sections. Narration follows the same rules: no dashes, no jargon before its meaning, numbers said the way people say them, no stock phrases.
- The lesson you are animating, in `content/lessons/<id>.json`. Match its numbers and its running example (a payments company: merchants, payments, the ledger).

The Python environment and the Kokoro model are already set up in `videos/.venv` and `videos/models`. Don't reinstall.

## Build intuition, not a summary

Each video is 60 to 120 seconds, 10 to 16 beats, on one persistent diagram that changes.

1. Open on a concrete situation from the lesson and a question the viewer can't answer yet ("two refunds hit the same account at once; where does the second one go?").
2. Show the simplest thing that could work, and let the viewer watch it fail, with a number or a visible wrong result.
3. Build the real mechanism step by step. Each beat changes one thing on screen; highlight what changed and dim what doesn't matter now. Slow down at the moment that matters.
4. End on the one sentence the viewer should keep.

Show, don't tell: counts ticking, timelines, before and after, a value moving between boxes. At most about six things on screen at once.

## Lessons learned by earlier video makers

- The voice cache in `videos/voice` is keyed by the written text, so a new `SAY` rule does nothing for a line already synthesized. Delete that line's cached file before re-rendering.
- Manim shows an object that is moved or transformed later in a beat from the start of that beat. Add such objects only when their step starts, so nothing appears early.
- `Indicate` on a filled box can hide its label. Use an outline pulse instead.
- Whisper often mishears homophones (write/right) and spelled-out ids. Fix only real mispronunciations, with a `SAY` rule at the top of your scene file. Don't edit `sfz.py`.

## For each video

1. Write `videos/scenes/<name>.py` with one `VoiceScene` subclass.
2. Draft with `QUICK=1 ./render.sh ...` and inspect a contact sheet of the frames for overlaps, text touching lines and things appearing early. Fix every one.
3. Render for real with `./render.sh scenes/<name>.py <Class> <slug>`. It writes `web/video/<slug>.mp4`, `.jpg` and `.vtt` at 2560x1440.
4. Run `.venv/bin/python check_audio.py <slug>` and fix real mispronunciations.

Render one video at a time: other video makers share this machine. Work efficiently. Don't edit `content/videos.json`, any lesson file or `sfz.py`.

## Final report

Under 200 words. For each video give:

- its slug
- the scene path and class (`scenes/<file>.py:<Class>`)
- the lesson id
- the 0-based section index it belongs at (check `content/videos.json` so you don't pick a section that already has one)
- a title in sentence case
- its duration
- the check_audio result

Mention any video you couldn't finish.
