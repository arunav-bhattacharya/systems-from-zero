# Save it and say it, together: the transactional outbox

- Slug / scene: `cdc-outbox`, `videos/scenes/cdc_outbox.py:CdcOutbox`
- Lesson: `stream-02`, section 3, "The outbox: an event you designed, saved in the same transaction"
- Audience / level: a complete newcomer. Has seen the dual write and a copy that follows a database's log
  (stream-01); doesn't know Debezium, the outbox or at-least-once delivery.
- Length: 4:37 (~700 words of narration, two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=148.5`, the `poster` stamp (pay-3 and its outbox row e-66 committed, BEGIN 771 to COMMIT 771 in the log, the record
  in the topic, the ledger "applied e-66")
- The learner's real question: how do I tell another program about a change exactly when the change is saved, and
  never when it isn't?
- Misconception to steelman and break: "save, then send" is fine (a crash between loses the event; swapped, it
  announces a payment that never saved). Then "just follow the table's changes" (no dual write, but readers get your
  columns and no reason).
- Concept chain: a dual write can lose or invent events → following the table leaks its shape → save the event as a
  row in the same transaction → only committed transactions leave the log → the router names topic, key and id →
  delivery is still at least once, so readers drop repeats (hardest last)
- Analogy family: a carbon-copy form at a shop. One stroke of the pen writes the sale (the payment row) and the
  courier's note underneath (the outbox row); the courier (Debezium) takes only the bottom sheet.
- Open loops: "the event when the row is saved, and never when it isn't" planted in scene 1 → paid off in scene 5
  ("no event without a payment, and no payment without an event") and in the check.
- Assumptions: pay-3, e-66, acct-17, BEGIN/COMMIT 771, pay-4 and e-77 rolled back in 772, and e-88 sent twice are the
  lesson's stepper. pay-4's account acct-42 is from the stepper. The check's pay-5, e-99 and transaction 773 are
  illustrative. The Java and Kotlin helpers `insertPayment` and `insertOutbox` are named for the picture; the JDBC
  calls around them are real.

## The one picture

Top left: the payments program (gold). Left: the database (white) with two tables, `payment` (white) and `outbox`
(yellow). Under it, the database's log as four chips. Bottom right: Debezium (teal), fed by an arrow from the log.
Right: the Kafka topic (blue) with up to three records. Top right: the ledger (green) with a state line. Yellow dots
and colours mark outbox events; red marks a crash, a lost or invented event, or a repeat.

## Scene 1 · The question · 0:00–0:35 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: The payments program has just authorized a payment, pay-3: the bank has set the money aside. It saves the
payment's row in its database, PostgreSQL. Now the ledger, the program that books every movement of money, needs to
hear about it. The message is an event called PaymentAuthorized. It travels through Kafka, a program that keeps
streams of messages in order, for other programs to read. So how do we get the event out exactly when the row is
saved, and never when it isn't?

SCREEN: The program saves "pay-3 AUTHORIZED" into the payment table. The ledger appears ("waiting to hear"), then the
Kafka topic with an arrow up to the ledger. Caption: "the event when the row is saved, and never when it isn't".

## Scene 2 · Save, then send · 0:35–1:20 · [PAIN] [BREAK] [JOKE:release]

VO: The obvious way: save the row, then send the event. But that's a dual write, two writes to two systems with
nothing tying them together. Crash between the lines, and the payment is saved, but the ledger never hears. Swap the
lines, and it's worse. Send first, then crash before the save, and the ledger books a payment that doesn't exist. So
one order loses news, and the other spreads rumours. Neither is what a ledger wants. Two systems, and no all or
nothing between them.

SCREEN: Save arrow, then a send arrow straight to the topic. A red "crash" on it; the ledger turns red, "never heard
of pay-3". Then send first: a record lands, the ledger "booked pay-3", a crash on the save, "no such payment" in the
table, the ledger "a ghost".

## Scene 3 · Follow the table instead · 1:20–2:00 · [BREAK] [WISH]

VO: Second try: don't send at all. Let Debezium, a program that reads a database's log and turns each change into a
message, follow the payment table. No dual write now. But every reader gets your table's columns, so renaming one
breaks them. And the message says only what the row became. Captured? Or someone fixing a mistake? It can't say why.
What we want is an event we designed, saved together with the row, so both happen or neither does.

SCREEN: Debezium and the log appear. An UPDATE of pay-3 runs through Debezium to the topic as "row pay-3:
status=CAPTURED", then a red "why?".

## Scene 4 · The carbon-copy form · 2:00–2:50 · [ANALOGY] [MAP]

VO: Think of an old carbon-copy form at a shop. You write the sale on the top sheet, and the same stroke of the pen
writes the courier's note on the sheet underneath. One can't exist without the other. And the courier takes only the
bottom sheet, the one written for the courier.

Map it. The top sheet is the payment row. The bottom sheet is a second row, in a table called outbox, written for the
readers. The one stroke is a single database transaction, a group of changes saved all together, or not at all. And
the courier is Debezium, reading only the outbox.

SCREEN: The diagram dims; two sheets, one pen stroke drawn on both; the bottom sheet slides away with the courier.
Back on the diagram: the payment table pulses, the outbox table appears, a dashed outline "one transaction" around
both, Debezium pulses.

## Scene 5 · Watch the log · 2:50–3:40 · [SHOW] [PREDICT] [PAUSE] [LOOP-PAYOFF]

VO: Watch the log. BEGIN, transaction 771. Insert the payment row. Insert the outbox row, event e-66 for account
acct-17. COMMIT. Debezium reads the committed transaction and picks up only the outbox insert.

Now a second payment, pay-4, with its outbox row e-77. The program crashes before commit, so the database rolls it
back. Does e-77 reach Kafka? Pause and guess.

(three seconds)

No. Its rows were in the log, but the log reader hands out only committed transactions. No event without a payment,
and no payment without an event.

SCREEN: Log chips BEGIN 771, payment pay-3, outbox e-66, COMMIT 771 as the rows appear. A dot runs to Debezium; only
the outbox chip lights; "PaymentAuthorized e-66" lands in the topic; the ledger "applied e-66". Then BEGIN 772 ...
ROLLBACK 772 in red, the rows vanish, countdown, "sees nothing" under Debezium.

## Scene 6 · The name, and the router · 3:40–4:15 · [NAME]

VO: This is called the transactional outbox. Debezium's outbox router turns each outbox row into a Kafka record. The
topic comes from the row's kind, payment. The key is the account, acct-17, so each account's events stay in order.
And the event's id, e-66, travels along in a header. The program can even delete the outbox row in the same
transaction. The router ignores deletes, so the table stays empty.

SCREEN: Title "the transactional outbox". Debezium becomes "Debezium + outbox router"; the topic shows
`outbox.event.payment`; the record becomes "key acct-17 | id e-66". The outbox row fades: "the outbox stays empty".

## Scene 7 · Two guardrails · 4:15–5:00 · [GUARDRAIL]

VO: Why not a small program that checks the outbox table every second? It costs a query every second, and it can skip
a row whose transaction commits late. The log hands out transactions in commit order, so nothing slips past.

One thing the outbox doesn't fix. Debezium saves its place in the log only about once a minute. Say e-88 reaches
Kafka, and Debezium dies before the next save. After a restart, it reads from the old place and sends e-88 again,
with the same id. So the ledger keeps the ids it has applied, and drops repeats. Delivery is at least once, never
exactly once for free.

SCREEN: Captions for the poller. "saved place: after e-66" under Debezium; e-88 runs to the topic and the ledger;
Debezium turns red; after the restart a second e-88 record in red; the ledger "e-88 again: dropped".

## Scene 8 · The code, the moral, a check · 5:00–5:45 · [MORAL] [PREDICT] [PAUSE]

VO: In Java and Kotlin, it's one transaction with two inserts, and one commit. Publish what you meant, not what your
table looks like, and write it in the same transaction.

One quick check. A payment and its outbox row commit, and the program crashes a moment later. Does the ledger hear
about it? Pause and think.

(three seconds)

Yes. The commit is in the log, and Debezium reads it, whether the program is alive or not.

SCREEN: Java and Kotlin side by side (`setAutoCommit(false)`, two inserts, `commit()`), with the inserts and the commit
highlighted. Then the moral as a caption. For the check: BEGIN 773 ... COMMIT 773, a red crash on the program,
countdown; e-99 runs through Debezium to the topic and the ledger, a green tick.

---

### Beat check

- Opens with QUESTION (scene 1) on a real need; FAMILIAR is the dual write from the last lesson (scene 2).
- BREAK twice before the analogy: save-then-send and send-then-save (scene 2), and plain CDC (scene 3), then the WISH.
- ANALOGY + MAP (scene 4), PREDICT + PAUSE + SHOW (scene 5, and the check in scene 8).
- NAME after the SHOW (scene 6). GUARDRAIL (scene 7: the poller's trap; at-least-once) and MORAL (scene 8) last.
- Light moment: "one order loses news, and the other spreads rumours" (scene 2).

### Accuracy notes for the producer

- The lesson's stepper: BEGIN 771, INSERT payment pay-3, INSERT outbox e-66 acct-17, COMMIT 771; a second transaction
  772 (pay-4, e-77, acct-42) rolls back and Debezium sees nothing; e-88 is written twice after a crash before the
  offset flush. The video drops LSNs and the replication slot, and calls the offset "its place in the log".
- The router's mapping (topic `outbox.event.<aggregatetype>`, key `aggregateid`, value `payload`, header `id`) is the
  lesson's. The video says "the row's kind" for `aggregatetype` and "the account" for `aggregateid`.
- Debezium runs inside Kafka Connect; the lesson says Connect flushes the offset about once a minute. The video keeps
  one name, Debezium.
- Kafka's own transactions and KIP-939 (from the section) are left out for length.
- In the check, the program's crash after COMMIT doesn't matter, because the committed rows are in the log; Debezium
  reads them whenever it next runs.
