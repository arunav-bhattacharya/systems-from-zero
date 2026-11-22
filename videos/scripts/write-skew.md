# Both checked, both paid: how Ivy goes below zero

- Slug / scene: `write-skew`, `videos/scenes/write_skew.py:WriteSkew`
- Lesson: `txn-01`, section 3, "Ivy goes below zero: write skew, a rule over two rows"
- Audience / level: a complete newcomer. Has met transactions, snapshots and isolation levels in sections 0 to 2;
  doesn't know write skew or why a check-then-write isn't safe.
- Length: about 5 minutes (~800 words of narration, two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: each payment checked Ivy's total before it went through, inside a transaction, so how
  can she end below zero?
- Misconception to steelman and break: "check, then write, inside a transaction, is safe" (broken at Repeatable
  Read: both commit, total -6,000); "a level called SERIALIZABLE always stops it" (Oracle's doesn't).
- Concept chain: a rule over two rows → two transactions read the same snapshot → they write different rows, so no
  lock and no conflict → a state no order could make: write skew → fixes: lock first (`FOR UPDATE`) or Serializable
  with a retry (hardest last)
- Analogy family: two flatmates and a fridge with two cakes; the house rule "leave at least one cake for guests".
  Each opens the fridge at the same moment, each takes a different cake. A lock on the fridge door is FOR UPDATE.
- Open loops: "each one checked; how?" planted in scene 1 → paid off in scene 5 (write skew).
- Assumptions: all numbers are the lesson's (accounts 109 and 209 of customer 9 at 5,000 each, two withdrawals of
  8,000, both see 10,000, each row -3,000, total -6,000; the second sees 2,000 when run after; the error text and
  SQLSTATE 40001; FOR UPDATE then sees -3,000 and 5,000 and refuses). The flatmates are invented for the video.

## The one picture

Centre: the committed data (white box): rows 109 and 209 and the total. Left: Tx A (blue), right: Tx B (gold), each
a box listing what it saw, its draft and its commit. First drawn as the fridge with two cakes and two flatmates.
Locks are small chips beside a row. The bottom band holds the SQL or the error; captions at the bottom.

## Scene 1 · The puzzle · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: Ivy has two accounts with a payments company, with 50.00 in each. The company lets one account go below zero, as
long as the two together stay at zero or above. One evening, in the same second, she pays 80.00 for groceries from one
account, and her phone company takes 80.00 from the other. Each payment checks her total, sees 100.00, and goes
through. Ivy ends the evening at minus 60.00. Each one checked first. So how did that happen? Hold that question.

## Scene 2 · Two cakes · 0:30–1:15 · [FAMILIAR] [ANALOGY] [MAP] [JOKE:pivot]

VO: Picture two flatmates and a fridge with two cakes. The house rule: always leave at least one cake for guests. At
the same moment, both open the fridge. Each sees two cakes, so each thinks, fine, I can take one. One takes the
chocolate cake, the other takes the lemon one. They never reached for the same cake, so nobody argued. And the guests
get an empty fridge. Let's map it. The cakes are Ivy's two accounts. The rule over both cakes is the rule over her
total. And each flatmate is one payment, checking everything but changing only its own part.

## Scene 3 · Inside the database · 1:15–2:15 · [SHRINK] [SHOW]

VO: Now inside the database. Ivy is customer 9. Her accounts, 109 and 209, hold 5,000 each, counted in hundredths. Two
withdrawals of 8,000 arrive together, one from each account. Each runs in its own transaction at Repeatable Read, so
each reads from a snapshot, a picture of the committed data taken at its first statement. Each adds up her balances
and sees 10,000: allowed. Transaction A takes 8,000 from 109. Its draft says minus 3,000, and it holds the lock on that
row. Transaction B takes 8,000 from 209. A's lock is on 109, not 209, so B doesn't wait.

## Scene 4 · Predict the commits · 2:15–2:45 · [PREDICT] [PAUSE] [SHOW] [BREAK]

VO: Now both commit. Does either one fail? Pause and guess.

Neither. Both commits succeed. 109 is minus 3,000, 209 is minus 3,000, and Ivy's total is minus 6,000. No error
anywhere. Well, the fridge is empty.

## Scene 5 · Name it · 2:45–3:30 · [NAME] [LOOP-PAYOFF]

VO: This is called write skew. Each transaction read rows that the other one then changed, and each write was right for
the data it saw. Run one after the other, the second would have seen 2,000 and refused. Run together, they made a
state that no order of the two could have made. And Repeatable Read only complains when two transactions change the
same row. These two didn't. Any rule that reads rows it doesn't write has this hole: a daily limit checked at several
card readers, two bookings of one meeting room, or two refunds of one payment.

## Scene 6 · Names that mislead · 3:30–3:50 · [GUARDRAIL] [JOKE:is-the-explanation]

VO: The label won't save you either. Read Committed lets it through, and so does Oracle's level called SERIALIZABLE,
which is really snapshot isolation. A sign on the fridge that says serializable doesn't keep a cake in it.

## Scene 7 · Fix one: lock the fridge · 3:50–4:25 · [SHOW]

VO: The first fix: lock the fridge door before you look. Each transaction first locks all of Ivy's accounts with SELECT
FOR UPDATE, then checks. B's lock request waits until A commits. Then it reads the newest values, minus 3,000 and
5,000, and refuses. Withdrawals for one customer now run one at a time.

## Scene 8 · Fix two: Serializable, and a retry · 4:25–5:10 · [SHOW] [GUARDRAIL]

VO: The second fix: PostgreSQL's Serializable. It runs from snapshots as before, but it also notes what each
transaction read. A read 209, which B wrote, and B read 109, which A wrote. No order of the two explains that, so B's
commit fails with SQLSTATE 40001. The program runs B again from the start. Its new snapshot includes A's commit: the
total is 2,000, and the check refuses. The catch: your code has to retry, and the retry has to be safe to repeat.

## Scene 9 · The moral, and a check · 5:10–5:45 · [MORAL] [PREDICT] [PAUSE]

VO: So the moral of the story: checking first isn't enough when the check reads rows that someone else may change. Lock
what you read, or let Serializable catch it. One quick check. Two refunds of one payment each check how much is left,
then each writes its own refund row, at Repeatable Read. Can they refund too much? Pause and think.

Yes. Each reads the same amount left and writes a different row. That's write skew again: two cakes, two flatmates,
one empty fridge.

---

### Beat check

- QUESTION (1) → FAMILIAR + ANALOGY + MAP (2) → SHRINK + SHOW (3) → PREDICT + PAUSE + BREAK (4) → NAME + LOOP-PAYOFF
  (5) → GUARDRAIL (6) → fixes SHOW (7, 8) with the retry GUARDRAIL → MORAL + check (9).
- Light moments: the guests' empty fridge (1:10), "the fridge is empty" (2:40), the sign on the fridge (3:45).

### Accuracy notes for the producer

- Repeatable Read here is PostgreSQL's (snapshot at the first statement). Read Committed gives the same result.
- Oracle's SERIALIZABLE as snapshot isolation is from Hermitage, as the lesson cites.
- The full error is `could not serialize access due to read/write dependencies among transactions`; the screen shows
  it, the narration says only the SQLSTATE.
- Retrying safely is the next section's topic; the video only names it.
- The refunds check is the lesson's example ("two refunds that each check how much of a payment is left"); writing a
  separate refund row is the shape that makes it a rule over rows it doesn't write. The check's on-screen amounts
  (payment 80.00, 80.00 left) are made up for the picture.
