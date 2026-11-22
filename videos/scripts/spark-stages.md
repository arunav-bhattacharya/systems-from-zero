# Everything meets at the pass: Spark jobs, stages and tasks

- Slug / scene: `spark-stages`, `videos/scenes/spark_stages.py:SparkStages`
- Lesson: `batch-06`, section 2, "Where a job splits into stages: the shuffle"
- Audience / level: a complete newcomer. Knows the previous lessons' word "shuffle" only loosely; knows nothing about
  Spark's jobs, stages, tasks or plans.
- Length: 4:27 (two pauses, silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=172`, after the shuffle: four files, stage 1 tasks, 16 shuffle lines, stage 2 tasks, shop 42 met in one task,
  "1 job · 2 stages · 8 tasks"
- The learner's real question: the report reads 4 files, filters and adds up per shop. How many pieces of work does
  Spark run, and why does the job split where it does?
- Misconception to steelman and break: "each task can finish its own files' sums" (so 4 tasks): broken by shop 42,
  whose rows sit in all four files, so four part totals and nobody has the real one.
- Concept chain: one task per file → narrow steps chain inside a task → a wide step needs rows from every piece → the
  shuffle (hash, write, fetch) brings them together and every task before it must finish → job, stage, task, and the
  counting rule → the plan's `Exchange`; settings and AQE change the count (hardest last)
- Analogy family: the lesson's restaurant kitchen: cooks at their own stations (narrow steps), the pass where a plate's
  dishes meet (the shuffle), a plate that waits for its slowest dish.
- Open loops: the warm-up's "how many tasks?" planted in scene 1 → paid off in scene 6; "what if that machine dies?"
  planted in scene 8 → left to the next section, by name.
- Assumptions: numbers and output are the lesson's: 4 files, 4 shuffle partitions (default 200), 4 × 4 = 16 blocks,
  1 job, 2 stages, 8 tasks; AQE on: 2 jobs, 5 tasks [4, 1]; Spark 3.2; the plan lines from `StagesDemo` with the
  `#` ids and long FileScan details trimmed. Which stage 2 task owns shop 42 is a made-up picture (the lesson only
  says hash(merchant_id) mod 4 picks one).

## The one picture

Left to right: four files (grey), the four stage 1 tasks (blue) in a dashed "stage 1" frame with them, the shuffle
between (sixteen thin lines, "the shuffle"), four stage 2 tasks (teal) in a dashed "stage 2" frame, and the driver
(white), which receives the result of `collect()`. Shop 42's part totals are yellow tokens. A counter line under the
picture: jobs, stages, tasks. Captions at the bottom. The code and plan appear once, last, over a dimmed picture.

## Scene 1 · How many tasks? · 0:00–0:35 · [QUESTION] [PREDICT] [PAUSE] [LOOP-PLANT]

VO: Spark, a program that runs data jobs across many machines, splits its work into pieces called tasks. Here's a
nightly report. Read four files of payments, keep the captured ones, add up the amounts for each shop, and collect
the result. Spark gives each file its own task. After the grouping, it's set to make four pieces. How many tasks run
in total? Pause and guess.

(three seconds)

Hold on to your guess. Let's cook it.

SCREEN: The report as a chip at the top. Four files appear, then the driver. Countdown.

## Scene 2 · Each cook at their own station · 0:35–1:15 · [FAMILIAR] [SHOW] [NAME: narrow]

VO: Start with the files. Four files, four tasks, one per file. Each task reads its file, keeps the captured
payments, and adds up the amounts per shop. Task two can filter file two without looking at anything else.

So the steps run back to back inside one task. Read a batch of rows, filter it, add it to a running sum per shop,
then the next batch. Nothing in between gets written down. Steps like these, where each piece needs only its own
input, are called narrow.

SCREEN: Four task boxes grow from the files. Inside task 2: "read → filter → sum per shop" ticks along. Caption
"narrow: each piece needs only its own input".

## Scene 3 · Shop 42 is everywhere · 1:15–1:40 · [PAIN] [BREAK]

VO: But here's the catch. Shop 42 sold things in all four files. So each task ends up with its own part of shop 42's
total. Four part totals, in four places, and nobody has the real one. Adding up per shop is a wide step: the answer
for one shop needs rows from every piece.

SCREEN: A yellow "42" token appears in every stage 1 task; a red "?" by each. Caption "wide: one shop's answer needs
rows from every piece".

## Scene 4 · The pass · 1:40–2:15 · [ANALOGY] [MAP] [JOKE:pivot]

VO: A restaurant kitchen has the same problem. The steak comes off the grill. The fries come out of the fryer. Each
cook works their own station, and that's the narrow part. But a plate can't go out until its steak and its fries meet
at the pass, the counter where each order comes together. Nobody wants the fries delivered to table nine while the
steak is still on the grill.

Let's map that. The stations are the tasks. The pass is the shuffle. And a finished plate is one shop's total.

SCREEN: Captions; the stage 1 tasks glow ("stations"), the space between the columns glows ("the pass"), then the
stage 2 tasks appear ("plates").

## Scene 5 · How the pass works · 2:15–3:05 · [SHOW]

VO: Here's how the pass works. Each task splits its part totals into four parts, one for each task of the next step.
It picks the part by hashing the shop number and keeping the remainder after dividing by four, the same trick
MapReduce used. It writes the parts to its own machine's disk.

Then each next-step task fetches its part from every earlier task. Four times four, sixteen blocks. All four pieces of
shop 42 now meet in one task, which adds them up.

And notice the wait. No task after the pass can start until every task before it has finished writing. A plate waits
for its slowest dish. So the shuffle cuts the work in two.

SCREEN: "hash(merchant_id) mod 4" caption; small four-part marks on each task; sixteen lines draw; the four 42 tokens
fly to one stage 2 task and merge into "42: total". Task 4 lags; stage 2 tasks stay grey until it finishes. A
dashed cut line through the pass.

## Scene 6 · Job, stage, task · 3:05–3:40 · [NAME] [LOOP-PAYOFF]

VO: Now the three words. A job is everything one action runs; here, collect. A stage is a stretch of narrow steps
between shuffles. And a task is one piece of data going through one stage. Count them. One job. Two stages. Four tasks,
plus four tasks. Eight. Did you guess eight?

So the rule: stages are the number of shuffles plus one. Tasks are the input pieces plus the pieces of each shuffle.

SCREEN: Dashed frames "stage 1" and "stage 2"; counter "1 job · 2 stages · 8 tasks" builds; results flow to the
driver. Rule captions.

## Scene 7 · Read it in the plan · 3:40–4:05 · [SHOW]

VO: Spark's plan shows the same thing. Here's the report in Kotlin, and the plan it prints, read from the bottom.
Everything marked one runs in stage one. Everything marked two runs in stage two. And between them sits the shuffle,
which the plan calls Exchange. Count the Exchanges, and add one.

SCREEN: The picture dims; a code panel: three lines of Kotlin and five trimmed plan lines. `*(1)` lines glow blue,
`*(2)` teal, `Exchange` yellow.

## Scene 8 · What changes the count · 4:05–4:40 · [GUARDRAIL] [LOOP-PLANT]

VO: Two things change the count. The number of pieces after a shuffle is a setting, shuffle partitions. It's 200 by
default. The lesson's demo sets it to four.

And since Spark 3.2, a feature called adaptive query execution is on by default. It runs each stage that ends in a
shuffle as a job of its own, sees how small the shuffle really was, and plans the rest again. In the demo, it merges
the four tiny pieces into one: two jobs, and five tasks.

One more thing. The shuffle files sit on one machine's disk, in one copy. So what happens when that machine dies?
That's the next section.

SCREEN: Captions "default: 200 pieces after a shuffle (the demo: 4)", "AQE on: 2 jobs, 5 tasks [4, 1]" with the four
stage 2 tasks merging into one; a red outline on one stage 1 task's disk.

## Scene 9 · Moral and check · 4:40–5:05 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: The moral: narrow steps stay at their own station. A wide step sends everything to the pass, and the pass cuts the
job into stages.

One quick check. A plan reads four files and has two Exchanges, each making four pieces. How many stages, and how
many tasks? Pause and think.

(three seconds)

Three stages. Four, plus four, plus four: twelve tasks.

SCREEN: Captions; a check card; countdown; the answer.

---

### Beat check

- QUESTION with PREDICT and PAUSE (scene 1, the warm-up); FAMILIAR (scene 2, one task per file from the last section).
- PAIN and BREAK of "each task finishes its own sums" (scene 3) before the ANALOGY + MAP (scene 4).
- SHOW of the mechanism (scene 5), NAME of job, stage and task after it (scene 6), loop paid off by name.
- SHOW in the plan, code last (scene 7). GUARDRAIL (scene 8). MORAL and check (scene 9).
- Light moments: fries at table nine (2:05), the plate that waits for its slowest dish (2:55).

### Accuracy notes for the producer

- The plan lines are the lesson's `StagesDemo` output with the `#n` column ids, `output=[...]`, `ColumnarToRow`,
  `Project` and the long FileScan details trimmed. The stage numbers and the `Exchange hashpartitioning(merchant_id,
  4)` line are unchanged.
- "Writes the parts to its own machine's disk": shuffle files on the stage 1 task's machine, one copy (the lesson).
- Which stage 2 task owns shop 42 is drawn, not computed (Spark hashes with Murmur3, not `hashCode`).
- AQE's 2 jobs and 5 tasks [4, 1] are the demo's "AQE on" line.
- Left to the lesson: whole-stage code generation (`*(1)` explained only as "runs in stage one"), the Spark UI's
  DAG page, and lineage (next section).
