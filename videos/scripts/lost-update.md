# Where did ten dollars go? Two charges, one row, and a lost update

- Slug / scene: `lost-update`, `videos/scenes/lost_update.py:LostUpdate`
- Lesson: `txn-02`, section 0, "Read, compute, write: two charges and one lost update" (with the first fix from
  section 1, and the other two named as the guardrail)
- Audience / level: a complete newcomer. Can read a line of code; doesn't know what a row, a transaction or a lock is.
- Length: 5:17 (~850 words of narration at Kokoro's ~180 words a minute, plus three pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=117` (the broken race finished: both lanes full, the row at a red 4,000)
- The learner's real question: both charges ran and both said success, so where did ten dollars go? Doesn't the
  database stop two writes to one row from clashing?
- Misconception to steelman and break: "the database makes the second write wait, so it's safe". It does wait (the
  row lock), and the fee still writes the 4,000 it worked out before waiting.
- Concept chain: read, subtract in the program, write → two of them overlap → the row lock orders the writes but
  can't redo the sum (lost update, read-modify-write) → let the database do the arithmetic (3,000) → when it can't:
  lock on read, or compare and set (hardest last: choosing between them)
- Analogy family: two flatmates, one grocery card, its balance on the fridge whiteboard, and one marker. The fix is
  "bring an instruction, not a number: take 10 off".
- Open loops: "where did ten dollars go?" planted in scene 1 → answered in scene 8; "you'd be half right" planted in
  scene 3 → paid off at the end of scene 3 ("the lock did its job").
- Assumptions: all numbers are the lesson's (50.00 = 5,000 cents, two charges of 1,000, 4,000 instead of 3,000;
  account 109; the Kotlin read and update). The like counter in the check (41 likes) is made up for the question;
  the lesson names "a counter of likes" as one place the pattern hides.

## The one picture

Top centre: row 109 of `accounts` (white box, `balance_minor` and its value). Left lane: the card payment (blue);
right lane: the monthly fee (purple); a grey time arrow between them, and the steps as chips in time slots. The row
lock is a padlock at the row's right edge, in the colour of whoever holds it. In the story the row becomes the fridge
whiteboard, the padlock becomes the marker, the lane titles become the flatmates, and their sums are thought bubbles;
the mapping morphs each one back into its database part. Yellow is waiting, red is lost, green is right, gold is the
fix. Captions at the bottom.

## Scene 1 · The question · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: Picture the company behind a coffee-shop payments app, checking its numbers at the month's end. Ivy's spending
account started the month at 50.00. On the first morning, in one second, two charges came in: 10.00 for a coffee, and
a 10.00 monthly fee. It should show 30.00. It shows 40.00. Both charges are in the list of payments. Both programs
said success. No error anywhere. So where did ten dollars go?

SCREEN: Title card. Ivy's account with 50.00; two gold charge chips from the left; "should show 30.00" (green) and
"shows 40.00" (red), the balance turns red 40.00. "payments list: coffee, monthly fee", "both programs: success.
errors: none", and the yellow question.

## Scene 2 · The code we've all written · 0:30–1:05 · [FAMILIAR] [SHRINK]

VO: Let's put it in the database. The company keeps its data in PostgreSQL, a free database program, in tables made
of rows. Ivy's account is row 109, and it keeps the balance in cents. So 50.00 is 5,000. Each charge runs in a
transaction, a group of statements the database applies together or not at all. And each does three things we've all
written: read the balance, subtract in its own Kotlin code, and write the result back. Run them one after the other,
and the balance goes 5,000, 4,000, 3,000. So far so good.

SCREEN: The account shrinks into the row box at the top (row 109, `balance_minor 5,000`). The lesson's two lines of
Kotlin, and three chips: read, subtract in the program, write. Then the row counts 4,000 and a green 3,000.

## Scene 3 · Taking turns, and the guess · 1:05–2:00 · [PAIN] [PREDICT] [PAUSE] [SHOW] [BREAK] [JOKE:release]

VO: Now, you might be thinking: the database won't let two writes on one row clash. And you'd be half right. When a
transaction updates a row, PostgreSQL puts a row lock on it, a mark that makes any other writer of that row wait
until this transaction commits. So let the two overlap. The payment reads 5,000 and works out 4,000. The fee reads
5,000 too, and works out 4,000. The payment writes 4,000 and takes the lock. The fee tries to write, and waits. Good,
it's taking turns. The payment commits, which makes its change permanent, and lets go of the lock. What does the fee
write now? Pause and guess.

(three seconds)

4,000. The number it worked out before it waited. Two charges ran, and the balance went down by one. Well... the lock
did its job. It just wasn't the job we needed.

SCREEN: Lane titles and the time arrow. The padlock shows once, grey, with the caption defining a row lock. Then the
steps fill the slots: payment "read 5,000, work out 4,000"; fee the same; payment "UPDATE balance = 4,000" (row 4,000,
blue padlock); fee's UPDATE in yellow, "the fee waits for the payment's lock"; payment COMMIT (padlock off);
countdown; padlock turns purple, fee "writes 4,000, COMMIT", row a red 4,000; the fee's read pulses red; "two
charges, and the balance fell by 1,000".

NOTE: The steelman is said first ("half right"): the wait is real. The light line comes after the reveal.

## Scene 4 · The fridge whiteboard · 2:00–2:50 · [ANALOGY] [MAP] [JOKE:pivot]

VO: Let's leave computers for a minute. Two flatmates share a grocery card, and its balance is on the whiteboard on
the fridge: 50. In the morning, both glance at it. Each spends 10, works out 40 in their head, and comes home to write
it down. There's only one marker. So the second flatmate waits politely while the first writes 40. Then she takes the
marker, and writes... 40. Waiting her turn didn't help, because she brought an answer from the morning.

Map it back. The whiteboard is row 109. The marker is the row lock. The glance is the read, and the sum in her head is
the Kotlin code. The lock put the two writes in order. It couldn't fix a number worked out from an old read.

SCREEN: The lanes clear. The row becomes a whiteboard ("grocery card: 50"), the lane titles become "flatmate 1" and
"flatmate 2" with two figures, thought bubbles "50 - 10 = 40". The marker appears, goes to flatmate 1 ("flatmate 2
waits for the marker"), the board says 40, the marker goes to flatmate 2, and the board says 40 again, in red. On
"map it back" each part morphs into its database twin: whiteboard → row 109, marker → padlock, figures → "read
5,000" chips, bubbles → "Kotlin: 5,000 - 1,000" chips.

NOTE: The polite wait is the light moment, and it is the lesson: waiting your turn with an old answer.

## Scene 5 · The name · 2:50–3:20 · [NAME]

VO: This has a name: a lost update. Two transactions read the same value, each writes a result worked out from it,
and the second write erases the first. Nothing failed, so no log line tells you. The shape behind it is called a
read-modify-write cycle: read a value, change it in the program, write it back. It hides in a counter of likes, in a
program that loads a whole document and saves it back, and in a worker that reads which job is next and then marks it
taken.

SCREEN: Caption "lost update: the second write erases the first"; both lanes "writes 4,000" and "COMMIT: ok". Then
"read-modify-write" and three gold chips for where it hides.

## Scene 6 · Take 10 off · 3:20–4:05 · [ANALOGY] [SHOW] [PREDICT] [PAUSE] [LOOP-PAYOFF]

VO: So how do the flatmates fix it? Don't bring a number home. Bring an instruction: take 10 off. Whoever holds the
marker reads the board right then, and subtracts. In SQL, that's one statement: set the balance to the balance minus
1,000. The read and the write happen in one step, inside the database. Same race. The payment's update takes the
lock. The fee's update waits. The payment commits. Now what does the balance end at? Pause and guess.

(three seconds)

3,000. When the lock went, PostgreSQL read row 109 again, as the payment left it, and subtracted from 4,000. Both
charges are there, and nobody had to try again.

SCREEN: "bring an instruction, not a number: 'take 10 off'"; then the lesson's statement `UPDATE accounts SET
balance_minor = balance_minor - 1000 WHERE account_id = 109`. The race again: payment "SET balance = balance - 1,000"
(row 4,000, blue padlock), the fee's in yellow, payment COMMIT; countdown; fee "rereads 4,000, writes 3,000", row a
green 3,000, "both charges: 5,000 - 1,000 - 1,000 = 3,000".

## Scene 7 · Two more fixes, and when · 4:05–4:40 · [GUARDRAIL]

VO: Sometimes the new value needs logic SQL can't write, like a fraud score from another program. Then there are two
more fixes. Lock when you read: SELECT FOR UPDATE takes the marker before you look. The fee's read waits for the
payment, then sees 4,000. Or compare and set: write 4,000 only if the balance is still 5,000. If someone got there
first, the update changes no rows, and the program reads again and tries again. A rule of thumb: lock rows that many
transactions want at once. Compare and set on rows that are rarely shared.

SCREEN: Two panels: blue "lock when you read" (`SELECT balance_minor ... FOR UPDATE`, "take the marker before you
look", "the fee's read waits, then sees 4,000"), with the padlock on the row; purple "compare and set" (`SET ... =
4000 WHERE balance_minor = 5000`, "write only if it still says 5,000", "0 rows changed: read again, try again").
Caption "busy row: lock it. rarely shared row: compare and set."

## Scene 8 · The moral, and a check · 4:40–5:15 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, where did the ten dollars go? The fee wrote a number it worked out before it waited. The lock puts writes in
line. It doesn't redo your sums. Let the database do the arithmetic, or make it check yours.

One quick check. A post has 41 likes. Two people tap like at once, and each program reads 41, adds one in code, and
writes 42. What does the post show? Pause and think.

(three seconds)

42. One like is lost. Set likes to likes plus one, and it shows 43.

SCREEN: "where did 10.00 go?"; the row a red 4,000 with the padlock, "a lock puts writes in line. It doesn't redo your
sums."; then a green 3,000. A post box "41 likes" and two chips "read 41, write 42"; countdown; a red 42, the chips
become "SET likes = likes + 1", a green 43. The rule stays on the last frame.

---

### Beat check

- Opens with QUESTION (scene 1) from a felt symptom (ten dollars short, no error).
- FAMILIAR (scene 2): the read, subtract, write we've all written, run one at a time.
- PREDICT with PAUSE three times (scenes 3, 6, 8), SHOW right after each.
- BREAK: the "it waits, so it's safe" model, steelmanned and run to its end (scene 3).
- ANALOGY + MAP (scene 4), every part mapped out loud and morphed; the analogy carries the fix (scene 6).
- NAME after the SHOW: row lock (scene 3, as a plain mark), lost update and read-modify-write (scene 5).
- GUARDRAIL (scene 7) and MORAL (scene 8) last. Light moments: "the job we needed" (~1:58), the polite flatmate
  (~2:30), and the check.

### Accuracy notes for the producer

- The lesson's simulator and Try it: both read 5,000, the payment's UPDATE takes the row lock, the fee's UPDATE waits
  until the payment commits and then writes its 4,000 (`UPDATE 1`), ending at 4,000. The video shows the same order.
- "PostgreSQL read row 109 again" is the lesson's description of Read Committed's recheck for `SET x = x - n`: after
  the lock goes, it rereads the newly committed version, checks the WHERE again and subtracts.
- The video says "the fee's read waits for the payment, then sees 4,000" for SELECT FOR UPDATE, as section 1 says.
- The compare-and-set shown is section 1's idea with the lesson's numbers (the drill writes `SET balance_minor = 4000
  WHERE account_id = 109 AND balance_minor = 5000`). Section 1 also warns that not every database rechecks an
  UPDATE's WHERE the way PostgreSQL does; the video leaves that to the lesson.
- Left to the lesson: the fourth fix (Repeatable Read's first-updater-wins and 40001, and MySQL letting the lost
  update through), FOR NO KEY UPDATE, where PostgreSQL keeps row locks, and the job-queue and deadlock sections.
- Amounts are spoken as people say them ("fifty") through a `SAY` rule; captions keep "50.00". PostgreSQL is spoken
  "post-gress" through the known rule.
