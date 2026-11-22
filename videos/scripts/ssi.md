# Fifty dollars overdrawn, and nobody broke a lock: serializable snapshot isolation

- Slug / scene: `ssi`, `videos/scenes/ssi.py:SSI`
- Lesson: `txn-05`, section 3, "Catching write skew without read locks: serializable snapshot isolation"
- Audience / level: a complete newcomer. Has met row locks and snapshots in earlier videos; the video restates both in
  a sentence.
- Length: 5:14 (~810 words of narration at Kokoro's ~180 words a minute, plus two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=200` (both read-write arrows between A and B, A committed, B's COMMIT failing with 40001)
- The learner's real question: two withdrawals wrote different rows and no lock clashed, yet the account went 50.00
  overdrawn. How can a database catch that without making readers wait?
- Misconception to steelman and break: "row locks keep transactions safe". Broken by write skew: different rows, no
  clash. And "the fix is to lock reads too": correct, but the waiting (and deadlocks) come back.
- Concept chain: write skew slips past row locks → serializable means "same as one at a time" → version 1: reads lock
  (MySQL), which waits and deadlocks → version 2: SSI, notes of who read what, read-write arrows, a circle → the
  pivot shortcut → false alarms, so every transaction needs a retry loop (hardest last)
- Analogy family: an office archive with a clerk. Anyone reads any folder without waiting and signs its slip on the
  way out; when someone changes a folder, the clerk draws an arrow "reader before writer"; arrows in a circle send
  someone back to start over.
- Open loops: "how did the database let this through?" planted in scene 1 → answered in scenes 2 and 7; the clerk's
  arrows planted in scene 4 → drawn for real in scene 5.
- Assumptions: all numbers are the lesson's (acct-17, two cards of 75.00, withdrawals of 100.00, -25.00 each, -50.00
  total; 40001; version 9.1; MySQL's SERIALIZABLE turning reads into FOR SHARE; 2 million rows for the month-end
  report). Narration says "the first/second withdrawal"; the screen labels them A and B as the lesson's stepper does.

## The one picture

Left: acct-17's two cards (white boxes, balances in mono, a small note line inside each for read locks, slips or
SIREAD notes) and the total under them. A dashed divider. Right: the "who must come first" graph: A (blue) and B
(purple) as boxes, read-write arrows curving above (B to A) and below (A to B), and two status chips under them.
Gold is the clerk and his arrows in the analogy; red is overdrawn or aborted; green is the serial outcome.

## Scene 1 · The question · 0:00–0:35 · [QUESTION] [LOOP-PLANT]

VO: Picture one customer's account, acct-17, with two cards. Each card holds 75.00. The rule is simple: the account's
total must never go below zero. Two withdrawals of 100.00 arrive at the same moment, one from each card. Each checks
the total first: 150.00. Plenty. So each takes 100. Both commit. Card 1 is at -25.00, card 2 is at -25.00, and the
account is 50.00 overdrawn. Nobody broke a lock. How did the database let this through?

SCREEN: Title card. Two cards of 75.00, "total: 150.00", the rule. A and B appear; "A reads the total: 150.00", "B
reads the total: 150.00"; both cards drop to -25.00; both COMMIT ok; a red "total: -50.00".

## Scene 2 · Different rows · 0:35–1:20 · [FAMILIAR] [SHOW] [BREAK] [JOKE:release] [NAME]

VO: Locks put the writers of one row in line. But look at what each withdrawal wrote. The first wrote card 1. The
second wrote card 2. Different rows, so no lock ever clashed. Run them one after the other, and the second would
have seen 50.00, and refused. Together, each made its decision from a total the other one was about to change. Each
was careful. Just not with each other. This is called write skew: two transactions read the same rows, then write
different ones, and a rule breaks. Row locks can't see it. What we want has a name: serializable. The result must
equal running the transactions one at a time, in some order.

SCREEN: Each card pulses in its writer's colour; "different rows: no row lock ever clashed". The serial run: A first,
total 50.00, "then B sees 50.00: refuses" (green). Then back to the overlap: "A decided from 150.00", "B decided
from 150.00", -50.00. Captions naming write skew and serializable.

## Scene 3 · Version 1: reads lock too · 1:20–2:00 · [PAIN] [GUARDRAIL] [WISH]

VO: The first way to get it: make reads lock too. Every row a transaction reads gets a lock, held until it commits.
Now each withdrawal needs to write a card the other one holds. They wait for each other, the database stops one, and
it runs again. That's correct, and it's how MySQL's serializable works. But it brings the waiting back. A month-end
report would lock 2 million rows, and every transfer would queue behind it. So the wish: readers never wait, and
still, somebody notices.

SCREEN: Grey padlocks on both cards, "read-locked by A and B"; "A waits for B's lock on card 1", "B stopped: runs
again later"; captions for MySQL's SERIALIZABLE and the cost; the wish in green.

## Scene 4 · The archive clerk · 2:00–2:50 · [ANALOGY] [MAP] [JOKE:pivot]

VO: Picture an office archive with a clerk. Anyone can read any folder, with no waiting. But on the way out, you sign
the folder's slip: I read this. When someone changes a folder, the clerk checks its slip. Somebody else read the old
one, so in any one-at-a-time story, that reader came first. The clerk draws an arrow: reader before writer. If the
arrows ever go round in a circle, no one-at-a-time story fits. The clerk sends someone back to start over. Map it.
The signature on the slip is a note PostgreSQL calls an SIREAD lock. The arrow is a read-write dependency. Being sent
back is an error, and starting over is your program's retry.

SCREEN: A gold clerk figure and "the clerk's whiteboard" over the graph; the cards' note lines become "slip: read by
A, B"; a gold arrow B to A, then A to B (a circle); B pulses red. The map in three lines under the graph.

## Scene 5 · Run the cards · 2:50–4:00 · [SHOW] [PREDICT] [PAUSE] [NAME] [LOOP-PAYOFF]

VO: Let's run the cards, under PostgreSQL's serializable. Both withdrawals read both cards. Each read leaves a note.
The notes block nothing. The first withdrawal takes 100 from card 1. The second had read card 1, and won't see this
change. So the second must come before the first. An arrow, from second to first. Now the second takes 100 from card
2, which the first had read. An arrow, from first to second. No row lock clashed, and still, the arrows make a
circle. The first commits. What happens when the second tries to commit? Pause and guess.

(three seconds)

It fails, with error 40001: could not serialize access. The second is a pivot: one arrow in, one arrow out, and the
transaction at the far end has already committed. The second withdrawal's change to card 2 is thrown away with it, so
nobody will ever see it. The program's retry runs it again from the start. Its new snapshot sees card 1 at -25.00,
the total is 50.00, and the withdrawal is refused. The same end as running the first, then the second.

SCREEN: The lesson's stepper, frame by frame: "SIREAD: A, B" in both cards; card 1 to -25.00 and the purple arrow
"B read card 1, A wrote it"; card 2 to -25.00 and the blue arrow "A read card 2, B wrote it"; "A before B, and B
before A: no order fits"; A COMMIT ok; countdown; "B: COMMIT, ERROR 40001"; "pivot: one read-write arrow in, one
out"; card 2 back to 75.00, total 50.00; "B again: reads 50.00, refuses"; "the same end as A, then B".

## Scene 6 · The name, the shortcut, the cost · 4:00–4:45 · [NAME] [GUARDRAIL]

VO: This is serializable snapshot isolation, SSI, PostgreSQL's serializable since version 9.1. Readers read their
snapshot and never wait. The notes only feed the check. Searching every circle after each write would be slow. The
theory behind it shows that every circle has two arrows in a row. So PostgreSQL only watches for a transaction with
one arrow in and one arrow out. The shortcut has a cost: false alarms. The pattern can appear without a real circle,
and notes on a whole table, instead of a row, make it more likely. So under serializable, every transaction needs a
retry loop: code that runs it again from the start after 40001. In exchange, you don't have to study every pair of
transactions yourself.

SCREEN: "SSI: serializable snapshot isolation"; the two arrows redrawn and pulsed; "the shortcut: watch for a pivot,
not for whole circles"; "false alarms" with "note on the whole table" in both cards; the rule "every SERIALIZABLE
transaction gets a retry loop for 40001".

## Scene 7 · The moral, and a check · 4:45–5:13 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So how did the account go 50.00 overdrawn? Each withdrawal decided from a total the other was changing, and they
wrote different rows, so no lock saw it. Serializable snapshot isolation keeps notes of who read what, and sends one
back. Nobody waits to read. One quick check. Run the same two withdrawals at Repeatable Read instead. What are the two
cards at the end? Pause and think.

(three seconds)

-25.00 each. Both commit, and the account is 50.00 overdrawn. Repeatable Read gives each a snapshot, but keeps no
notes of who read what.

SCREEN: The overdrawn state again, then the SSI outcome (50.00, "B: 40001, retried, refused") and the moral. "REPEATABLE
READ" over the graph, cards back at 75.00; countdown; both cards a red -25.00, total -50.00, both COMMIT ok. The moral
stays on the last frame.

---

### Beat check

- Opens with QUESTION (scene 1), from a felt result (50.00 overdrawn, nobody broke a lock).
- FAMILIAR (scene 2): row locks put writers of one row in line; the serial run as the baseline.
- BREAK: row locks can't see write skew (scene 2); reads that lock bring back waiting (scene 3).
- ANALOGY + MAP (scene 4) before the mechanism; every part mapped out loud.
- PREDICT with PAUSE (scene 5 and the check in scene 7); SHOW right after each.
- NAME after the SHOW: write skew, serializable (scene 2), SIREAD lock, read-write dependency (scene 4, after the
  clerk), pivot (scene 5), SSI (scene 6).
- GUARDRAIL (scenes 3 and 6) and MORAL (scene 7) last. Light moments: "careful, just not with each other" (~1:05),
  the clerk who doesn't stop anyone (~2:05).

### Accuracy notes for the producer

- The stepper's order is followed: both read, A writes card 1 (edge B to A), B writes card 2 (edge A to B), A commits,
  B's COMMIT fails with 40001, "Canceled on identification as a pivot, during commit attempt"; the retry sees 50.00
  and refuses.
- "Every circle has two arrows in a row" is the lesson's summary of Fekete and colleagues' result (T1 to T2 to T3, T3
  the first to commit). PostgreSQL then aborts a transaction of the dangerous pattern; the video says it watches for
  a pivot.
- Version 1 is the lesson's strict 2PL: S locks on reads held to commit; A's and B's S locks block each other's X
  locks, so they deadlock and one runs again. "MySQL's SERIALIZABLE" turns plain SELECTs into `SELECT ... FOR
  SHARE`. The lesson's extra point about gap locks for a new card is left out.
- "Notes on a whole table": the lesson's Try it shows a relation-level SIReadLock on `cards` because the sum read the
  table with a sequential scan.
- The Repeatable Read answer is the Try it's: both commit and both cards end at -2,500 cents (-25.00).
- Left to the lesson: the stepper's later frames on why A may commit, SIREAD lock granularity details, and section
  4's measured costs.
- Amounts are spoken as people say them ("seventy-five", "minus twenty-five"); acct-17 is spoken "account
  seventeen"; 40001 is spoken digit by digit.
