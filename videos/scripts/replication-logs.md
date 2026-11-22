# Send the instruction, or send the result? What a replication log should say

- Slug / scene: `replication-logs`, `videos/scenes/replication_logs.py:ReplicationLogs`
- Lesson: `repl-02`, section 0, "Sending the statement: short, readable, and different on every machine"
- Audience / level: a complete newcomer who has met the leader's numbered log (lesson One leader, many followers).
  Doesn't know SQL, `now()`, `random()` or what a statement log is.
- Length: about 4:20 (~700 words of narration)
- Poster: `POSTER=136` (statement copy: other codes, times 350 ms later, fee 60, "equals the leader: false")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: the leader's log tells followers what changed. Why not just write down the command
  the leader ran, and let every follower run it too?
- Misconception to steelman and break: "the same statement run on every copy gives the same table". Broken by the
  lesson's demo (other codes, times 350 ms later, a fee paid twice). Second, "write the leader's values in and it's
  fixed", broken by the fee: still 60.
- Concept chain: a log entry can be the instruction → the follower runs it again, elsewhere and later → anything that
  depends on where or when comes out different → pinning values fixes some, not "add to it" twice → log what the
  statement did, the rows (hardest last: same result every time, the rule durable execution met)
- Analogy family: the lesson's café with two branches and a price list, changed by a text message ("raise every price
  by 10 cents, and write today's date at the top"), read the next morning and delivered twice.
- Open loops: "what should one entry say?" planted in scene 2 → answered in scenes 7 and 8; the café's double price
  rise planted in scene 1 → paid off by the fee of 60 in scene 4.
- Assumptions: all rows, codes, times and fees are the lesson's Try output (`LogsDemo.kt`). The statements on screen
  are shortened (`INSERT INTO payments (...) VALUES ...`, the column list left out). The tables show only rows 1 and
  3 (the ones left at the end), and leave out the amount column. The café's prices (2.50, 2.00) are made up for the
  picture.

## The one picture

Top: a wide log panel (the text message, then the statement log, then the row log). Bottom left: the leader's table
(blue). Bottom right: the follower's table (teal), follower S for statements, later follower R for rows. Yellow
marks the entry being run; red marks a cell that differs from the leader; green, one that matches.

## Scene 1 · The café's text · 0:00–0:45 · [QUESTION] [ANALOGY] [JOKE:release]

VO: Picture a café with two branches that keep the same price list. The owner changes prices at the first branch,
and texts the manager of the second: raise every price by 10 cents, and write today's date at the top.

He reads the text the next morning, so his list carries a different date. Then her phone says: not delivered, and
sends the text again. And the second branch raises its prices twice.

Sending the instruction felt natural. It's short, and anyone can read it. But the second branch did the work again,
at another time, and got another answer. Coffee at branch two is now the priciest in town.

SCREEN: Title card. Left card "branch 1" (coffee 2.50, tea 2.00, dated: today), right card "branch 2". The text
message appears in the top panel. Branch 1 becomes 2.60, 2.10, today. Branch 2: 2.60, 2.10, "dated: next day" (red);
a second copy of the text, branch 2 becomes 2.70, 2.20 (red).

## Scene 2 · A statement in the log · 0:45–1:30 · [FAMILIAR] [NAME] [LOOP-PLANT]

VO: Databases face the same choice. In One leader, many followers, the leader wrote every change into a numbered
log, and the followers applied it in order. But what does one entry actually say?

Changes arrive as statements. A statement is one command in SQL, the language most databases take commands in.
This one marks every payment in batch 42 as paid out to its shop.

The simplest log writes the statement down. 59 bytes, even if it changes 80,000 rows. A person can read it. MySQL,
a popular free database, copied changes only this way until version 5.1. It's the text message: each follower runs it
again.

SCREEN: The cards become "leader" and "follower" tables; the panel becomes "statement log". The UPDATE ... batch_id = 42
line; captions "59 bytes", "can change 80,000 rows", "MySQL: only this way until 5.1".

## Scene 3 · The demo, and a guess · 1:30–2:15 · [SHRINK] [PREDICT] [PAUSE]

VO: Let's test it with the lesson's demo. The leader runs five statements. Three add a payment, each with a
reference code made from a random number, and the time from now. One adds a fee of 30 to every payment of shop m1.
And one deletes shop m2's payment.

Follower S runs each statement 350 milliseconds after the leader. Then, as can happen after a reconnect, the end of
the log arrives a second time. Will the follower's table match the leader's? Pause and guess.

SCREEN: The five statements fill the log. The leader's table fills: rows 1 and 3, codes 23c52a1a and e0934861,
times 1000010 and 1000030, fees 0 then 30. Countdown.

## Scene 4 · Not one row matches · 2:15–3:05 · [SHOW] [BREAK] [LOOP-PAYOFF] [JOKE:is-the-explanation]

VO: Not one row matches. Look at payment 1. The reference code: the follower drew its own random number. The time:
350 milliseconds later, from the follower's own clock. And the fee: 60, not 30, because "add 30" arrived twice, and
ran twice.

It's the café again. The date at the top is now. The double price rise is the fee.

And there are quieter ways to differ. Two clients add a payment at the same moment. The leader gives them ids 7 and
8, but the second becomes final first, so the follower runs it first, and gives it 7. Each follower did exactly what
the log said. The log just told it to think for itself.

SCREEN: The follower's table fills with d850e0b3 / e936623d, 1000360 / 1000380, fee 30; then statement 4 arrives again
and the fees become 60. Differing cells red; "statement copy equals the leader: false". Then a small aside: "id 7, id
8: commit order", then cleared.

## Scene 5 · Write the leader's values in · 3:05–3:45 · [PREDICT] [PAUSE] [SHOW] [BREAK]

VO: Can the leader repair this? It can write its own values into each statement: the actual code and the actual
time, instead of random and now. MySQL does some of this. Which difference goes away, and which one stays? Pause and
guess.

Codes and times now match. The fee is still 60. Writing in the leader's values doesn't make "add 30" safe to repeat.

SCREEN: In statements 1 and 3, `md5(random()::text), now()` becomes `'23c52a1a', 1000010` (and the same for row 3).
Countdown. The follower's codes and times turn green; the fee stays red at 60.

## Scene 6 · The rule underneath · 3:45–4:10 · [NAME] [LOOP callback]

VO: The rule underneath: a statement must give the same result every time it runs, wherever it runs. Durable
execution met the same rule: a workflow reads the time and random numbers through the engine, so every replay makes
the same choices. For SQL, nothing enforces it.

SCREEN: Caption "the same result, every time, everywhere". Caption "durable execution: time and random through the
engine".

## Scene 7 · Log what it did · 4:10–4:40 · [SHOW]

VO: So log what the statement did instead. The row log says: payment 1, fee 30, code 23c52a1a. Statement 4 became two
row entries, one for each row it changed. And the row copy matches the leader exactly, resend and all.

SCREEN: The panel becomes "row log" with the six row entries; the two update entries glow. The right table becomes
"follower R", filled from the rows; every cell green; "row copy equals the leader: true".

## Scene 8 · Rule and check · 4:40–5:20 · [GUARDRAIL] [MORAL] [PREDICT] [PAUSE]

VO: So the rule to keep: a statement runs again on every follower. Unless something forces the same result, don't
ship statements. Ship what they did.

One quick check. A follower that was loaded from a copy receives: delete shop m2's payments, limit 100. Does it delete the same 100 as the leader? Pause and think.

No. It deletes the first 100 it meets, and it stores its rows in another order. So it deletes other rows.

SCREEN: The rule in yellow. Then `DELETE FROM payments WHERE merchant = 'm2' LIMIT 100` in the log; six of m2's rows in different orders under leader and
follower (pictured with LIMIT 3); countdown; different rows turn red on each side.

---

### Beat check

- QUESTION/ANALOGY (scene 1) from the lesson's café; FAMILIAR: the numbered log from the last lesson.
- NAME (statement, SQL) right after the familiar log; PREDICT with PAUSE in scenes 3, 5 and 8, SHOW after each.
- BREAK: the demo (scene 4), the pinned values (scene 5).
- GUARDRAIL and MORAL (scene 8) last. Light moments: the priciest coffee, "told it to think for itself".

### Accuracy notes for the producer

- Demo output is the lesson's; the follower runs statements 350 ms later, and the tail of each log is resent.
- The ids 7 and 8 example and the LIMIT check are the section's own text, not demo output.
- MySQL repairs `NOW()` by logging the leader's time, and flags `RAND()`, `UUID()`, updates with `LIMIT` and others as
  unsafe; `MIXED` logs those as rows. The video only says "MySQL does some of this".
- The disk-bytes log (PostgreSQL's WAL) is the next section; the video goes from statements straight to rows, the
  Try's comparison.
