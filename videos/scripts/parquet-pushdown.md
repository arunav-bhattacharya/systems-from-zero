# A label on every box: how a Parquet reader skips rows

- Slug / scene: `parquet-pushdown`, `videos/scenes/parquet_pushdown.py:ParquetPushdown`
- Lesson: `batch-05`, section 2, "The footer's smallest and largest values let a reader skip whole row groups"
- Audience / level: a complete newcomer. Knows a table has rows and columns; knows nothing about Parquet, row
  groups, footers or pushdown.
- Length: 4:39 (~640 words of narration, three pauses, silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=145`, the sorted file after the skip: row groups 0 and 1 dimmed and crossed, the six chunks of groups 2 and 3
  lit, "788,725 of 3,631,674 bytes (22%)"
- The learner's real question: two files hold the same payments; why does the same question read six times more from
  one of them?
- Misconception to steelman and break: "a column file reads only the rows a question needs" (the warm-up). Broken
  by the random file: every row group's range reaches 250,000, so all four are read and 96% of the rows are thrown
  away, with pushdown switched on.
- Concept chain: a Parquet file is row groups of column chunks → the reader skips columns it doesn't need (column
  pruning) → the footer holds each chunk's min and max → a filter compared with them skips whole row groups (predicate
  pushdown) → it only works if the rows are sorted, so each range is narrow (hardest last)
- Analogy family: the lesson's moving boxes. Twenty boxes labelled "books, authors A to C"; the friend's boxes all
  labelled "books"; the footer is every box's label copied onto one sheet; the analogy breaks because a Parquet file
  can't be repacked.
- Open loops: "383 kB or 2.3 MB, for the same 16,200 rows" planted in scene 1 → paid off in scene 6.
- Assumptions: all numbers are the lesson's: 400,000 payments, 4 row groups, sorted ranges 100..63,031,
  63,033..125,677, 125,677..188,240, 188,241..250,099 cents; 788,725 of 3,631,674 bytes (22%); 199,296 rows decoded,
  160,308 match; for `> 240000`: sorted 98,944 rows and 382.7 kB, random 400,000 rows and about 2.3 MB, 16,200 match
  (96% thrown away); merchant_id 0 to 499 in every row group. The four moving boxes and their letter ranges (A to F,
  G to L, M to R, S to Z) are a picture of the lesson's twenty boxes.

## The one picture

Left: the file as a grid. Five columns of chunks (payment, merchant, country, status, amount), four row groups as
rows, the footer as a bar under them. Right of each row: its label, the min and max of `amount` (gold). Read chunks
fill yellow, skipped row groups dim with a red cross, unneeded columns dim grey. Top: the file's name and the query.
Under the footer: the reader's counts. In the opening, the four rows are four moving boxes with paper labels.

## Scene 1 · Moving house · 0:00–0:45 · [QUESTION] [ANALOGY] [LOOP-PLANT]

VO: Picture moving house. You pack your books into twenty boxes, and label each one: books, authors A to C. To find a
cookbook by Moreno, you open one box. A friend packed hers in any order, and labelled every box: books. She opens all
twenty.

Data files have the same problem. Two files hold the same 400,000 payments. Ask both for every payment above 2,400
euros. From one, the reader fetches 383 kilobytes. From the other, 2.3 megabytes. The same 16,200 rows come back. Only
the order of the rows differs. So what is the reader looking at?

SCREEN: Four boxes with labels A to F, G to L, M to R, S to Z; "Moreno" opens the M to R box. The labels change to
"books"; all four open. Then two file names with "383 kB" and "2.3 MB", "16,200 rows each".

## Scene 2 · Inside a Parquet file · 0:45–1:30 · [FAMILIAR] [SHOW] [WISH]

VO: These are Parquet files. Parquet is a file format that stores a table column by column. The rows are cut into
blocks called row groups, here four of about 100,000 rows. Inside a row group, each column sits together, as one
chunk.

A fraud analyst, someone who hunts for stolen cards, asks for three columns of every payment above 1,500 euros. The
reader skips the two columns she didn't name. That's column pruning. But can it skip rows too, before reading them?

SCREEN: The boxes become the four rows of the grid; columns appear with their names. Query chip
`SELECT merchant_id, status, amount_cents ... WHERE amount_cents > 150000`. The payment and country columns dim:
"column pruning: 2 of 5 columns not needed".

## Scene 3 · The footer is the label sheet · 1:30–2:05 · [ANALOGY] [MAP]

VO: It can, with the footer. At the end of the file, the footer lists every chunk: where it starts, how big it is, and
its smallest and largest value, its min and max. Remember the moving boxes? The footer is the label from every box,
copied onto one sheet.

So the reader reads the footer first. In this file, sorted by amount, row group zero holds amounts from 100 to 63,031
cents. Row group one, up to 125,677. Two, up to 188,240. And three, up to 250,099.

SCREEN: The footer bar glows; "offset, size, min, max" for each chunk. A copy of the footer's amount ranges flies to
the label next to each row.

## Scene 4 · Skip by the label · 2:05–3:00 · [PREDICT] [PAUSE] [SHOW]

VO: The analyst wants amounts above 150,000 cents. Which row groups can the reader skip, without reading a byte of
them? Pause and guess.

(three seconds)

Zero and one. Their largest amounts are below 150,000, so no row in them can match. Two and three might, so the reader
fetches them. Six chunks, 788,725 bytes of the file's 3.6 million. About a fifth.

Min and max work on whole row groups, though. Row group two starts at 125,677, below the line. So the reader unpacks
all 199,296 rows of groups two and three, and a filter keeps the 160,308 that match.

SCREEN: A red line at 150,000 against the labels; countdown. Rows 0 and 1 dim with crosses; six chunks fill yellow;
"read: 788,725 of 3,631,674 bytes (22%)". Then "199,296 rows unpacked, 160,308 match".

## Scene 5 · The name · 3:00–3:20 · [NAME]

VO: Checking a filter against these numbers, inside the file reader, is called predicate pushdown. A predicate is a
condition, like amount above 150,000. Pushing it down means handing it from the query to the reader.

SCREEN: Caption "predicate pushdown"; the `WHERE` part of the query chip slides down to the footer.

## Scene 6 · The other file · 3:20–4:10 · [BREAK] [PREDICT] [PAUSE] [LOOP-PAYOFF] [JOKE:release]

VO: Now the other file. Same payments, written in the order they happened. Every row group holds amounts from 100 to
about 250,000. Ask for amounts above 240,000. How many row groups can the reader skip? Pause and guess.

(three seconds)

None. Every label says: maybe. That's the friend's boxes, every one labelled books. The reader unpacks all 400,000
rows, and the filter throws away 96% of them. On the sorted file, it reads one row group of four, 98,944 rows. Same
16,200 answers. Pushdown was on both times. It just had nothing to push against.

SCREEN: The file name becomes `random.parquet`; every label "100..~250,000". Countdown. All rows light; "400,000
rows unpacked, 16,200 match: 96% thrown away; 2.3 MB". Then the sorted labels return, only row 3 lit: "98,944 rows,
16,200 match; 383 kB".

## Scene 7 · Guardrails · 4:10–4:35 · [GUARDRAIL]

VO: So, min and max skip only what sorting made tidy. Sort each file by the column you filter on most. But one sort
tidies one column. In the sorted file, the merchant column still runs from 0 to 499 in every row group.

And here the moving boxes break. You can repack a box when you notice the mess. A Parquet file is never changed once
it's written. To tidy one, you write a new file.

SCREEN: Captions; the merchant column glows with "0..499" in every row. "never changed once written: write a new
file".

## Scene 8 · Moral and check · 4:35–5:00 · [MORAL] [PREDICT] [PAUSE]

VO: The moral: a label only helps if it's narrow, and the order of the rows decides how narrow. One quick check, on the
sorted file. Amounts below 50,000 cents. How many row groups does the reader open? Pause and think.

(three seconds)

One. Row group zero. Row group one starts at 63,033.

SCREEN: Query chip `WHERE amount_cents < 50000`; countdown; row 0 lit, the rest crossed.

---

### Beat check

- QUESTION with the lesson's analogy (scene 1); FAMILIAR (scene 2) before any term but "Parquet", which gets a plain
  sentence first; WISH at the end of scene 2.
- ANALOGY + MAP (scene 3): footer = the label sheet. PREDICT + PAUSE + SHOW (scene 4).
- NAME after the show (scene 5). BREAK of the wrong model with a second prediction (scene 6), loop paid off.
- GUARDRAIL with the analogy's breaking point (scene 7). MORAL and check (scene 8).
- Light moments: the friend's boxes (0:15), "every label says: maybe" and "nothing to push against" (4:00).

### Accuracy notes for the producer

- The 383 kB and 2.3 MB are DuckDB's "Data Read"; the 98,944 and 400,000 rows are Spark's scan. The video says "the
  reader" for both. The 2.3 MB moves a little between runs.
- The 788,725 bytes include only the three named columns in groups 2 and 3 (column pruning and row group skipping
  together).
- The random file's ranges are "100 to about 250,000" as the lesson says; exact values are not shown.
- Left to the lesson: zone maps, the footer length and `PAR1` bytes, `spark.sql.parquet.filterPushdown`, and filters
  that look pushed down but don't skip (next section).
