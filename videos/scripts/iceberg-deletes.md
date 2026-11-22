# 30 refunds in ink: copy the page or pin a slip

- Slug / scene: `iceberg-deletes`, `videos/scenes/iceberg_deletes.py:IcebergDeletes`
- Lesson: `batch-12`, section 0, "Correcting rows in files that never change: rewrite the file or note the delete"
- Audience / level: a complete newcomer who has seen that an Iceberg table's files are never edited.
- Length: about 4.5 min (~780 words)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: merge-on-read after one batch: three day files, each with a small green data file and a red delete slip
- The learner's real question: the command looks like an ordinary UPDATE, so why can 30 changed rows cost megabytes,
  or cost something at every read?
- Misconception to steelman and break: "changing 30 rows costs about 30 rows". Broken by copy-on-write (299,970
  unchanged rows copied) and then by merge-on-read's reader bill (9 files, then 33).
- Concept chain: Parquet files can't be edited → copy the whole file (copy-on-write) → write the change and a note of
  what to skip (merge-on-read, position deletes) → the reader pays on every read → deletion vectors trim the bill →
  choose by how often changes come (hardest last)
- Analogy family: the lesson's notebooks in pen, one page per day: copy the page out, or pin a slip of corrections
- Open loops: "copy the page or pin a slip?" planted in scene 1 → answered as a rule in scene 8
- Assumptions: numbers are the lesson's demo (three daily files of 100,000 rows, 30 refunds, 10 per day; 3.1 MB and
  299,970 rows copied; 6.4 KB plus 7.4 KB; 3 files become 9; after five batches 33; v3: 3 vectors in a 1.7 KB file).
  The 5-minute feed and 512 MB files are the lesson's illustration.

## The one picture

Three day files (blue boxes with ink lines) in a row, the refunded rows marked red. Under each, room for a small new
data file (green) and a delete file (red slip). A counter line under them, notes on the right, caption at the bottom.
The same boxes are the notebook pages at the start (gold).

## Scene 1 · Ink · [QUESTION] [ANALOGY] [LOOP-PLANT]

VO: Picture a shop that keeps its sales in notebooks, in pen, one page per day. One evening, 30 refunds come in, 10
from each of the last three days. You can't rub out ink. So what do you do? Copy the three pages out again, with the
changes? Or leave them alone, and pin a slip of corrections to each? Hold that choice.

SCREEN: Three gold pages with ink lines; red marks on each; a ghost copy beside one page; a red slip pinned to another.

## Scene 2 · The ordinary way · [FAMILIAR]

VO: A payments company meets exactly this. Every evening, a file of refunds arrives: 30 payments whose status must
change from captured to refunded. In an ordinary database, the program that stores tables and answers questions about
them, one UPDATE command changes the 30 rows in place. Done.

SCREEN: The pages become "day 1: 100,000 rows" and so on (blue). Caption: the UPDATE line, then "30 rows changed in place".

## Scene 3 · Files that can't change · [PAIN] [MAP]

VO: But our table is an Iceberg table. Apache Iceberg is a free format for tables made of plain files, and those
files are never edited. The rows sit in Parquet files, a common file format for tables stored by column. The columns
are squeezed, and a summary at the end of the file records where each one sits, and its smallest and largest values.
Change one value, and all of that is wrong. So the file is the page in ink. Every change is written as new files, and a
commit, a new snapshot of the table, makes them visible. The command is MERGE INTO. It matches the refunds to the
table on the payment number. Under it, there are two ways to write the files.

## Scene 4 · Copy the page out · [PREDICT] [PAUSE] [SHOW] [NAME] [BREAK]

VO: Way one: copy the page out. Find every file that holds a row to change, read it whole, and write a new copy with
the change made. The commit swaps the old files for the new ones. To change 30 rows, how many unchanged rows did it
copy? Pause and guess. (three seconds) 299,970. Three whole files, 3.1 MB, rewritten for 30 rows. This is called
copy-on-write, and it's Iceberg's default. Readers notice nothing, because the table is still just plain data files.
But it breaks when changes are small and frequent. Corrections every 5 minutes, against files of 512 MB, and you're
rewriting gigabytes an hour to change a few hundred rows. That's copying out the whole notebook to fix one smudge.

SCREEN: A scan line sweeps each file; a fresh copy replaces it with green rows; counter "written 3.1 MB, copied
299,970 unchanged rows". Then "every 5 minutes × 512 MB files: gigabytes an hour".

## Scene 5 · Pin a slip · [SHOW] [NAME]

VO: Way two: pin a slip. Back to the original files, and leave them alone. Write the new versions of the 30 rows into
small new data files, plus delete files that say which old rows no longer count. Each line of a delete file names a
data file and a row position in it, such as row 1,000 of the day 1 file. That's called a position delete. The same 30
refunds wrote 6.4 KB of new rows and 7.4 KB of delete files. About 14 KB, instead of 3.1 MB. This is merge-on-read.

SCREEN: Three small green files and three red slips under the day files; one slip opens to
"day 1 file, row 0 / row 1,000 / row 2,000"; counter "written 6.4 KB + 7.4 KB".

## Scene 6 · The reader's bill · [BREAK] [JOKE:release]

VO: And here's the catch. The cost moved to the reader. Every read of a data file must also read its delete files, and
skip the rows they list. One batch turned 3 files into 9. Here the notebook picture breaks. You'd read a slip once and
remember it. The table's readers apply every delete file again, on every read. And corrections keep coming. After five
batches, each day has 5 small data files and 5 delete files, and every read opens 33 files. That's a lot of slips for
one page.

SCREEN: A reader's dot visits 9 files ("a read opens 9 files"); then stacks of five behind each small file and slip:
"after 5 batches: 33 files per read".

## Scene 7 · Deletion vectors · [SHOW] [NAME]

VO: Iceberg's format version 3 trims part of that bill. It keeps one bitmap per data file, a row of bits with a 1 for
each deleted row, called a deletion vector. A later delete in the same file joins the same bitmap, so a reader loads at
most one per data file. In the demo, all three vectors fit in one 1.7 KB file.

SCREEN: The slip stacks fold into one purple bitmap per day file ("0 1 0 ... 1"); "3 vectors, one 1.7 KB file".

## Scene 8 · Which way · [GUARDRAIL] [LOOP-PAYOFF]

VO: So, copy the page or pin a slip? You choose per table, and per kind of change, with settings such as
write.merge.mode. Rare, large changes: copy-on-write. Frequent, small ones: merge-on-read. And remember that merge-on-read
sends its readers a bill, which a cleanup job, called compaction, has to pay later.

SCREEN: The setting line; two rule cards.

## Scene 9 · Moral and check · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So the moral of the story. A file that can't be edited leaves two choices. Copy the page, and pay once, when you
write. Or pin a slip, and pay a little every time you read. One quick check. A table gets a batch of corrections every
five minutes, and a report reads it once a night. Which way? Pause and think. (three seconds) Merge-on-read. The changes
are small and frequent, and the reader comes only once a night. Just tidy the slips away now and then.

---

### Beat check

- QUESTION + ANALOGY (1) → FAMILIAR (2) → PAIN, MAP (3) → PREDICT + PAUSE, SHOW, NAME copy-on-write, BREAK (4) →
  SHOW, NAME merge-on-read (5) → BREAK of the analogy and the reader bill (6) → NAME deletion vectors (7) →
  GUARDRAIL, LOOP-PAYOFF (8) → MORAL, check (9).
- Light moments: the whole notebook for one smudge (4), a lot of slips for one page (6), tidy the slips (9).

### Accuracy notes for the producer

- Demo (lesson): copy-on-write v2 wrote 3 data files (3.1 MB), dropped 3, copied 299,970 unchanged rows; reader opens
  3 files. Merge-on-read v2 wrote 3 data files (6.4 KB) and 3 delete files (7.4 KB); reader opens 6 data and 3 delete
  files. Merge-on-read v3 wrote 3 data files (6.9 KB) and 1 delete file (1.7 KB) holding 3 deletion vectors. The
  printed position deletes are rows 0, 1,000 and 2,000 of the day 1 file.
- "After five batches, 33 files per read" is from the lesson's stepper.
- Equality deletes, the worked `MERGE INTO`, and the separate `write.update.mode` and `write.delete.mode` settings are
  left to the lesson. Deletion vectors live in Puffin files; the video says "one file".
- The 10 refunded rows per file are drawn as a few red ink lines.
