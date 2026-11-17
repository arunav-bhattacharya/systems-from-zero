# Paid twice for one coffee? Let the unique index decide

- Slug / scene: `upsert-race`, `videos/scenes/upsert_race.py:UpsertRace`
- Lesson: `sql-09`, section 2, "Check first, then insert: how one message gets stored twice"
- Audience / level: a complete newcomer. Has met a table, a row and INSERT in earlier lessons; knows nothing about
  messages, workers or transactions.
- Length: 4:51 (~760 words of narration at the Kokoro voice's ~180 wpm, plus a guess, a check and the silent
  moves)
- Poster: the default, 82% in (the ON CONFLICT replay: A's row committed, B's repeat skipped, one payment)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: looking before you write feels careful. How can "check, then insert" store one
  payment twice?
- Misconception to steelman and break: "if I check first, I can't insert a duplicate". Broken by the guess in
  scene 3: both checks run before either insert, so both see 0.
- Concept chain: a message can arrive twice → a unique code spots a repeat → check-then-insert has a gap between the
  look and the write → a unique index decides at the moment of the write → a transaction hides an unfinished row, so
  the second insert waits → the error spoils a transaction → ON CONFLICT DO NOTHING skips instead of failing, and
  RETURNING says which happened (hardest last: every order of events ends with one row)
- Analogy family: the lesson's two waiters with one paper order book, who each check, find nothing and write; the
  unique index is a book where checking and writing are one movement of one pen. Breaks on speed: a pen serves one
  writer at a time, while PostgreSQL lets thousands of inserts with different codes through at once.
- Open loops: "how did it go wrong?" planted in scene 1 → answered in scene 3 and the moral in scene 10.
- Assumptions: the code `...a001`, the 0 counts, the waits, the error text and SQLSTATE 23505, payment 40, `INSERT 0 0`
  and zero rows from RETURNING are the lesson's stepper and Try it. "500 messages in one transaction" is the lesson's
  illustration.

## The one picture

Top centre: the card reader, which sends the message twice. Left and right: worker A and worker B, each a box whose
lines say what that worker did, in order. Middle top (from scene 4): the unique index on payment_uid, with its one
entry for `...a001` and whose it is. Middle bottom: the payments table's count of rows with this code, the number
that should end at 1. Gold is the message and "not committed yet"; green is committed or right; red is an error or a
duplicate. Same places from start to end.

## Scene 1 · Paid twice · 0:00–0:39 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: Picture a café on a busy morning. You tap your card, and the card reader sends a message about the payment to the
company that records it. The reader hears nothing back, so it sends the same message again. Both copies arrive a
millisecond apart. The company runs two copies of its program, called workers, so one can carry on if the other
crashes. Each worker picks up one copy, and asks the database: do we have this payment yet? Each hears no. Each stores
it. You've paid for one coffee twice. Looking before you write felt careful. So how did it go wrong?

SCREEN: The card reader at the top; a gold message chip `...a001` leaves it, then a second one. Worker A and worker B
boxes; one chip lands in each. Each box writes "do we have it? no" and "store it". The count of payments with this
code goes 0, 1, 2 (red). Caption "one coffee, paid twice".

## Scene 2 · A code to spot a repeat · 0:39–1:05 · [FAMILIAR] [NAME]

VO: First, how can a worker tell a repeat from a new payment? The card reader gives every payment a long unique code,
called payment_uid. A copy sent again carries the same code. A code like that is called an idempotency key: it lets
the receiver spot a repeat. So the obvious plan: look for the code. If it's not there, insert the payment. With one
message at a time, this passes every test.

SCREEN: The count resets to 0. Both chips glow: same code. Caption "payment_uid: an idempotency key". Each box reads
"look for ...a001" and "not there? insert". Caption "one message at a time: passes every test".

## Scene 3 · Two waiters, and a guess · 1:05–1:48 · [ANALOGY] [MAP] [JOKE:pivot] [PREDICT] [PAUSE] [BREAK]

VO: Picture two waiters and one paper order book. An order comes in twice, one copy to each waiter. Each checks the book.
Nothing. Each walks off to write it down. Two plates, one table, one very full customer. The waiters are the workers,
the book is the payments table, checking is a look, and writing is an insert. Let's slow our workers down. Worker A
looks, worker B looks, and only then does either one insert. What does each look find? Pause and guess.

(three seconds)

Zero, for both. Neither has written anything yet. So both decide to insert. The answer was true when they asked, and
out of date a moment later.

SCREEN: Captions map: "waiter = worker", "the order book = the payments table", "check = a look, write = an insert".
Each box gets "look: ?" in yellow; countdown. Then "look: 0" on both, then "insert" on both, and the count goes to 2
(red). Caption "true when they asked, out of date a moment later".

## Scene 4 · The referee · 1:48–2:08 · [NAME] [ANALOGY]

VO: Something does stop it here. The payment_uid column is marked UNIQUE: no two rows may share a value. PostgreSQL keeps
that rule with a unique index: a sorted list of every code in the column, and every insert must pass through it. In
the café, that's a book where checking and writing are one movement of one pen.

SCREEN: The count resets to 0 and the boxes clear. The unique index box appears in the middle: "unique index on
payment_uid", "no entry for ...a001". Arrows from both workers to it: "every insert passes through". Caption "one
movement of one pen".

## Scene 5 · Unfinished work · 2:08–2:25 · [SHRINK] [NAME]

VO: One more word. A transaction is a group of changes that the database applies all together, or not at all. COMMIT saves
them for good, and shows them to everyone else. ROLLBACK throws them away. Until a worker commits, no other worker can
see its new row.

SCREEN: Captions: "transaction: all together, or not at all", "COMMIT: save, and show everyone", "ROLLBACK: throw it
away", "until COMMIT, nobody else sees the row".

## Scene 6 · Replay the race · 2:25–2:58 · [SHOW]

VO: Now replay the race. Worker A inserts. Its code goes into the unique index at once, marked as belonging to A's
unfinished transaction. Worker B's insert reaches the index and finds the same code. B can't know yet whether A will
commit, so it waits. A commits. B's insert fails: duplicate key value violates unique constraint. Its error code is
23505. Had A rolled back instead, B's insert would have gone through. Either way, one row.

SCREEN: A's box "INSERT: 1 row"; the index entry becomes "...a001: A's, not committed" (gold). B's box "INSERT: waits
for A" with a pulsing clock dot. A's box "COMMIT: ok"; the entry turns green "...a001: committed"; the count is 1. B's
box "ERROR 23505" (red), and the error text as a caption.

## Scene 7 · Safe, but clumsy · 2:58–3:17 · [PAIN] [JOKE:amplify]

VO: So the data is safe. But catching that error is clumsy. An error spoils the whole transaction it happens in. A worker
that stores 500 messages in one transaction loses all 500 to a single repeat. One extra coffee, and the whole
morning's orders go back in the queue.

SCREEN: B's box: "500 messages" and a row of small squares under the error, all turning red. Caption "one error spoils the whole
transaction".

## Scene 8 · Decide inside the insert · 3:17–3:53 · [WISH] [SHOW] [NAME]

VO: Better to put the decision inside the insert itself: INSERT, ON CONFLICT on payment_uid, DO NOTHING. The insert asks
the unique index in the same step as the write. Replay it. A's insert goes in, and RETURNING hands back the new
payment's number, 40. B's insert finds A's unfinished entry, and waits, as before. A commits. This time, B's insert
sees the code is there, and skips the row. No error. RETURNING gives B zero rows, which is how B's program knows the
message was a repeat. One payment.

SCREEN: The boxes and the index reset. Caption `INSERT ... ON CONFLICT (payment_uid) DO NOTHING RETURNING payment_id`.
A: "ON CONFLICT DO NOTHING", "1 row back: 40", "COMMIT: ok"; B: "ON CONFLICT DO NOTHING", "waits for A", "0 rows: a
repeat" (green). Index gold, then green. Count 1 (green).

## Scene 9 · Where the pen breaks · 3:53–4:12 · [GUARDRAIL]

VO: Here the pen picture breaks. A pen serves one writer at a time. PostgreSQL lets thousands of inserts with different
codes through at once. Only inserts with the same code wait for each other. And some second messages carry news, and
should change the row instead of being skipped. That's the next section.

SCREEN: Many small chips with different codes stream through the index at once; only the two `...a001` inserts wait.
Caption "only the same code waits". Then "news in a second message: change the row (next section)".

## Scene 10 · The moral, and a check · 4:12–4:51 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So how did one coffee get paid twice? Each worker looked, then wrote, and the look was out of date before the write. A
check in a separate statement can be out of date before you act on it. Let the unique index decide. One quick check.
A's insert goes in, and then A crashes before it commits. B is waiting. How many payments end up stored, and who
stores them? Pause and think.

(three seconds)

One, stored by B. A's unfinished entry vanishes, and B's insert goes ahead. Every order of events ends with exactly
one row.

SCREEN: Caption "a separate check can be out of date: let the unique index decide". A's box shows "crashed" (red)
with the entry gold; countdown. Then the entry becomes "...a001: B's", B's box "1 row back", count 1 (green).

---

### Beat check

- QUESTION from a felt situation (scene 1); FAMILIAR plan and NAME of the key (scene 2).
- ANALOGY + MAP, PREDICT with PAUSE, and the BREAK of "check first" (scene 3).
- NAME the unique index and the transaction (scenes 4, 5) and SHOW the race with them (scene 6).
- PAIN of the error (scene 7), WISH and the fix SHOWN (scene 8), GUARDRAIL with the analogy's limit (scene 9).
- MORAL with the lesson's bold line, and a check answerable from the stepper's picture (scene 10).
- Light moments: one very full customer (1:30), the morning's orders back in the queue (3:30).

### Accuracy notes for the producer

- The race, the waits, the error text, SQLSTATE 23505, `INSERT 0 0` and zero rows from RETURNING are the lesson's
  stepper and its two-session Try it. Payment 40 is the stepper's number (on a fresh database, after the Try it's part
  1 used 38 and 39).
- The video's "look" stands for the stepper's `SELECT count(*) ... WHERE payment_uid = ...` and the lesson's Kotlin
  `findByUid`; the code itself is left to the lesson. The SQL shown is the ON CONFLICT statement only.
- "Its code goes into the unique index at once, marked as belonging to A's unfinished transaction" is the lesson's
  simplification of how PostgreSQL checks a unique index against in-progress inserts.
- Without the unique constraint, both inserts would commit: scene 1 and scene 3 show that count of 2 before the
  constraint is introduced.
- Left to the lesson: why skipped inserts use up payment numbers, ON CONFLICT DO UPDATE (next section), MERGE, and
  jsonb.
- Spoken forms via `SAY`: payment_uid as "payment U I D", ON CONFLICT, DO NOTHING, INSERT, COMMIT, ROLLBACK, UNIQUE and
  RETURNING in lower case, 23505 digit by digit.
