# Task sheet for video makers (the newcomer remakes)

You remake narrated course videos in the venkat-style-video teaching style, for complete newcomers, at 1440p.
Forty-six remakes are already approved and live. Match them. Your prompt lists your videos (slug, scene
file:class, lesson, section index); do them one after another.

## Read first

1. `videos/REMAKE_BRIEF.md`: the rules. It wins over every other brief.
2. Everything it lists: the venkat-style-video skill and its four reference files (load the skill with the Skill
   tool as `venkat-style-video:venkat-style-video`, or read it from disk at the path in REMAKE_BRIEF.md), and
   `videos/MAKER_BRIEF.md` for the pipeline, helpers and Manim traps.
3. Two approved remakes as the bar for arc, pace, layout and helpers: `videos/scripts/derived-data.md` with
   `videos/scenes/derived_data.py`, and `videos/scripts/index-scan.md` with `videos/scenes/index_scan.py`.
4. For each video: the rewritten lesson (`content/lessons/<id>.json`): its `opening`, the section the video is
   attached to, and its `closing`. The video tells that lesson's story with the same running example, numbers
   and analogy. Numbers, rows and outputs on screen must match the lesson's output blocks, steppers and seed data;
   never invent output. A product (Kafka, Redis, Cassandra, Spark...) gets one plain spoken sentence before its
   name carries any weight. On the Caching, Messaging and Stream processing tracks, code on screen is Java and
   Kotlin side by side.

## For each video

1. Write the script to `videos/scripts/<slug>.md` in the script-template format, with beat tags.
2. Replace the scene: same path, same class name.
3. Draft with `QUICK=1 ./render.sh ...`, make a contact sheet, and fix every overlap, clipped text, text touching a
   line, and object appearing before its cue.
4. Render the final at full 1440p (no `QUICK`), with `POSTER=<seconds>` set to the key picture.
5. Run every check in REMAKE_BRIEF.md: full-size frames at the busiest moments, `check_audio.py <slug>` (fix
   real mispronunciations with `SAY` rules at the top of your scene file, deleting the cached line before you
   re-render), and ffprobe, which must print `2560,1440`. Aim for 3 to 5 minutes; never pad.

## Working alongside others

Three other makers share this machine. Render one video at a time yourself, never two at once, and always draft
with `QUICK=1` before a full render. Don't touch lesson files, `content/videos.json`, `sfz.py` or another maker's
scenes. No git commands, and no uploads: the coordinator ships finished videos to the GitHub release. Keep
scratch files in a folder of your own in the session scratchpad. If the coordinator sends a change of scope,
finish the video you're on (if it's past its QUICK draft), then follow it.

## Final report

Under 200 words. Per video: slug, duration, file size, the analogy, the check_audio result (and any SAY rules
added), the poster time, and a new title in sentence case. Name any video you couldn't finish and its state.
