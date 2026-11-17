# Task sheet for lesson writers (the newcomer rewrite)

You rewrite lessons of this course for complete newcomers, in the venkat-voice book voice. The Foundations
and Computer networking tracks are already done this way, and the user approved them. Match them.

## Read first

1. `brief/VOICE.md`: the rules for this rewrite. It wins over every other brief.
2. The venkat-voice skill at the absolute path given in VOICE.md (read the file; it won't load with the Skill
   tool).
3. Two finished lessons in this course, as the bar: `content/lessons/found-01.json` (opening, sections 0 and 1,
   the aside, recap, closing) and `content/lessons/net-07.json` (opening, section 0, closing).
4. `brief/BRIEF.md` for the house rules (its "Who the learner is" section is superseded by VOICE.md).
5. For each lesson: the current file, the research notes for its track in
   `research_notes/Systems course curriculum research/`, and the neighbors. Read the previous lesson's closing
   (or its last section if it isn't rewritten yet) so your opening links to it. Read the next lesson's goal and
   first section so your closing leads into it. Other writers may be rewriting the neighbors right now: read
   whatever state they're in.

## For each lesson

- Add `opening` and `closing`. Rewrite the goal, warmup, every section's heading and prose, try-it steps and
  expect prose, worked example, lab steps and hints, drill, recap, quiz wording and `why`, flashcards, terms,
  explain-back and deeper, all in the voice and for a reader who knows nothing about the topic. Every term gets
  a plain definition the first time it appears in the lesson, even if an earlier lesson defined it.
- Keep everything VOICE.md lists under "What must not change": ids, titles, section count and order (videos are
  attached by index), quiz `from` fields, labs, try code and commands, real output blocks, sims, and
  stepper/figure structure. Check this with a small script that compares against `git show HEAD:<file>`.
- Keep the substance. Every mechanism, real number and command stays, explained one level down. Jargon a
  newcomer can't use yet is cut or moved to `deeper`.
- Edit with a Python script (json.load, edit, json.dump with ensure_ascii=False, indent=2). Run
  `/usr/local/bin/python3 site/validate.py content/lessons/<id>.json`; it must give 0 errors.
- Reread the lesson as the newcomer, run the skill's "Before you hand it in" checklist and VOICE.md's step 4,
  and fix what you find before moving to the next lesson.

## Track pages (only when your task names one)

Do the track page after your lessons. Rewrite `intro`, `cheatsheet`, `recap` and the quiz wording and `why` for a
newcomer, consistent with that track's rewritten lessons (read their goals, openings and recaps). Keep the quiz's
structure, `answer` indexes and any `from` fields. Validate with
`/usr/local/bin/python3 site/validate.py content/tracks/<id>.json` (0 errors). Model: `content/tracks/net.json`.

## Rules for working alongside others

Other writers and video makers work in this repo at the same time. Touch only your own files. Don't run
build.py or git, and don't touch anything in `videos/`, `web/`, `labs/` or `content/videos.json`. If the
coordinator sends a change of scope, finish the lesson you're on (validated), then follow it.

## Final report

Under 150 words: per lesson, the opening scene, the new section headings, the section word count, and anything
cut or moved to deeper; one line per track page. Mention anything you couldn't verify.
