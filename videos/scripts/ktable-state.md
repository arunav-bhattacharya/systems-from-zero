# The box of cards and the notebook in the safe: where a Kafka Streams table lives

- Slug / scene: `ktable-state`, `videos/scenes/ktable_state.py:KTableState`
- Lesson: `stream-05`, section 1, "The table lives on local disk, and a changelog topic backs it up"
- Audience / level: a complete newcomer. Has paid for a coffee and kept a tab; met a Kafka topic as a log of
  records; knows nothing about state stores, RocksDB, changelogs or compaction.
- Length: 5:47 (~900 words of narration, three pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=217` (the restore done: store rows 75.00 and 30.00, a changelog of five lines, saved place 4)
- The learner's real question: the balances live in the program, so what happens to them when the computer dies,
  and how do they come back without reading every payment again?
- Misconception to steelman and break: (1) "after a restart, just read every payment again" (1.8 billion records,
  five hours, and old payments already deleted); (2) "the changelog is compacted, so a restore of 10 accounts reads
  10 lines" (the demo restores 1,000: compaction never touches the newest segment).
- Concept chain: balances in memory vanish on a restart → keep the table on local disk next to the code, and write
  every change to a log in Kafka → the store overwrites, the changelog only appends → a lost disk is rebuilt from the
  changelog, then the payments carry on from the saved place → the wait grows with the store; a standby keeps a warm
  copy (hardest last)
- Analogy family: the lesson's café. A box of cards by the till, one per regular, the amount owed in pencil (the
  store); a notebook in the office safe where the owner writes each new total, "Sam owes 12.50" (the changelog); the
  till receipts (the payments); a second café keeping its own box from a copy of the notebook (a standby replica).
- Open loops: "where should the table live, so a restart costs minutes and not hours?" planted in scene 1 → scene 5;
  "the notebook only needs the latest line" voiced in scene 6 → broken there.
- Assumptions: all numbers are the lesson's (2 million balances, 3,000 a second, 1.8 billion records and five hours;
  the stepper's five payments on partition 0 and the store and changelog values; the Try it's 1,000 payments for
  10 accounts and 1,000 restored records; 50 GB at 100 MB a second, more than 8 minutes; `num.standby.replicas=1`).
  Sam's 12.50 is the lesson's notebook line; the café's other cards are blank.

## The one picture

Top: partition 0 of `payments`, five blue records with their offsets, and a yellow "saved place" bookmark under the
next record to read. Bottom left, gold: first the café's box of cards, then "this computer's disk" with the store
`balances` (RocksDB) and one row per account. Bottom right, teal: first the notebook in the safe, then the changelog
topic in Kafka, one cell per change with its offset. Yellow dots carry each payment into the store and each change
into the changelog. Red marks the lost disk. Captions at the bottom.

## Scene 1 · The box by the till · 0:00–0:50 · [QUESTION] [FAMILIAR] [PAIN] [JOKE:amplify] [LOOP-PLANT]

VO: Picture a café that lets its regulars pay at the end of the month. By the till sits a box of cards, one per
regular, with the amount owed in pencil. Sam buys a coffee, the owner finds Sam's card, and changes one number. It's
fast.

Now make that box a program. Kafka is a program that keeps logs of records for other programs to read, and here it
hands our program every card payment, 3,000 a second. The program keeps 2 million balances in memory, and adds each
payment as it comes.

One night the computer restarts. Memory is wiped, and every balance is gone. To get them back, the program must read
every payment again from the start. A week of payments is 1.8 billion records, about five hours of reading.

The tests never caught this. Tests never restart halfway through. So where should the table live, so that a restart
costs minutes and not hours?

SCREEN: Title card. A gold box of cards; Sam's card "Sam owes 12.50" lifts and its number changes. The box turns
into "the program's memory: 2 million balances"; a red flash, "empty". Captions "read every payment again: 1.8
billion records, about five hours". The question in white.

## Scene 2 · The notebook in the safe · 0:50–1:25 · [WISH] [ANALOGY] [MAP]

VO: Back to the café. Each time the owner changes a card, she also writes the new total as a line in a notebook:
Sam owes 12.50. And she keeps the notebook in the office safe. Lose the box, and she rebuilds every card from the
notebook. She never touches the till receipts.

Map it out. The box of cards is the table, kept on the program's own disk, right next to the code. The notebook is a
second log in Kafka, with one line for every change. And the till receipts are the payments themselves.

SCREEN: The gold box is back; a teal notebook appears on the right with a line "Sam owes 12.50" written as the card
changes. A red cross over the box; dots run from the notebook lines back into fresh cards. Captions "box of cards =
the table, on the program's own disk", "notebook = a log in Kafka, one line per change", "till receipts = the
payments".

## Scene 3 · The names · 1:25–1:55 · [NAME]

VO: Kafka Streams, a library you add to your own program, builds exactly this. It keeps the box of cards in a state
store, RocksDB by default. RocksDB is a small database that keeps a value under each key, in files on the local
disk. A read or a write takes microseconds. Every write to the store also goes to a Kafka topic called the changelog. That's the notebook.

SCREEN: The box becomes "this computer's disk" with "store: balances (RocksDB)"; the notebook becomes "Kafka" with
"changelog topic". Captions name each.

## Scene 4 · Four payments · 1:55–2:55 · [SHRINK] [SHOW]

VO: Kafka splits the payments into separate logs called partitions. Let's follow just one, partition 0, with five
payments. Offset 0: acct-1 pays in 100.00. There's no row yet, so it starts at 0 and becomes 100.00. The new value
goes into the store, and the same line goes into the changelog. Offset 1: acct-2 pays in 50.00. A new key, so a new
row, and a new line. Offset 2: acct-1 pays 30.00. Its row changes from 100.00 to 70.00, in place. But a log never
changes a line, so the changelog adds acct-1 = 70.00 at the end. Offset 3: acct-1 pays in 5.00 and reaches 75.00.
Then the program commits: it saves its place on payments as 4, the next record to read. Notice the two shapes. The
store keeps one row per account. The changelog keeps every change, in order.

SCREEN: The partition row with offsets 0 to 4 and the bookmark "saved place: 0". Each payment pulses, a dot runs to
the store, its row appears or changes, a dot runs on to the changelog and a cell appears with its offset. Old cell 0
dims when 70.00 arrives. The bookmark jumps to 4.

## Scene 5 · The bad night · 2:55–3:45 · [PREDICT] [PAUSE] [SHOW] [LOOP-PAYOFF]

VO: Now, the bad night. The computer dies, and its disk goes with it. The work moves to another computer with an
empty disk. Before it handles payment 4, what does it do? Pause and guess.

(three seconds)

It reads the changelog from the beginning into a fresh store, oldest first: 100.00, then 50.00, then 70.00, then 75.00. For each
account, the last line wins. So acct-1 is 75.00, and acct-2 is 50.00. Only then does it carry on with the payments,
from the saved place, 4. acct-2 pays 20.00 and goes down to 30.00. Nothing came from the old disk. The payments, the
changelog and the saved place all live in Kafka. Four lines to read, not five hours.

SCREEN: The disk box turns red, "empty: the disk is gone", then grey "a new computer: empty disk". Countdown. Dots
run from each changelog cell, oldest first, into the store; acct-1's row shows 100.00, then 70.00, then 75.00.
Payment 4 pulses; acct-2 becomes 30.00; a fifth changelog cell appears.

## Scene 6 · Ten accounts, ten lines? · 3:45–4:25 · [BREAK] [PREDICT] [PAUSE] [JOKE:release]

VO: You might be thinking: the notebook only needs the latest line per account. Kafka can clean a log down to that.
It's called compaction, and the changelog has it switched on. So the lesson's demo adds up 1,000 payments for 10
accounts, then deletes the local store. How many records does the restore read? Pause and guess.

(three seconds)

1,000. Every update. Compaction never touches the newest file of a log, the one still being written, and this
changelog is young. Well... so much for ten. The balances came back right, just more slowly.

SCREEN: Caption "compaction: keep only the latest line per key"; the two out-of-date cells dim. A demo panel
"1,000 payments, 10 accounts; delete the local store". Countdown. Output line `run 2: restored 1000 records`.
Caption "compaction never touches the newest file".

## Scene 7 · The wait, and a second café · 4:25–5:20 · [GUARDRAIL]

VO: So the wait grows with the store. 50 GB, read at 100 MB a second, is more than 8 minutes, and that partition's
payments wait. One setting shortens it: num.standby.replicas, set to 1. Another copy of the program keeps a warm store
by reading the changelog all the time. That's a second café keeping its own box from a copy of the notebook. After a
failure, only the last few lines need replaying. The café picture breaks at scale: one box for the owner, but here one
slice of the table per partition, and thousands of lines a second.

Here it is in Java and Kotlin. groupByKey and aggregate are the fold: start at 0, add each payment. Materialized.as
names the store, and the changelog comes with it. One setting asks for the standby.

SCREEN: Caption "a 50 GB store at 100 MB a second: more than 8 minutes". A dashed box inside the disk box, "standby on
another computer: a warm copy", with a dot stream from the changelog. Then the diagram dims and two code panels, Java and Kotlin, with
the fold, the store name and the standby setting highlighted in turn.

## Scene 8 · The moral, and a check · 5:20–5:55 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So the moral of the story: keep the table next to the code for speed, and write every change to a log that
outlives the disk. The box of cards is fast. The notebook is what you trust. One quick check. acct-1 pays in 10.00
more. What changes in the store, and what changes in the changelog? Pause and think.

(three seconds)

The store overwrites one row: acct-1 becomes 85.00. The changelog adds one line at the end: acct-1 = 85.00.

SCREEN: Diagram restored; moral in yellow. A new payment "acct-1 +10" arrives; countdown; the row changes to 85.00
and a sixth cell joins the changelog. Last caption "fast copy on the disk, every change in the log".

---

### Beat check

- Opens with QUESTION and FAMILIAR (scene 1), PAIN with numbers and the light moment about tests (scene 1).
- WISH, ANALOGY and MAP said out loud (scene 2), before any name. NAME (scene 3) after the analogy.
- SHRINK and SHOW (scene 4); PREDICT with PAUSE three times (scenes 5, 6, 8).
- BREAK twice: "read every payment again" (scene 1) and "compaction means ten lines" (scene 6).
- GUARDRAIL with the cost and the standby, and the analogy's breaking point (scene 7). MORAL and check (scene 8).

### Accuracy notes for the producer

- The five payments and every store and changelog value are the lesson's stepper; the commit saves offset 4.
- The changelog's name is `<application.id>-balances-changelog`, created with `cleanup.policy=compact`; the video
  says "a Kafka topic called the changelog".
- The Try it's run 2 prints `restored 1000 records` for 10 accounts with the record cache off
  (`statestore.cache.max.bytes=0`); with the default 10 MiB cache, updates to one key between commits are merged,
  so fewer records reach the changelog. The video leaves the cache out.
- The table's changes also go to the `balances` output topic; the video leaves that out.
- The check (acct-1 + 10.00 → 85.00) is a hand-picked next payment, not from the lesson.
- The code panels trim the serdes and the store's type arguments; the lesson's listing has them in full.
- A crash between processing and committing can count a payment twice; the lesson's last section and
  `exactly_once_v2` cover it. The video's restore happens after a clean commit at 4, so it doesn't arise.
