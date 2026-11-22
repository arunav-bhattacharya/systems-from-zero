# Ink the whole batch, or none of it: a Kafka transaction

- Slug / scene: `kafka-transactions`, `videos/scenes/kafka_transactions.py:KafkaTransactions`
- Lesson: `msg-10`, section 1, "One transaction holds the entries and the bookmark"
- Audience / level: a complete newcomer. Can read a little code; doesn't know Kafka, offsets, producers or transactions.
- Length: 5:32 (~870 words of narration, plus three pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=221` (right after the commit: six entries and the bookmark inked, ABORT and COMMIT markers in place)
- The learner's real question: the program crashed between writing the entries and moving its bookmark. How do you stop
  the next copy writing four payments twice?
- Misconceptions to steelman and break: (1) "the idempotent producer drops repeats", broken by the new copy being a new
  producer with a new id; (2) "pencil means nothing is in the log yet / an abort deletes", broken by `send` putting the
  records in the log before the decision, and the abort only adding a marker; (3) "every reader sees only committed
  data", broken by the default `read_uncommitted` reader seeing all ten (and the closing check: all 14).
- Concept chain: two separate writes → a crash between them repeats work → one write for both (a transaction) → a
  coordinator, a transactional id, five calls → markers decide, readers must trust only ink → rewind after an abort, keep
  transactions short (hardest last)
- Analogy family: the lesson's address book, copied with a sticky note; pencil, one ink stamp, crossed out; a visitor who
  trusts only ink.
- Open loops: "how many addresses in the new book?" planted in scene 1 → 10; "how do you stop four entries landing
  twice?" planted in scene 2 → scene 10.
- Assumptions: numbers and outcomes are the lesson's demo (6 payments, instance 1 writes pay-0 to pay-3 and dies,
  instance 2 starts at offset 0, `read_uncommitted` sees 10, `read_committed` sees 6, committed offset 6). The names Ana
  to Finn are made up for the address book. `ledger-0` is the lesson's example id.

## The one picture

Top: `payments` (six blue cells) with the gold sticky note (the bookmark) under it; the ledger program box; the purple
coordinator box (`__transaction_state`). Middle: `ledger-entries`, up to 12 cells. Lower: `__consumer_offsets` (offset
0, then offset 6 and its COMMIT marker). Bottom: two reader chips. Yellow = a repeat, dashed grey = pencil (sent but
undecided), green = ink (committed), red = aborted, gold = a marker.

## Scene 1 · The address book · 0:00–0:50 · [QUESTION] [FAMILIAR] [PREDICT] [PAUSE] [SHOW]

VO: Picture copying the addresses from an old address book into a new one. You keep your place with a sticky note.
You've copied four when the doorbell rings. While you're away, a friend carries on from the sticky note, which still
marks the start. The friend copies from the note to the end. How many addresses are in the new book now? Pause and guess.

(three seconds)

Ten, for six people. Four of them twice. Nobody did anything wrong. The sticky note stayed behind the work.

SCREEN: Title card. Six names in the old book, the program box ("you"), the sticky note. Four copies run down; "ding
dong"; "a friend"; six more copies; countdown; the eight repeats outlined in yellow; "10 addresses for 6 people".

## Scene 2 · The payments program · 0:50–1:35 · [MAP] [PAIN]

VO: The café payments program does the same. It reads card payments from Kafka, a program that keeps logs of messages
for other programs to read. For each payment, it writes a ledger entry, a line in the book of money movements, to a log
called ledger-entries. Then it moves its bookmark. Kafka keeps that bookmark in a log of its own. So these are two
separate writes, often on different machines, and nothing ties them together. A crash in between, and the lesson's demo
ends with 10 entries for 6 payments.

SCREEN: The names become pay-0 to pay-5 (blue); the copies become ledger entries (pay-0 to pay-3 twice, yellow); "bookmark:
0"; the `__consumer_offsets` row with "offset 0"; two white dots leave the program for the two logs.

## Scene 3 · The idempotent producer? · 1:35–2:05 · [BREAK] [JOKE:release] [WISH]

VO: You might be thinking: Kafka has an idempotent producer, which drops repeats. It drops one kind: the same producer
sending the same batch twice. The friend who took over is a new producer with a new id. To Kafka, its four entries are
brand new. Same face, total stranger. What we want is for the entries and the bookmark to be one write. All of it, or
none of it.

## Scene 4 · Pencil and ink · 2:05–2:40 · [ANALOGY] [MAP] [NAME]

VO: Back to the address book. Suppose you copy each address in pencil, and move the sticky note in pencil too. At the
end of the batch you either ink the whole lot with one stamp, or cross the whole lot out. A visitor who trusts only ink
never sees half a batch. That's a transaction: a group of writes that count together or not at all. Kafka needs three
things to do it.

SCREEN: Three dashed (pencil) entries and a dashed note; they turn green ("one stamp"), then red ("crossed out").

## Scene 5 · Three things, and the first three calls · 2:40–3:40 · [SHOW] [NAME] [BREAK]

VO: First, a referee who remembers which logs a transaction touched, and how it ended. Kafka calls it the transaction
coordinator. One of Kafka's servers takes on the job, and keeps its notes in a log of its own. Second, a name for each
copy of the program, such as ledger-0. It's called the transactional id, and it stays the same across restarts, so
Kafka knows the next copy is the same program. Third, five calls, in order. Let's replay the crash with them.
initTransactions, once at start-up: the copy registers its name with the coordinator. beginTransaction: from now on,
everything it sends belongs to the transaction. Then send. Here's the surprise. The entries go into the log straight
away, before anything is decided. They're in pencil, but they're in. And now the crash. Instance 1 dies with four
entries in pencil.

SCREEN: The coordinator box; "id: ledger-0"; each call appears under the program as it's said; four dashed entries;
"records reach the log before the decision"; a red cross on the program.

## Scene 6 · Instance 2, and the stamp · 3:40–4:45 · [SHOW] [JOKE:reward]

VO: Instance 2 starts with the same name. Its initTransactions reaches the coordinator, which finishes what the older
copy left open. It aborts it. An abort deletes nothing. It adds a marker after the four, a small record that tells
careful readers: skip what came before. Instance 2 begins, reads from the bookmark at 0, and sends six entries, in
pencil. sendOffsetsToTransaction: the bookmark joins the transaction. It's in pencil too, and the program has turned
off saving it on its own. commitTransaction. The coordinator writes its decision in its notes. Then it puts a COMMIT
marker into every log the transaction touched: the entries, and the bookmark's log too. One stamp, and the whole batch is
in ink. The most powerful rubber stamp in the building. So the point is: one decision makes six entries and a bookmark
count together.

SCREEN: "ledger-0's open one: abort"; an ABORT marker after the four, which turn red; six dashed entries; a dashed
"offset 6"; "enable.auto.commit=false"; "ledger-0: commit"; COMMIT markers in both logs; everything of the batch turns
green; the sticky note reads "bookmark: 6".

## Scene 7 · What readers see · 4:45–5:15 · [PREDICT] [PAUSE] [SHOW] [GUARDRAIL]

VO: So ledger-entries holds ten entries. How many does a reader see? Pause and guess.

(three seconds)

It depends on the reader. A careful reader, set to read_committed, skips the aborted four and sees six, each payment
once. A reader left on the default, read_uncommitted, sees all ten. So every program that reads ledger-entries must ask
for read_committed, or the transaction protects nothing.

## Scene 8 · Two habits · 5:15–5:45 · [GUARDRAIL]

VO: Two more habits. After an abort, seek back to the first record of the batch. Reading the batch already moved the
program's position past it. Without the seek, the next read skips the batch, and it's never written at all. And keep
transactions short, one batch each. Every transaction costs a few extra round trips to the coordinator, so one per
record is slow. And while one is open, the careful readers wait.

## Scene 9 · The code · 5:45–6:05 · [SHOW]

VO: Here's one batch, in Java and in Kotlin. Begin, send the entries, send the bookmark, commit. If anything fails,
abort, and seek back. But catch ProducerFencedException first: it means a newer copy has taken over the name, so this
one must stop.

SCREEN: The lesson's batch in two panels, Java left, Kotlin right; lines light as read.

## Scene 10 · The moral, and a check · 6:05–6:45 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, how do you stop four entries landing twice? Make the entries and the bookmark one write. Everything goes in
pencil, then one stamp inks it all, or one marker crosses it all out. And every reader trusts only ink. One quick check.
A program writes 14 entries in a transaction, then aborts. Another program reads the topic with Kafka's default
settings. What does it see? Pause and think.

(three seconds)

All 14. The abort only added a marker, and the default reader doesn't look at markers. Set read_committed.

---

### Beat check

- QUESTION + FAMILIAR + PREDICT (scene 1) in the address book before any Kafka word; MAP (scene 2).
- BREAK: the idempotent producer (scene 3), pencil means "not in the log" (scene 5), the default reader (scene 7, 10).
- ANALOGY (pencil and ink, scene 4) before NAME (transaction, coordinator, transactional id, markers, read_committed).
- GUARDRAIL: read_committed everywhere, rewind, short transactions (scenes 7 and 8). MORAL and RECAP last.
- Light moments: "same face, total stranger", "the most powerful rubber stamp in the building".

### Accuracy notes for the producer

- The demo's outcome (10 entries in the log; `read_committed` sees 6, `read_uncommitted` 10; instance 2 starts at offset 0
  and commits offset 6) is the lesson's `LedgerDemo txn` expected output.
- The ABORT marker for instance 1's open transaction is written when instance 2's `initTransactions()` makes the
  coordinator finish it (the lesson: "finishes anything an older copy with this id left open"). The epoch and producer id
  are left out.
- The coordinator writes the decision to `__transaction_state` first, then the markers; markers take offsets.
- One partition of `ledger-entries` is drawn; the lesson's program may write to several, each getting a marker.
- The code is the lesson's batch with the type of `r` written as `var` and shorter comments; `nextOffsets` and `rewind`
  are the lesson's helpers. The 4.0 `TimeoutException` rule and the last stable offset are left to later sections.
- Ana to Finn are invented names for the address book.
