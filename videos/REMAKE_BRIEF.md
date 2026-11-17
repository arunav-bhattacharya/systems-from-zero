# Brief for remaking videos (the newcomer rewrite)

Every video is being remade to teach the way the **venkat-style-video** skill describes, for a complete
newcomer, after its lesson has been rewritten in the book voice (`brief/VOICE.md`). Pipeline details (helpers,
render commands, the voice cache, Manim traps) are in `videos/MAKER_BRIEF.md` and `videos/README.md`; this file
says what changes. Where they disagree, this file wins.

## Read first

- The skill, from disk (it may not load with the Skill tool):
  `/Users/arunav/Library/Application Support/Claude/local-agent-mode-sessions/433d709e-8728-4258-b10c-98909f71fe68/5c806f8d-0769-4e35-ac24-a3ea18081c67/rpm/plugin_016d3EqtH26wG3KkkcCwp4FJ/skills/venkat-style-video/SKILL.md`
  and, in its `references/` folder, `teaching-arcs.md`, `analogy-bank.md`, `humor-and-voice.md` and
  `script-template.md`. Read all four before scripting your first video.
- `brief/VOICE.md`, "The reader is a complete newcomer".
- The rewritten lesson (`content/lessons/<id>.json`): its `opening`, the section the video belongs to, and its
  `closing`. The video tells the same story with the same running example and the same analogy, so text and
  video agree. Never add a fact the lesson or its research notes don't support.
- The old scene (`videos/scenes/<name>.py`) for the mechanism and the numbers it already got right.

## What a remade video is

- **1440p by default.** Every final render is 2560x1440 at 30 fps: run `./render.sh` without `QUICK`.
  `QUICK=1` is only for drafts and contact sheets.
- **2 to 6 minutes**, one concept, the full arc: the real question, the familiar starting point, the pain and the
  wish, an everyday analogy mapped part by part out loud, the problem shrunk, predict then show (with a pause
  of two or three seconds after "pause and guess"), the wrong model broken on purpose, the name only after the
  idea is understood, the guardrail, the moral, and one quick check question the viewer can answer from the
  picture. The user prefers a longer video that builds intuition over a short one that rushes; never pad.
- **For a complete newcomer.** No product, tool or industry word without a plain sentence first. No "as you
  know". Everyday analogies (a parcel, a queue at a counter, a library catalogue, a notebook, order slips).
- **One picture they could redraw.** One persistent diagram of physical things that move (boxes, queues,
  tokens, arrows), each with the same colour and place from start to end. At most about six things on screen.
  Code, if any, comes last and short, as confirmation of what they saw. On the Kafka and Redis tracks, code on
  screen is Java and Kotlin side by side.
- **Humor** as the skill says: about one light moment every one to two minutes, at pivots and payoffs, never
  inside a walkthrough, each cashed back into the idea. Invent every analogy and joke; never reuse Venkat's
  jokes, stories or catchphrases, and never present the narrator as him.
- **Narration**: written to be said, very simple English, no em or en dashes, no banned words from
  `brief/BRIEF.md`, no "In this video", no "Let's dive in". About 150 to 170 words a minute.

## Files

- Keep the video's existing `slug`, so its place in `content/videos.json` stays. Write the new scene to the same
  path (`videos/scenes/<name>.py`), replacing the old one, with the same class name.
- If the old voice lines in `videos/voice` are not reused, that's fine; new text gets new cache files.
- Before any render, write the script (scene blocks with beat tags, as in `script-template.md`) to
  `videos/scripts/<slug>.md`. It is the record of the arc and the accuracy notes.
- Render one video at a time: other makers share this machine.

## Check your work (required)

1. Draft with `QUICK=1`, make a contact sheet, and fix every overlap, clipped text, text touching a line,
   and object appearing before its cue (see "Lessons learned" in `MAKER_BRIEF.md`).
2. Render at full 1440p. Look at three or more full-size frames at the busiest moments.
3. `.venv/bin/python check_audio.py <slug>` and fix real mispronunciations with `SAY` rules at the top of your
   scene file (delete the cached line before re-rendering).
4. Keep the final `.mp4` reasonably small for streaming (most are 13 to 24 MiB). The site serves MP4s from the GitHub
   release, not from Cloudflare, so there's no hard 25 MiB cap any more; the coordinator uploads each file when it ships.
5. `ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 ../web/video/<slug>.mp4`
   must print `2560,1440`.

Don't edit `content/videos.json`, any lesson file, `sfz.py` or anything outside `videos/` and `web/video/`.
No git commands.

## Final report

Under 200 words. For each video: slug, scene path and class, lesson id, section index, a new title in sentence
case if the old one no longer fits, duration, resolution, and the check_audio result.
