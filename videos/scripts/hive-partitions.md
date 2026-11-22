# One shelf per day: how a folder name lets a query skip the rest

- Slug / scene: `hive-partitions`, `videos/scenes/hive_partitions.py:HivePartitions`
- Lesson: `batch-04`, section 1, "One directory per day lets a query skip the other days"
- Audience / level: a complete newcomer. Knows what a folder and a file are; has seen a SQL `WHERE` once; knows
  nothing about partitions, pruning or query plans.
- Length: 4:04 (~650 words of narration, two pauses, silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=125`, the pruned query: seven day folders, only `dt=2026-11-03` lit, "opens 1/8 files"
- The learner's real question: why did a question about yesterday take twenty minutes, and how can a program skip
  the days it doesn't need?
- Misconception to steelman and break: "a filter on `created_at` for the same day skips the other days too, since
  the dates match". Broken by the demo's plan: the `dt` filter opens 1/8 files, the `created_at` filter opens all 8.
- Concept chain: one folder means every query reads everything → one directory per day, named `dt=<day>` → the value
  lives only in the path → a filter on `dt` skips directories (pruning) → any other filter reads them all → so put
  `dt` in the query, and pick a column with few values (hardest last)
- Analogy family: the lesson's library: every book on one long shelf, then one shelf per year with the year on a
  label; a question about one year never visits another shelf. The engine only reads the labels.
- Open loops: the twenty-minute wait (scene 1) → explained in scene 2 and fixed in scene 5; the warm-up's
  `created_at` trap planted in scene 6 → paid off in scene 6 and the check in scene 9.
- Assumptions: numbers are the lesson's: 1,095 days in three years, about a thousand directories, 500,000 shops and
  500 million directories, the demo's week (`dt=2026-11-01` to `dt=2026-11-07`, 8 files in 7 directories), `opens 1/8
  files` and `opens all 8 files`, the warm-up's 30 November folders. The coloured dots inside the folders are a
  picture of payments, not counts. Row values are not shown, only the column names.

## The one picture

Top: the query, as a yellow chip. Middle: the table folder `payments/`. At first one long box (the one long shelf)
with payments as coloured dots, one colour per day; then seven day folders in a row, `dt=2026-11-01` to
`dt=2026-11-07`, each with its own dots. Folders the query opens light up yellow; skipped folders dim with a grey
"skipped". Under the folders: the result line (files opened). Captions at the bottom.

## Scene 1 · Twenty minutes for one day · 0:00–0:30 · [QUESTION]

VO: Picture a small company that records card payments for cafés and shops. Every night, a program saves the day's
payments as files in one shared folder. By now, it holds a whole year. A colleague in finance asks how much the shops
took yesterday. The answer arrives twenty minutes later. Why so slow, for one day?

SCREEN: The `payments/` box fills with dots night by night (caption "one folder, a whole year"); the question chip
"how much did the shops take yesterday?"; a clock caption "20 minutes".

## Scene 2 · One folder reads everything · 0:30–1:00 · [FAMILIAR] [PAIN]

VO: Because the program read the whole year to find one day. With one folder for the whole table, every question
reads every file. And the table grows by a day, every day. After three years, a question about yesterday reads 1,095
days of data, to use one of them.

SCREEN: A yellow sweep passes over every dot; caption "every question reads every file"; then "3 years: reads 1,095
days to use 1".

## Scene 3 · The long shelf · 1:00–1:40 · [ANALOGY] [MAP] [JOKE:pivot]

VO: A library with every book on one long shelf has the same problem. Ask for one year's books, and somebody walks
the whole shelf. Usually the new person. The library's old fix: one shelf per year, with the year on a label. A
question about one year never visits the other shelves.

Let's do the same with the table. Split the folder into smaller folders, one per day, and name each one after its
day. The shelf is a folder. The label is the folder's name. And the books are the payments.

SCREEN: The long box splits into seven day folders; dots fly to their own day; labels `dt=2026-11-01` ... appear.
Mapping captions as each part glows.

## Scene 4 · The value lives in the name · 1:40–2:20 · [SHOW] [NAME]

VO: Each of these folders is called a partition, and dt, short for date, is the partition column. The name holds the
column and its value together, so any program can rebuild the column from the path alone.

In fact, the value lives only there. Spark, the engine this course uses to run jobs over many machines, takes the dt
column out of the rows when it writes, and puts it in the folder name instead. When a program reads the table, it
turns the name back into a column.

SCREEN: `dt=2026-11-03` glows; caption "partition column: dt". A row card with columns `dt  created_at  amount_cents`
appears; the `dt` cell flies up into the folder name; the card keeps `created_at  amount_cents`. Then the name's
`dt` flies back down into the card (caption "reading: the name becomes a column again").

## Scene 5 · Pruning · 2:20–2:50 · [SHOW] [NAME] [LOOP-PAYOFF]

VO: Now ask for one day. Where dt is the third of November. The program reads the labels first, and skips every folder
that can't match, before opening a single file. That's called partition pruning. In the lesson's week of payments,
DuckDB opens one file out of eight. Over three years, one day out of about a thousand.

SCREEN: Query chip `WHERE dt = '2026-11-03'`; a cursor reads each label; six folders dim ("skipped"), one lights.
Result "DuckDB: opens 1/8 files". Caption "partition pruning: skip what can't match, before opening a file".

NOTE: DuckDB gets one sentence before its result: "a small database that runs inside a program".

## Scene 6 · The same day, another column · 2:50–3:35 · [PREDICT] [PAUSE] [BREAK] [JOKE:release]

VO: Now a different filter. Every payment inside the files also has its exact time, in a column called created at.
Ask for the payments whose created at is on the third of November. The very same day. How many files does it open?
Pause and guess.

(three seconds)

All eight. The answer is right, nothing fails, and nobody notices the extra reading. The program only reads labels,
and the labels say dt. It can't know that created at and dt agree. Only you know that. The program would need to be
a mind reader, and it's a file reader.

SCREEN: Query chip `WHERE created_at::DATE = DATE '2026-11-03'`; countdown; all seven folders light; result "opens all
8 files"; caption "right answer, nothing fails, all the reading".

## Scene 7 · How to see it · 3:35–3:55 · [SHOW]

VO: The plan, the program's own description of how it will run a query, tells you. In DuckDB, a line like scanning
files, one of eight, means it skipped files by their path. No such line means it reads them all. In Spark, an empty
list of partition filters means nothing was skipped.

SCREEN: Two mono chips: `Scanning Files: 1/8` (green, under the first query) and `PartitionFilters: []` (red).

## Scene 8 · Guardrails · 3:55–4:25 · [GUARDRAIL]

VO: So, the rule: a filter on the partition column skips folders, and any other filter reads them all. Put dt in the
query. Keep the created at filter too, for the exact hours.

And pick a partition column that questions filter on, with few different values. A day is the classic: three years
is about a thousand folders. Split by shop as well, with 500,000 shops, and you get 500 million folders, most holding
one tiny file. Strike that one.

SCREEN: Query chip `WHERE dt = '2026-11-03' AND created_at ...`; one folder lit again. Captions "day: about 1,000
folders" (green), "day × shop: 500 million folders" (red, struck).

## Scene 9 · Moral and check · 4:25–4:55 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: The moral: the program skips by the label, never by what's inside. Name the folders by what you ask about, and
ask by that name.

One quick check. Thirty folders, one per day of November. You ask for dt on or after the twenty ninth. How many
folders does it open? Pause and think.

(three seconds)

Two. The twenty ninth and the thirtieth. Ask by created at instead, and it opens all thirty.

SCREEN: Captions; the check as a caption and a query chip; countdown; answer caption.

---

### Beat check

- QUESTION (scene 1) from the lesson's opening; FAMILIAR + PAIN (scene 2) with the lesson's 1,095 days.
- ANALOGY + MAP (scene 3), the library's shelves, mapped out loud before any term.
- NAME after the picture: partition, partition column (scene 4), partition pruning (scene 5).
- PREDICT + PAUSE + BREAK (scene 6): the warm-up's trap, run to its result in the demo (all 8 files).
- GUARDRAIL (scene 8), MORAL and a check (scene 9) last.
- Light moments: "usually the new person" (1:10), the mind reader and the file reader (3:30), "strike that one" (4:20).

### Accuracy notes for the producer

- "1/8 files" and "all 8 files" are the lesson's `PartitionPruningDemo` output for the week 2026-11-01 to 2026-11-07
  (8 files in 7 directories: one day has two files because two Spark tasks wrote it; which day varies, so the picture
  doesn't draw files).
- The library in the lesson splits by year; the table splits by day. Both are said.
- The engine can still skip parts of each file with statistics inside it (next lesson), and Iceberg's hidden
  partitioning removes the trap (lesson 11); both are left to the lesson.
- How the engine learns which days exist (listing directories, the metastore) is the next section; the video only
  says "reads the labels".
