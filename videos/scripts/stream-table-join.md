# Gold one week, silver the next: join with the tier as it was

- Slug / scene: `stream-table-join`, `videos/scenes/stream_table_join.py:StreamTableJoin`
- Lesson: `stream-06`, section 1, "A stream-table join answers with the table as it is now, unless you keep its history"
- Audience / level: a complete newcomer. Has a loyalty card; met a Kafka topic, a partition and a `KTable` (a table
  kept on local disk, one row per key) in the last lesson; knows nothing about versioned tables or event time.
- Length: 4:45 (~750 words of narration, three pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=190` (both tables side by side after the rerun: plain join "gold, then silver", versioned join "silver, silver")
- The learner's real question: the program looked up Mira's tier and got gold; a rerun over the same payments got
  silver. Same data, same code: which answer is right, and why did it change its mind?
- Misconception to steelman and break: "look up the current tier, as a database join does" (broken by the late
  order and the rerun: the answer depends on arrival order); then "a versioned table fixes every lateness" (broken by
  the late upgrade o-2, fixed by a grace period that costs five minutes on every order).
- Concept chain: enrichment needs a tier per order → ask the database (15 questions waiting) → a local table (fast)
  → one row per customer answers with the tier now → a late order gets the wrong tier, and a rerun disagrees → keep
  every version, pick the one in force at the order's own time (versioned table) → limits: history is bounded, and a
  late table update needs a grace period (hardest last)
- Analogy family: the café chain from the lesson's opening. A wall board with one line per member, rubbed out and
  rewritten (the plain table); a member's logbook with a dated line for each tier, "silver from 09:00, gold from
  10:00" (the versioned table); the time printed on the till receipt (the order's own timestamp); the receipt that
  prints the points you earned (the lesson's aside and closing).
- Open loops: "which answer is right?" planted in scene 1 → scene 5; "two answers" planted in scene 1 → broken in
  scene 4.
- Assumptions: all values are the lesson's (2% silver, 5% gold, made-up rates; 3,000 orders a second, 5 ms, 15
  questions waiting; c-1 silver from 09:00, gold from 10:00; o-1 placed 09:30, arriving 10:01; o-2 at 10:02; 7 days
  of history; 5 minutes of grace, stream time past 10:07; the Try it's rows A1, A2 and B). Mira is the lesson's c-1.

## The one picture

Top: an event-time line from 09:00 to 10:30, silver until 10:00 and gold after, with o-1's own time at 09:30 (and
later o-2 at 10:02). Middle left, gold-outlined in blue: the plain table, one row per customer. Middle right, teal:
the versioned table, one row per version with its start time. An order chip arrives in the middle and dots run into
each table; each join's answer appears under its table. Red marks a wrong answer, green a right one. Captions at the
bottom.

## Scene 1 · Mira's coffee · 0:00–0:40 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: Picture a café chain with a loyalty scheme. Silver members get 2% of each purchase back, and gold members get
5%. Mira is upgraded to gold at 10:00. She bought a coffee at 09:30, but that payment was held up, and reached the
program that works out cashback at 10:01. The program looks up Mira's tier, finds gold, and gives her 5%. Next week,
the company runs the same program again over the same payments, to check its sums. This time Mira's coffee gets 2%.
Same data, same code, two answers. Which one is right, and why did the program change its mind?

SCREEN: Title card. The timeline: silver from 09:00, gold from 10:00; a coffee marker at 09:30; a "10:01" arrival
flag. "5%" then, under it, "next week: 2%". Caption "same data, same code, two answers".

## Scene 2 · The lookup we all write · 0:40–1:25 · [FAMILIAR] [SHRINK]

VO: Adding a detail to each event from a table is called enrichment. Each order needs its customer's tier, because
the tier sets the cashback. The tiers live in a database that another team runs, and every change to it is copied
as a record onto a Kafka topic, customer-tiers. Version 1 asks the database for every order. At 3,000 orders a
second and 5 ms a question, that's 15 questions waiting at every moment. Version 2 keeps a local copy: a table built
from customer-tiers, on the program's own disk, as in the last lesson. It keeps the latest value for each customer,
and a lookup takes microseconds.

SCREEN: A grey "tiers database" box with 15 small question dots queued; caption "3,000 a second × 5 ms = 15
waiting". Then the box becomes the plain table "one row per customer"; caption "a local copy: microseconds".

## Scene 3 · The late coffee · 1:25–2:05 · [SHOW] [PAIN]

VO: Now watch c-1, that's Mira. Her silver record arrives: c-1 is silver from 09:00. Then the upgrade arrives, and
the row is overwritten: gold. Silver is gone. A tier change sends nothing on, so orders joined earlier keep what they
got. Now o-1, the coffee placed at 09:30, finally arrives at 10:01. The join looks up c-1, finds gold, the only row it
has, and pays 5%. No error. No warning.

SCREEN: The plain table row "c-1: silver" then "c-1: gold"; the o-1 chip "placed 09:30, arrives 10:01" drops in; a
dot runs to the row; under the table "o-1: gold, 5%" in red.

## Scene 4 · Next week · 2:05–2:40 · [PREDICT] [PAUSE] [BREAK] [NAME] [JOKE:release]

VO: Next week, the same topics are read again, and this time the partitions are read in a different order. o-1
arrives before the upgrade. What does the join say now? Pause and guess.

(three seconds)

Silver. Same input, two answers. A join like this isn't deterministic: two runs over the same data disagree. It's a
cashier who charges whatever the board says when you reach the front of the queue, not when you picked up the cup.

SCREEN: The row resets to silver; o-1 drops in before gold; "o-1: silver, 2%" appears beside "gold"; caption "not
deterministic: two runs, two answers".

## Scene 5 · The logbook · 2:40–3:30 · [ANALOGY] [MAP] [SHOW] [NAME] [LOOP-PAYOFF]

VO: Back to the café. The wall board has one line per member, rubbed out and rewritten. Now picture a logbook
instead, with a dated line for every change: Mira, silver from 09:00. Mira, gold from 10:00. And look at the time
printed on the till receipt: 09:30. Which line was in force then? Silver. It doesn't matter when the receipt reaches
the office. Map it out. The wall board is the plain table. The logbook is a table that keeps every version, with the
time it took effect. And the receipt's time is the order's own timestamp. Kafka Streams calls this a versioned table.
The join picks the version with the latest time at or before the order's time. Run it both ways: silver, and silver. Which answer was right? Silver. She paid at 09:30.

SCREEN: The versioned table appears on the right with two dated rows. A dashed line from 09:30 on the timeline down to
the silver row. Captions map each part. o-1 runs into the versioned table twice, in both arrival orders: "silver,
silver" in green.

## Scene 6 · Its limits · 3:30–4:25 · [GUARDRAIL] [BREAK] [PREDICT]

VO: Two limits. First, the logbook isn't endless. Here it keeps 7 days. An order older than that can't be answered:
an inner join drops it, and a left join joins it with nothing. Second, versions fix late orders, not late table
updates. Order o-2 is placed at 10:02, but this time the upgrade itself is late, and o-2 gets there first. The table
only knows silver, so o-2 gets silver. The fix is a grace period on the order side: hold each order 5 minutes, in
stream time. o-2 waits until stream time passes 10:07, the upgrade arrives meanwhile, and o-2 gets gold. The price is
that every order now comes out 5 minutes later.

SCREEN: Caption "history: 7 days". The gold row fades out; o-2 at 10:02 arrives and gets silver (red). A yellow hold
bar "grace: 5 minutes" fills; the gold row returns; o-2 gets gold (green). Caption "every order 5 minutes later".

## Scene 7 · The code · 4:25–4:45 · [SHOW]

VO: In Java and Kotlin, the change is the store: a persistent versioned store with 7 days of history. The join
itself stays the same.

SCREEN: Two code panels; the versioned store line highlighted, then the join line.

## Scene 8 · The moral, and a check · 4:45–5:20 · [MORAL] [PRINCIPLE] [PREDICT] [PAUSE]

VO: So the moral of the story: join each event with the table as it was when the event happened, not as it is when
the event arrives. Or print the answer on the receipt: if the till writes the tier into the order when Mira pays, no
later join can change it. One quick check. Order o-3 was placed at 09:59 and arrives at 11:00. What does the versioned
join give it? Pause and think.

(three seconds)

Silver. 09:59 is before 10:00, so the silver line was in force.

SCREEN: The moral in yellow. A new chip "o-3: placed 09:59, arrives 11:00" with its mark on the timeline just left of
10:00; countdown; a dashed line to the silver row; "o-3: silver".

---

### Beat check

- QUESTION and FAMILIAR (scene 1), SHRINK (scene 2), PAIN and SHOW (scene 3).
- PREDICT with PAUSE three times (scenes 4, 8, and the o-2 case in scene 6 shown as a reveal).
- BREAK: the plain join gives two answers (scene 4); the versioned table can't fix a late upgrade (scene 6).
- ANALOGY and MAP (scene 5) before the name "versioned table"; NAME "not deterministic" after the break.
- GUARDRAIL (scene 6), MORAL and PRINCIPLE (scene 8). Light moment: the cashier at the front of the queue.

### Accuracy notes for the producer

- The Try it's rows: A1 (o-1 before the upgrade) unversioned silver, versioned silver; A2 (after) unversioned gold,
  versioned silver; B (upgrade after o-2) unversioned and versioned silver, versioned with grace gold.
- Versioned tables need Kafka Streams 3.5 or later; the lesson's store keeps 7 days (`Duration.ofDays(7)`); "older
  than that" means more than 7 days older than the table's newest record.
- Grace on a versioned table's join: `Joined.withGracePeriod(...)`; stream time is the largest timestamp seen.
- The lesson also covers Flink SQL's temporal joins (`FOR SYSTEM_TIME AS OF`); the video leaves Flink out.
- The code panels trim serdes on the join; the Java line uses `Materialized.as(Stores.persistentVersionedKeyValueStore(...))`.
- The cashier line is an illustration of arrival-time lookups, not from the lesson.
