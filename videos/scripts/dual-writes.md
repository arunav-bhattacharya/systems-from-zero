# Two writes, both succeed, still wrong: the dual-write race

- Slug / scene: `dual-writes`, `videos/scenes/dual_writes.py:DualWrites`
- Lesson: `stream-01`, section 0, "From a nightly copy to two writes that quietly disagree" (the fix previews section 1)
- Audience / level: a complete newcomer. Knows nothing about databases, search indexes, threads or logs.
- Length: 5:04 (~720 words of narration, two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=148`, the `poster` stamp (the race finished: the database REFUNDED, the index CAPTURED in red, t1 to t4 along the
  bottom, every write ticked as successful)
- The learner's real question: if both writes succeed, how can the two stores disagree? And why didn't a test catch it?
- Misconception to steelman and break: "two writes that both succeed are safe, and retries cover the rest". Broken by
  the race (no write fails, the index is wrong for good) and by the crash between the two lines.
- Concept chain: a nightly copy is a day behind (batch job) → follow each change as it happens (event, stream
  processing) → the obvious way, two writes from your code → two writers pick two orders (the race) → only two of six
  orders break, so tests pass → a crash loses the second write → name: dual write → one writer, copies follow its log
  (hardest last)
- Analogy family: the café. The book by the till (the database), the board in the back (the search index), the owner
  rewriting the board after closing (a batch job), a helper copying each receipt as it prints (stream processing), two
  cashiers who each write the book and then walk to the board (the dual write), one stopped on the way (the pause),
  numbered receipts copied in order with the last number noted (the log, a follower, a bookmark).
- Open loops: "how can two writes that both succeed disagree?" planted in scene 1 → answered in scene 9; the refund
  missing from support's screen (scene 1) → shows up in scene 9.
- Assumptions: pay-981, its three statuses, the t1 to t4 order and "two of six" are the lesson's table and Try it.
  Commit numbers 768 and 769 and the bookmark come from section 1's stepper. The café book and board are the
  lesson's café owner and helper, extended with two cashiers for the race.

## The one picture

Left: two requests (capture, blue, top; refund, gold, bottom). Right: the database (white, top) and the search index
(purple, bottom), each showing `pay-981` and its status. Arrows from each request to each store; a dot runs along an
arrow for a write. Bottom row: the four writes t1 to t4 as chips. In the fix, a log box sits between the stores, the
requests write only the database, and a purple follower arrow runs from the log to the index with a bookmark beside it.
Red means wrong; green means checked.

## Scene 1 · The support desk · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: Picture the support desk at a café payments company. A customer's coffee was refunded yesterday, but support's
screen still says captured. That screen reads a copy, rebuilt every night, so it's a day behind.

So the team stops waiting for the night. Whenever a payment changes, the program updates the records, then the copy.
Two lines of code, and every test passes. A month later, one payment says refunded in the records and captured on the
screen, for good, with no error anywhere. How can two writes that both succeed disagree?

SCREEN: "customer: refunded yesterday" on the left; the search copy box with pay-981 CAPTURED; caption "rebuilt every
night at 2:00, so a day behind". The records box appears with the rule at the top. Then REFUNDED in the records,
CAPTURED in red on the screen, "no error, no retry, no line in any log", and a yellow "?".

## Scene 2 · The café: a batch and a stream · 0:30–1:05 · [FAMILIAR] [ANALOGY] [NAME]

VO: Picture the café itself. By the till, a book where every sale is written down. In the back, a board the staff
read from. One way to fill the board: after closing, the owner rewrites it from the day's receipts. Right, but only
once a day. A program that works through a whole pile in one run like that is a batch job.

The other way: a helper copies each receipt onto the board as the till prints it. Each receipt is an event, a record
of one thing that happened, and handling each event as it arrives is stream processing.

SCREEN: The boxes are relabelled "the book by the till" and "the board in the back". A down arrow: a burst of grey
dots "after closing, the whole pile at once", then single yellow dots "one receipt at a time". Captions name batch job,
event and stream processing.

## Scene 3 · The program · 1:05–1:42 · [MAP] [FAMILIAR]

VO: In the program, the book is the database, where each payment is stored. Here it's PostgreSQL, a free database
many companies run. The board is a search index, a copy built for fast searching, like the index at the back of a
book. It lives in OpenSearch, a free program for such indexes. A payment's status goes from authorized, money set
aside, to captured, money moved, and maybe refunded. And there's no helper. Each request is a cashier who writes the
book, then walks to the board and writes it there too.

SCREEN: Labels swap to "the database: PostgreSQL" and "the search index: OpenSearch", both pay-981 AUTHORIZED. The
three statuses as a legend. The two request boxes slide in.

## Scene 4 · The race · 1:42–2:35 · [SHOW] [BREAK] [JOKE:release]

VO: Two requests for pay-981 arrive a millisecond apart, each on its own thread, a line of work running at the same
time: a capture, and the shop's refund. The capture writes the database: captured. Then it stalls for a couple of
milliseconds, say while the program clears out unused memory. A cashier stopped on the way to the board. The refund
writes the database: refunded. Right, the refund came second. It writes the index too: refunded. Then the capture
wakes up and makes its second write. The index now says captured.

Every call returned success. No error, no retry, no log line. And the index stays wrong until pay-981 changes again,
which may be never. Both cashiers did exactly what they were told, and the board is wrong anyway. Nobody to blame,
which is somehow worse. The bug lives in the gap between the two writes.

SCREEN: The lesson's table as motion: t1 capture to the database, the capture greys out "paused"; t2 refund to the
database; t3 refund to the index; t4 the capture to the index, which turns red. A green tick over each of the four
chips. Caption "each line is right on its own; the trouble is between them".

NOTE: The joke comes after the trace, never inside it.

## Scene 5 · Predict: how many orders break it? · 2:35–3:15 · [PREDICT] [PAUSE] [SHOW] [JOKE:release]

VO: Was that bad luck? Each request writes the database, then the index, so the four writes can mix in six ways. How
many of the six leave the stores different? Pause and guess.

(three seconds)

Two. The one we saw, and its mirror, where the database ends captured and the index refunded. In the other four,
whoever wrote the database last also wrote the index last. Nothing in the code makes that true. The timing usually
does, and that's why every test passed. Four out of six is a fine score on a test. For payments, not so much.

SCREEN: The diagram dims. Six cards (C db, C ix, R db, R ix in each order) appear, countdown bar, then each card's end
state and a tick or cross. The two red cards are outlined; the four green ones after "the other four".

## Scene 6 · Retries, and the second door · 3:15–3:40 · [BREAK]

VO: You might think: we retry on errors. But nothing failed here, so there was nothing to retry. And a real failure
opens a second door. If the program crashes between the two lines, after a restart it doesn't know a second write
was owed. One store has the change, and the other never will.

SCREEN: The four chips pulse green ("no error, so no retry"). Then the database CAPTURED, the index AUTHORIZED; the
capture's second arrow is cut by a red "crash"; caption "after a restart, nobody knows a second write was owed".

## Scene 7 · The name, and the code · 3:40–4:00 · [NAME]

VO: This pattern is called a dual write: one change sent to two systems, one after the other, with nothing tying them
together. In Java and Kotlin, it's these two lines, and the gap sits between them. Both problems have one root: two
writers, each deciding the order.

SCREEN: The definition at the top. Java and Kotlin `setStatus` side by side; the update lines and the gap comment
highlight in turn. Then the race's end state returns with "two writers, each picking its own order".

## Scene 8 · One writer, and its price · 4:00–4:40 · [GUARDRAIL] [ANALOGY] [SHOW]

VO: Back to the café. Let only the till decide the order. It numbers each receipt, and the helper copies them in
number order, noting the last number so it can carry on after a break.

In the program, requests write only the database, and the database settles the race. The capture holds the row, so
the refund waits its turn. Its log records the capture first, then the refund. A follower applies that log to the
index in order, keeping a bookmark of how far it got. Both stores end at refunded. The price is lag: the index hears
each change a few milliseconds late. But it can't get the order wrong, because it no longer picks one.

SCREEN: A log box grows between the stores ("numbered receipts, in order", then "the database's log, in commit
order"), a helper/follower arrow to the index. Both requests write the database; the refund "waits its turn"; log
entries 768 CAPTURED and 769 REFUNDED; the follower applies each, "bookmark: 768" then "769". Caption "the price:
lag".

## Scene 9 · The moral, and a check · 4:40–5:04 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, two writers pick two orders. Give the data one writer, and let every copy follow its log. Now the customer's
refund shows on support's screen.

One quick check. With the follower in place, the program crashes right after the refund's database write. What does
the index end up saying? Pause and think.

(three seconds)

Refunded. The change is already in the log, and the follower picks it up from its bookmark. Nobody had to remember a
second write.

SCREEN: "one writer; every copy follows its log". For the check: index CAPTURED, bookmark 768, the refund writes the
database and 769 lands in the log, then a red "crash". Countdown. The follower carries 769 to the index: REFUNDED,
bookmark 769, a green tick.

---

### Beat check

- Opens with QUESTION (scene 1), from a felt symptom (the missing refund).
- FAMILIAR + ANALOGY (scene 2, the café) before any product name; MAP said out loud (scene 3).
- SHOW and BREAK: the race (scene 4), the retry idea and the crash (scene 6).
- PREDICT with PAUSE: six orders (scene 5) and the check (scene 9).
- NAME after the SHOW: batch job, event, stream processing (scene 2), dual write (scene 7, after the race).
- GUARDRAIL (scenes 6 and 8: retries can't help; the fix and its price, lag) and MORAL (scene 9) come last.
- Light moments: "nobody to blame, which is somehow worse" (scene 4), "four out of six is a fine score on a test"
  (scene 5).

### Accuracy notes for the producer

- The race is the lesson's t1 to t4 table, and "two of the six orders" is its Try it (the mirror order ends
  db CAPTURED, index REFUNDED).
- "Clears out unused memory" is the lesson's example of the pause (a garbage-collection pause).
- Left out for length: rebuilding every five minutes (the section's aside) and two-phase commit, which section 1 rules
  out because the index has no prepare step and every write would need both systems up.
- The log is PostgreSQL's write-ahead log; the numbers 768 and 769 are transaction numbers from section 1's stepper.
  The video calls it "the database's log" and leaves WAL, LSNs and replication slots to sections 2 to 4.
- The capture "holds the row": a transaction takes the row's lock, and the refund's transaction waits for it.
