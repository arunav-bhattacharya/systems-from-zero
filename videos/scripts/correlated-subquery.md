# Thirteen hours for one question: a subquery that runs once per row

- Slug / scene: `correlated-subquery`, `videos/scenes/correlated_subquery.py:CorrelatedSubquery`
- Lesson: `sql-05`, section 1, "A subquery that runs again for every row"
- Audience / level: a complete newcomer who has met a subquery used as a value (section 0) and GROUP BY (the last
  lesson). No idea how a database runs a query.
- Length: 4:48 (~790 words of narration at the Kokoro voice's ~180 words a minute, plus a guess, a check and
  silent sweeps)
- Poster: `POSTER=124` (run 3: shop 4's seven stripes lit in the pot, the panel's "129900 > 48620.86 ? yes: keep", the
  counters at 3 runs and 111 rows)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: the query reads exactly like the question and answered at once on 37 payments. Why
  would it take 13 hours on a million?
- Misconception to steelman and break: "a query that reads like the question is cheap, because the database finds a
  fast way". Broken by counting: 30 runs and 1,110 rows read for 6 different answers, then 51 ms a run times
  930,826 payments.
- Concept chain: one overall average runs once → a per-shop average needs the outer row's shop → so it runs once per
  outer row (correlated, SubPlan) → each run reads the whole table → the cost is rows × table → work out every
  shop's average once and join → when it's fine anyway (rewritten to joins, an index, few rows) → name every column
- Analogy family: the lesson's kitchen. The easy subquery is a cook who makes one pot of sauce before dinner; this one
  is a cook told "for each guest, go and taste the sauce": one walk to the pot per guest. The guest is the outer row,
  the pot is the payments table, each walk is one run. The fix extends it: taste each dish once and write it on a
  card.
- Open loops: "why 13 hours?" planted in scene 1 → paid off in scene 8.
- Assumptions: the outer rows, averages, counters and the six-average hash table are the lesson's stepper; the
  stripes in the pot that light up are the real succeeded payments of each shop in the seed (shop 1: 1, 7, 11, 14, 24,
  29, 34; shop 2: 2, 25, 30; shop 4: 3, 8, 17, 18, 19, 28, 31). Timings are the lesson's.

## The one picture

Top: the query, `p.merchant_id` in yellow. Left: the outer rows, the guests (payments 1 to 5 and "... 30 succeeded
rows"). Middle: the pot, `payments p2`, 37 thin stripes, one per payment; a yellow bar sweeps it on every run and the
kept stripes light gold. Right: what this run did (the shop plugged in, rows kept, the average, the comparison) and two
counters (runs, rows read). In the fix, the right side becomes a teal hash table of six averages. Captions at the
bottom.

## Scene 1 · The question · 0:00–0:35 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: Picture a team asked a simple question: which payments were bigger than their own shop's usual payment? A 5.50
payment is tiny for Volt Electronics, which sells laptops. At Metro Transit, where a ride costs 2.75, it's twice the
usual fare. So each payment has to be compared with its own shop's average.

The team writes the query the way they'd say it, and tests it on 37 payments. It answers at once. On the full data, a
million payments, it doesn't come back. At that pace, it would need about 13 hours. Why?

SCREEN: Two lines, "5.50 at Volt Electronics, which sells laptops: tiny" and "5.50 at Metro Transit, where a ride costs
2.75: twice the fare". Then the query at the top, "37 payments: an answer at once" (green) and "1,000,000 payments:
about 13 hours" (red) in the middle, and "why?".

## Scene 2 · The value from outside · 0:35–1:05 · [FAMILIAR] [SHRINK]

VO: Comparing every payment with one overall average is easy. The subquery, the query in parentheses, runs once,
before anything else, and its answer is reused.

This subquery asks for the average of this payment's shop. That shop number comes from outside, from the row being
tested, the outer row. So the subquery can't run until there is an outer row.

SCREEN: "one overall average: 24015.17, worked out once, before anything else, then reused" (the lesson's section 0
figure). Then `p.merchant_id` glows yellow and the outer rows appear on the left.

## Scene 3 · The kitchen · 1:05–1:35 · [ANALOGY] [MAP]

VO: A kitchen helps. The easy subquery is a cook who makes one pot of sauce before dinner starts. This one is a cook
told: for each guest, go and taste the sauce. One walk to the pot per guest, even when two guests ordered the same
dish.

So the guest is the outer row, a payment. The pot is the payments table. And each walk is one run of the subquery.

SCREEN: The pot (37 stripes) draws in the middle; captions map each part as it is said.

## Scene 4 · Watch it run · 1:35–2:45 · [SHOW] [PREDICT] [PAUSE]

VO: Let's watch. Row 1 belongs to shop 1. PostgreSQL plugs in 1 and runs the subquery. It reads all 37 payments,
keeps shop 1's seven succeeded ones, and averages them: 4704.86. 4250 isn't bigger, so row 1 is dropped.

Row 2, shop 2. The subquery runs again from the start: another 37 rows, average 1935. 1890 is below it. Dropped.

Row 3, shop 4: a third run, average 48620.86. 129900 is above it, so payment 3 is kept.

There are 30 succeeded payments. How many runs, and how many rows read? Pause and guess.

(three seconds)

30 runs, and 1,110 rows read, for only 6 different answers. Payment 17 also belongs to shop 4, and the subquery works
out the same average for it all over again.

SCREEN: For each row, an arrow to the pot, a yellow sweep, the kept stripes lit, the panel and the counters; row 3's
outline turns green when it is kept. Countdown. Then the counters jump to 30 and 1,110.

## Scene 5 · Thirteen hours · 2:45–3:20 · [BREAK] [NAME] [JOKE:release]

VO: On the large data set, each run reads all million payments to find one shop's rows. That's about 51 milliseconds a
run. For the first 20 payments, 1.1 seconds. For all 930,826 succeeded payments, about 13 hours. An overnight answer
to an afternoon question.

So reading like the question doesn't make a query cheap. Here PostgreSQL does exactly what the words say, once for
every payment. A subquery that refers to the outer row is called correlated. EXPLAIN, the command that shows the plan,
calls it a SubPlan, and counts its runs as loops.

SCREEN: Captions with the numbers; the panel reads "large data set: 51 ms per run", "930,826 runs: about 13 hours".

## Scene 6 · Taste each dish once · 3:20–4:00 · [SHOW]

VO: The fix turns the work around. Taste each dish once. One pass over the payments with GROUP BY works out all six
shop averages, and keeps them in a hash table, a lookup table in memory.

Then a second pass reads each payment once, and looks up its shop's average in one step. Two passes, 74 rows read
here. Written as a join, on the large data set, it answers for all 930,826 payments in 282 milliseconds.

SCREEN: The query becomes the join. One sweep of the pot fills the six teal cards (m1 4705, m2 1935, m3 344, m4 48621,
m5 55917, m7 1498). Each outer row and its card glow together. Counters: "averages computed: once", "rows read: 74".

## Scene 7 · When it's fine, and a trap · 4:00–4:35 · [GUARDRAIL]

VO: Correlated subqueries are not always slow. PostgreSQL rewrites EXISTS, NOT EXISTS and IN into joins on its own, but
not a subquery that works out an average, like this one. And one that finds its rows through an index, a sorted
catalogue, is cheap when the outer query has few rows. So read the plan: a SubPlan that loops as many times as a big
table has rows is the one to rewrite.

One trap: name every column. Write merchant_id equals merchant_id without the short names, and both find the inner
table. The condition is always true, and you're back to the overall average, with no error.

SCREEN: Captions; then `WHERE merchant_id = merchant_id` in red at the top, both names pointing into the pot.

## Scene 8 · The moral, and a check · 4:35–5:00 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, why 13 hours? A subquery that depends on the outer row runs once per row. Work it out once for every key, and
join.

One quick check. In the join version, payment 17 comes along. Is shop 4's average worked out again? Pause and think.

(three seconds)

No. It's already on its card, 48621. One look, and one comparison.

SCREEN: "runs once per row: work it out once per key, and join". For the check, a yellow outer row "17 m4 18999", a
countdown, then the m4 card glows.

---

### Beat check

- QUESTION first, from a felt mismatch (5.50 at two shops) and the 13 hours (scene 1).
- FAMILIAR: the one-average subquery that runs once (scene 2).
- ANALOGY + MAP said out loud (scene 3).
- SHOW the runs, PREDICT with PAUSE (scene 4), and the check (scene 8).
- BREAK: "reads like the question, so it's cheap" (scene 5), then NAME (correlated, SubPlan, loops).
- The fix shown in the kitchen and the picture (scene 6). GUARDRAIL (scene 7). MORAL last.
- Light moments: an overnight answer to an afternoon question (~2:55); the always-true trap (~4:30).

### Accuracy notes for the producer

- Stepper values: row 1 (shop 1) 4250 vs 4704.86, dropped; row 2 (shop 2) 1890 vs 1935.00, dropped; row 3 (shop 4)
  129900 vs 48620.86, kept; 30 runs, 1,110 rows read, 6 different answers; join: 37 rows to build, 74 in all; the
  six rounded averages.
- Large data set (lesson): about 51 ms per run, 1.1 s for the first 20 payments (19 runs, since one failed),
  930,826 succeeded payments, about 13 hours; the join 282 ms. Apple-silicon laptop under Docker Desktop.
- The rewrite rule (EXISTS, NOT EXISTS, IN become joins; an aggregate subquery isn't rewritten in PostgreSQL 18),
  the index caveat and the alias trap are the lesson's.
- The 5.50 and 2.75 figures are the lesson's.
- 24015.17 (the average succeeded payment) is the lesson's section 0 figure.
- Left to the lesson: InitPlan by name, the exact EXPLAIN output, and WITH (sections 2 and 3).
- Pronunciation: `SAY` rules for the digit possessive ("shop 1's", "shop 4's") and for "subqueries" (Kokoro said
  "subgears"). "aren't always slow" sounded like "are always slow", so the line now says "are not always slow".
- check_audio: 97.1% at -16.1 LUFS; the rest are number formatting (4 700 4, 48 600 20) and Whisper spellings (postgres, catalog).
