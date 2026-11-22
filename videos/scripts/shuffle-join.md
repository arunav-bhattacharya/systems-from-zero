# Where did nineteen minutes go? Move the letters, or copy the list

- Slug / scene: `shuffle-join`, `videos/scenes/shuffle_join.py:ShuffleJoin`
- Lesson: `batch-07`, section 4, "Joining two tables: move both, or copy the small one everywhere"
- Audience / level: a complete newcomer. Has never heard of Spark, partitions, shuffles or joins.
- Length: about 4.5 min (~780 words; Kokoro speaks about 180 wpm, pauses and builds bring it to ~165)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: the broadcast picture (four tasks each with a copy of the shops, "payments moved: 0")
- The learner's real question: the shops table is tiny, so why did one join make a 6 minute report take 25?
- Misconception to steelman and break: "the cost of a join is the matching, and a tiny table makes it cheap".
  Broken by counting what way one moves (every payment), and again by the trap: Spark itself only broadcasts when
  its size guess is under 10 MB, and after a filter the guess is the old, big one.
- Concept chain: matching needs both rows in one task → move both by key (shuffle, sort-merge join) → move the
  small one instead (broadcast hash join) → Spark chooses by a size guess that can be wrong → say so with a hint
  → the copy has a cost (hardest last)
- Analogy family: the post office at the end of the day (the lesson's): clerks with sacks of letters, pigeonholes,
  vans, and a one page list of postcodes and districts, photocopied for every clerk
- Open loops: "where did nineteen minutes go?" planted in scene 1 → paid off in scene 7
- Assumptions: numbers are the lesson's demo (1,000,000 payments in 4 partitions of 250,000, 500 shops, 1,000,500 rows
  and about 9.4 MB shuffled, 4 stages, 165 ms against 91 ms). The 3 GB customers table in the check is hypothetical.

## The one picture

Left column: four map tasks (white boxes, grey dots for payments, one gold dot for shop 42) and below them the
shops table (green). Middle: each task's shuffle file, four coloured blocks (blue, teal, purple, gold for reduce
tasks 0 to 3), later the copies of the shops (green chips). Right column: four reduce tasks in the same four colours,
later the driver (green, bottom right). Top right: a counter of rows moved. Bottom: one caption line.

## Scene 1 · The slow report · [QUESTION] [LOOP-PLANT]

VO: Picture the company that runs a café's card payments. Every hour, a report adds up what each shop took. It takes
about 6 minutes. Then the owners want totals per kind of shop: cafés, bookshops, grocers. Only the shops table knows
each shop's kind, so a teammate adds one line that matches each payment with its shop. The report now takes 25
minutes. And the shops table is tiny, just 500 rows. So where did nineteen minutes go? Hold that question.

SCREEN: "report: 6 min" chip; the code line `payments.join(merchants, "merchant_id")` drops in; the chip turns red,
"25 min"; "shops: 500 rows" and a big "?".

## Scene 2 · Both rows in one task · [FAMILIAR] [NAME:join]

VO: The report runs on Spark, a program that runs one job across many computers. Spark cuts the payments into slices
called partitions, and a task works on each slice. Here, a million payments sit in four partitions. Matching the
rows of two tables that share a key is called a join. And here's the catch. Spark can only match two rows that sit in
the same task. Shop 42 has payments in all four partitions, and its own row is in the shops table, somewhere else.
So before any matching, rows have to move.

SCREEN: Four task boxes with dots, "250,000 payments each"; gold dots pulse in all four; the shops box with its gold row.

## Scene 3 · The post office · [ANALOGY] [MAP]

VO: Picture a post office at the end of the day. Four clerks each hold a sack of letters from all over town. Every
letter has a postcode, and a one page list says which district each postcode is in. The job is to write the
district on every letter. Let's map it. The clerks are the tasks. The letters are the payments. The postcode is the
shop number. And the one page list is the shops table.

SCREEN: The same boxes relabelled "clerk 1" to "clerk 4", the shops box "postcode list: 1 page". Then each label turns
back while the caption builds the mapping.

## Scene 4 · Way one: move everything · [SHOW] [NAME:shuffle, sort-merge join]

VO: Way one moves everything. Each task works out a number for every row: hash the shop number, divide by four, keep
the remainder. Shop 42 gets 3. Like clerks sorting letters into four pigeonholes, one per van, each task writes its
rows to its own disk in four blocks. Then each task on the far side, called a reduce task, collects its block from
every file, like a van doing its round. Spark calls this move a shuffle. The shops go through the same shuffle, with
the same rule. So shop 42's row lands in reduce task 3, right beside its payments. Each reduce task sorts both piles
by shop number and walks them together, like merging two sorted piles of letters. That's a sort-merge join. It works
at any size, because sorting can spill to disk. But count what moved. Every payment and every shop: 1,000,500 rows,
written to disk, read back and sent across. In the lesson's demo, that's four stages and about 9.4 MB.

SCREEN: The rule chip; reduce task 3 pulses gold; write arrows and shuffle files; gold dots fly to block 3; fetch
arrows into reduce task 3, then all sixteen; the shops' file and its arrow to reduce task 3; "sort, then merge" in
every reduce task; the counter "rows moved: 1,000,500".

## Scene 5 · Photocopy the list · [WISH] [JOKE:pivot] [PREDICT] [PAUSE]

VO: Back in the post office, that's a lot of driving for a one page list. Wouldn't it be nicer to move the list
instead? So photocopy it. Every clerk gets a copy and writes the district on each letter right at the desk. How many
letters have to move now? Pause and guess. (three seconds) None. Not one letter leaves the desk.

SCREEN: Files, arrows and reduce tasks clear; the counter resets; a countdown bar.

## Scene 6 · Broadcast hash join · [SHOW] [NAME]

VO: Spark does the same. The driver, the program that plans the job, collects the 500 shops and sends a copy to
every worker. Spark calls these workers executors. Each task builds a hash table from its copy: a lookup that finds a
shop in one step, like a HashMap. Then it streams its 250,000 payments through it and joins them where they sit.
That's a broadcast hash join. No payment is shuffled, and nothing is sorted. In the demo, it took 91 milliseconds,
against 165 for the sort-merge join. About half.

SCREEN: Shops → driver; four green arrows → four "copy of 500 shops" chips; they become "hash table: 500 shops"; the
dots become "joined in place"; "payments moved: 0"; the two timings.

## Scene 7 · The trap · [BREAK] [LOOP-PAYOFF] [JOKE:is-the-explanation]

VO: So why didn't Spark do this for our report? It does broadcast on its own, when its size guess for one side is
under 10 MB. Here's the trap. The report keeps only the shops still in business. After a filter, Spark often can't
tell how small a table has become, so it kept its guess for the whole table: over 10 MB. It weighed the shops before
their diet. So it planned a sort-merge join, and every payment took the van. That's where the nineteen minutes went.
When you know a side is small, say so. Wrap it in broadcast. A hint is a request, and Spark can refuse it. Here it
copies the shops, and the payments stay where they are.

SCREEN: "broadcast only if the guess is under 10 MB"; on the shops box, "filter: still in business" and a red tag
"Spark's guess: over 10 MB"; red crosses on the copies; counter "rows moved: 1,000,500" (red); then the code
`payments.join(broadcast(merchants), "merchant_id")` (Kotlin) and the crosses go, counter "payments moved: 0".

## Scene 8 · The photocopier's limit · [GUARDRAIL] [JOKE:amplify]

VO: Now, where the photocopy picture breaks. Copying one page costs almost nothing. But a broadcast table passes
through the driver, and a full copy lands in every executor's memory. Broadcast a 2 GB table to 100 executors and
you've moved 200 GB, if the driver survives collecting it. That's photocopying the phone book for every clerk. Keep
broadcasts to tables of tens of megabytes.

SCREEN: The driver glows; the copies turn red "copy: 2 GB"; counter "2 GB × 100 executors = 200 GB"; caption "keep
broadcasts to tables of tens of MB".

## Scene 9 · Moral and check · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So the moral of the story. Both sides big: shuffle both, and sort-merge. One side small: send it to the data, and
the big side stays put. One quick check. A report joins the payments with a customers table of 3 GB. Should you
broadcast the customers? Pause and think. (three seconds) No. Three gigabytes in every executor is the phone book
again. Both sides are big, so shuffle both.

---

### Beat check

- QUESTION (1) → FAMILIAR (2) → ANALOGY + MAP (3) → SHOW, NAME shuffle and sort-merge join (4) → WISH, PREDICT +
  PAUSE (5) → SHOW, NAME broadcast hash join (6) → BREAK, LOOP-PAYOFF (7) → GUARDRAIL (8) → MORAL, check (9).
- Light moments: the driving for a one page list (5), weighing the shops before their diet (7), the phone book (8).

### Accuracy notes for the producer

- All numbers are the lesson's demo: 4 payment partitions of 250,000, 500 shops in 2 partitions, 1,000,500 rows of
  the two tables shuffled (the demo's 1,001,000 records also count 500 partial sums after the join), about 9.4 MB,
  4 stages, best-of-3 times 165 ms (sort-merge) and 91 ms (broadcast). The broadcast join still shuffled 2,000 partial
  sums for the `groupBy` after the join; the video says only "no payment is shuffled".
- "6 minutes → 25 minutes" is the lesson's opening story, not the demo.
- The shuffled hash join, the SQL hint, the left outer join limit and AQE's run-time switch are left to the lesson.
- The shops' file is drawn as one file; in the demo the shops sit in 2 partitions, so two map tasks write files.
- The 3 GB customers table in the check is hypothetical.
