# Redo a month of numbers without a hole: replay the log into a second table

- Slug / scene: `kappa-reprocessing`, `videos/scenes/kappa_reprocessing.py:KappaReprocessing`
- Lesson: `derive-01`, section 3, "Kappa: keep the log, replay it into a second copy, switch the readers"
- Audience / level: a complete newcomer. Has seen a café till and a dashboard; doesn't know what a log, a job, a
  replay, event time or the kappa architecture is.
- Length: 4:50 (~860 words at Kokoro's ~175 words a minute, plus a pause and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=190`, v2 rebuilt by event time, its bars beside v1's, the owners' tag still on v1
- The learner's real question: finance changed the rule for a month of takings. How do you work the month out again
  while two thousand owners keep reading it, without anybody seeing holes?
- Misconception to steelman and break: (1) "change the code, empty the table, let it refill", broken by a month with
  holes while it refills; (2) "the new job can keep the old job's habit of putting each payment on the day it handled
  it" (the lesson's warm-up), broken by the replay that puts 554,322.25 on today and zero on every earlier day.
- Concept chain: one log, one job, one table → a fresh sheet beside the old one → keep the log, replay into v2 →
  processing time vs event time (hardest) → size the replay, switch the readers, delete the old → the name, the three
  conditions, the costs
- Analogy family: the lesson's café notebook and clerks. Lambda had two clerks; kappa is one clerk with one method, who
  starts a fresh sheet from the notebook's first page whenever the method changes.
- Open loops: "without a hole?" planted in scene 1 → paid off in scene 7 (the switch); "a busy morning" in scene 5 →
  cashed back as "the clock on the wall".
- Assumptions: numbers are the lesson's Try it (ReplayDemo): 30 days, 400 records a minute, 5 new a minute, 395
  gained, 6,000 records of history, 16 minutes; 554,322.25 on day 30 by processing time; 19,684.20, 19,139.78,
  19,609.06, 17,678.19, 19,785.49 and 6,846.18 by event time; 64 minutes at 100 a minute. The heights of the other
  event-time bars, and of v1's bars, are illustrative (the demo prints "..."); only the named values are labelled.

## The one picture

Top: the log as a tape of 31 cells, day 0 on the left, day 30 (today) on the right, new payments arriving from the
right. Under it, two job boxes: v1 on the right reading the newest cell, v2 on the left with a yellow reading cursor.
Bottom: two tables as small bar charts of takings by day, v1 (blue) on the right, v2 (green) on the left. A green tag
"owners read this" sits above whichever table the owners read. Captions at the bottom.

## Scene 1 · The request · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: Picture the café where this course began. Each card payment becomes one line in the payments app, and a program
turns those lines into the owner's takings: the money her shop took each day. Now finance asks for one change.
Takings should subtract refunds, and count each payment on the day it happened. A month of numbers must be worked out
again, while two thousand owners keep looking at theirs. How do you redo a month without anybody seeing a hole?

SCREEN: Title card. The log tape fills in, the v1 job and its table grow; captions for the two changes; the owners'
tag; a "?".

## Scene 2 · The log, the job, the table · 0:30–1:00 · [FAMILIAR]

VO: Here's the setup. The log is every payment, one after another, in the order they arrived. Nothing in it is ever
changed. A job called v1 reads each new line as it lands, and adds it to a table: takings, by day. The owners'
dashboards read that table.

SCREEN: The log glows; a dot runs from the newest cell to v1 and on to the table; the newest bar grows a little.

## Scene 3 · The tempting plan · 1:00–1:25 · [PAIN] [BREAK]

VO: The tempting plan: change v1's code, empty the table, and let it fill up again. One program, one table. Feels
tidy. But until it refills, every owner sees a month with holes in it. That's not a fix. That's an outage with good
intentions.

SCREEN: v1's bars drain to zero, red caption "a month with holes, until it refills", then come back ("let's not").

## Scene 4 · A fresh sheet · 1:25–2:00 · [ANALOGY] [MAP]

VO: The café already knows better. Picture the clerk who keeps the takings sheet from the notebook. When her method
changes, she doesn't rub out the sheet the owner is reading. She takes a fresh sheet, starts from the notebook's
first page, and works forward. When she's caught up, she hands it over, and bins the old one. Map it. The notebook is
the log. The sheet is the table. Her method is the job's code. And here the picture breaks in our favour: a program
rereads a month in minutes, and can do it again tomorrow.

SCREEN: Captions for each mapping while the log, the v1 table and the v1 job glow in turn.

## Scene 5 · Replay, and a guess · 2:00–3:00 · [SHOW] [PREDICT] [PAUSE] [BREAK] [JOKE:release] [NAME]

VO: So start a second job, v2, with the new code. It reads the log from the very first line and writes to a new table.
Nobody reads that table yet. Now suppose v2 kept one habit from v1: it puts each payment on the day it handled it.
For a year, that looked right. Where will this replay put the month's takings? Pause and guess.

(three seconds)

All of it on today. 554,322.25 on day 30, and zero on every day before. According to this table, the café sold a
month of coffee this morning. Busy morning. The habit was wrong all along. Live, a payment is handled within a second
of happening, so the two days almost always matched. A replay handles every line today, so the hidden mistake becomes
the whole answer. The day the job handles a line is called processing time. The day written inside the line, when the
payment happened, is called event time. A replay must use event time.

SCREEN: v2 job and table grow on the left. Caption "v2 puts each payment on the day it handled it". Countdown. The
cursor sweeps the log; every dot lands on day 30's bar, which grows off the chart: red "554,322.25 on day 30";
"0" on the rest. Captions name the two times.

## Scene 6 · By event time, and how long · 3:00–3:40 · [SHOW] [SHRINK]

VO: Replay again, by event time. Day 0: 19,684.20. Day 1: 19,139.78. And so on, up to today, which has only just
begun. How long does it take? v2 reads 400 lines a minute while 5 new ones arrive, so it gains 395 a minute. Six
thousand lines of history take 16 minutes. Until then, v2's table is missing the recent days, so nobody moves to it.

SCREEN: The table empties; the cursor sweeps again and the bars grow day by day; callouts for days 0, 1, 29 and 30.
Captions "400 read, 5 new: 395 gained a minute" and "6,000 / 395: 16 minutes".

## Scene 7 · Switch, then delete · 3:40–4:15 · [SHOW] [NAME] [LOOP-PAYOFF]

VO: When v2 reaches the end of the log, both tables follow the same lines, each with its own code. Now switch the
owners to v2. Nobody saw a hole, because the old table kept serving the whole time. Later, stop v1 and delete its
table. That's the whole recipe. Jay Kreps, who helped build Kafka, a program that keeps logs like this one, suggested
it in 2014, and half joking, called it the kappa architecture. One engine, one codebase. Replaying the oldest part of
the log is the batch job.

SCREEN: v2's cursor reaches the newest cell; dots run from it to both jobs. The owners' tag slides from v1 to v2.
v1 and its table fade out. Caption "kappa: keep the log, replay into a second copy, switch the readers".

## Scene 8 · Three conditions, and the bill · 4:15–4:50 · [GUARDRAIL]

VO: It works under three conditions. The replay runs through the same code as live lines. A crash halfway must not
count anything twice. And every grouping by time uses event time. Then the bill. The log must still hold the month.
Kafka deletes lines older than 7 days unless you tell it otherwise, so keep 30 days on purpose. A busy log holds 130
billion lines after a month. And while both versions run, you pay for two jobs and two tables.

SCREEN: Three captions. Then the log's cells older than 7 days turn grey with a red "deleted after 7 days by default",
and come back with "keep 30 days, on purpose". Caption "a busy log: 50,000 a second, 130 billion a month".

## Scene 9 · The moral, and a check · 4:50–5:20 · [MORAL] [PREDICT] [PAUSE]

VO: So: keep the log, replay it into a second table by event time, and switch the readers when it has caught up. Never
rebuild the table they're reading. One quick check. You replay at 100 lines a minute instead of 400. What changes,
and what doesn't? Pause and think.

(three seconds)

It takes 64 minutes instead of 16. And the daily takings don't change by a cent. The answer depends on the log, not on
how fast you read it.

SCREEN: Moral caption. For the check, the cursor sweeps slowly, caption "100 a minute: 64 minutes"; the bars glow,
unchanged.

---

### Beat check

- QUESTION (scene 1) from the opening's request; FAMILIAR (scene 2).
- BREAK: the empty-and-refill plan (scene 3) and the processing-time habit (scene 5).
- ANALOGY + MAP (scene 4) with its breaking point said out loud.
- PREDICT with PAUSE: scene 5 and the check in scene 9.
- NAME after SHOW: processing time and event time (scene 5), kappa (scene 7).
- GUARDRAIL (scene 8) and MORAL (scene 9) last. Light moments: "an outage with good intentions" (about 1:20), "busy
  morning" (about 2:30).

### Accuracy notes for the producer

- The demo's table is net revenue for all shops together by day; the video calls it takings, as the lesson does.
- v2 "read 6,080 records in 16 minutes": 6,000 of history plus the ones that arrived meanwhile.
- At 100 a minute the demo reads 6,320 records in 64 minutes and days 0 to 29 don't change; day 30 (today) keeps
  growing with live payments, which the narration's "daily takings" glosses over.
- The stable-share move of owners, comparing the two tables and the rollback are the next section's; the video does a
  single switch.
- 130 billion is the lesson's figure for a log at 50,000 records a second over a month.
- Exactly-once processing is said as "a crash halfway must not count anything twice"; Beam and the DDIA wording are left
  to the lesson.
