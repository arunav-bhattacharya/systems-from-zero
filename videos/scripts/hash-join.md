# Does the database run the loop? The cloakroom's pigeonholes

- Slug / scene: `hash-join`, `videos/scenes/hash_join.py:HashJoin`
- Lesson: `sql-03`, section 3, "How PostgreSQL finds the pairs without trying them all"
- Audience / level: a complete newcomer who has met the lesson's loop picture of a join (for each row on the left,
  look at every row on the right, keep the pairs that match) and its party cloakroom.
- Length: 4:21 (~690 words of narration at the Kokoro voice's ~180 words a minute, plus a guess, a check and
  silent moves)
- Poster: `POSTER=178` (titles renamed build / hash table / probe, every ticket filed, the three output rows)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: a join is "for each payment, look at every shop". With a million payments, does the
  database really do that?
- Misconception to steelman and break: "once a payment's number lands in a pigeonhole, the shop in that pigeonhole is
  its shop". Broken by payment 5: shop 5 lands in pigeonhole 1, next to Northwind Grocers, and only comparing the
  number stops a wrong pair.
- Concept chain: the loop is the meaning → its cost grows with both tables → file the small side once into
  pigeonholes → each big-side row looks in one pigeonhole → the number on the ticket still decides → names (hash
  function, hash table, bucket, build, probe, hash join) → real cost → limits (equals only, memory, other methods)
- Analogy family: the lesson's party cloakroom. A box of tickets (the shops, the smaller input), a queue of guests
  (the payments), the number each one holds (the shop number). The smart clerk files the tickets into numbered
  pigeonholes before the doors open (the build), then sends each guest to one pigeonhole (the probe).
- Open loops: "does the database have to run the loop?" planted in scene 1 → answered in scene 9.
- Assumptions: the toy is the lesson's stepper exactly (four shops, id mod 4, payments 1, 2, 3 and 5 with shops 1, 2,
  4 and 5; three output rows). The timings are the lesson's (Apple-silicon laptop under Docker Desktop). The shop 8 in
  the check is a made-up arrival for the four-shop toy.

## The one picture

Left: four gold tickets, the shops ("1 Northwind Grocers" ... "4 Volt Electronics"). Middle (from scene 2): a teal
rack of four pigeonholes, numbered 1, 2, 3, 0 top to bottom, as in the lesson's stepper. Right: four blue guests, the
payments ("payment 1 · m1" ... "payment 5 · m5"). Under them, the output rows in green. Yellow marks the row being
handled; red marks a failed comparison. Captions on one line at the bottom.

## Scene 1 · The loop, and its bill · 0:00–0:50 · [FAMILIAR] [QUESTION] [LOOP-PLANT]

VO: A join pairs rows that match. Its meaning is a loop: for each payment, look at the shops, and keep the pairs whose
shop numbers are equal.

Payment 3 has shop 4. So it checks shop 1, shop 2, shop 3, and finds its match at the fourth. Four comparisons, for one
payment.

With four shops, that's nothing. The course's large data set has a million payments and 2,500 shops. With the faster
methods switched off, PostgreSQL joined only the first 10,000 payments this way. That took 0.44 seconds and 6.3
million comparisons. All million payments would take about 40 seconds.

The answer must be what the loop produces. But does the database have to do all that work to get it?

SCREEN: Tickets left, guests right. A yellow line from payment 3 to each ticket in turn; red crosses, then a green
tick on Volt; the output row (3, Volt Electronics). Caption counts "comparisons: 1, 2, 3, 4". Then three stat lines in
the empty middle.

## Scene 2 · The cloakroom · 0:50–1:35 · [ANALOGY] [MAP] [WISH] [JOKE:pivot]

VO: Go back to the party's cloakroom. At the end of the night, a queue of guests wants their coats, and the clerk has
a box of tickets. A slow clerk reads the whole box for every guest. By the hundredth guest, the queue reaches the car
park.

A smart clerk does some work before the doors open. She files each ticket into one of four pigeonholes, by one rule:
the remainder when you divide its number by 4. Then each guest's number points to one pigeonhole, and she looks only
there.

Let's map it. The tickets are the shops, the smaller input. The guests in the queue are the payments. And the number
each one holds is the shop number.

SCREEN: Captions for the slow clerk. The rack of pigeonholes draws in the middle, numbered 1, 2, 3, 0. Captions map
each part as it is said; the titles gain "the tickets" and "the guests".

## Scene 3 · Filing the tickets · 1:35–2:05 · [SHRINK] [SHOW]

VO: Let's file our four shops. Shop 1: 1 divided by 4 leaves 1, so pigeonhole 1. Shop 2 goes in 2, and shop 3 in 3.
And shop 4? 4 divided by 4 leaves nothing, so pigeonhole 0.

That's the first phase. The shops are read once, and never again.

SCREEN: A short copy of each ticket flies into its pigeonhole while the caption shows the remainder.

## Scene 4 · One look per guest · 2:05–2:45 · [PREDICT] [PAUSE] [SHOW]

VO: Now the payments, one at a time. Payment 1 has shop 1: pigeonhole 1, compare the number, a match. Out comes one
row, and it never looked at shops 2, 3 or 4. Payment 2 goes to pigeonhole 2, the same way.

Payment 3 has shop 4. Which pigeonhole? Pause and guess.

(three seconds)

Pigeonhole 0. One look, one comparison, and there's Volt Electronics.

SCREEN: An arrow from each guest to one pigeonhole; "1 = 1" ticks; output rows appear. Countdown bar for the guess.

## Scene 5 · The pigeonhole is a shortlist · 2:45–3:15 · [BREAK] [JOKE:is-the-explanation]

VO: Now payment 5. It has shop 5, which isn't among our four. 5 divided by 4 leaves 1, so it lands in pigeonhole 1,
next to Northwind Grocers.

If the pigeonhole were enough, payment 5 would be paired with Northwind. Wrong shop. So the clerk always checks the
number on the ticket: 1 isn't 5, no match, and an inner join puts out nothing. The pigeonhole gives a shortlist. The
number on the ticket decides.

SCREEN: Arrow to pigeonhole 1; the caption "(5, Northwind Grocers)? the wrong shop" in purple while the filed
Northwind ticket pulses; then "1 ≠ 5" in red in the pigeonhole and the arrow turns red.

## Scene 6 · Names · 3:15–3:40 · [NAME]

VO: Now the names. The filing rule is a hash function: it turns a key into a bucket number. The rack is a hash table,
and each pigeonhole is a bucket. Filing the smaller input is the build. Looking up each payment is the probe. Together,
that's a hash join.

SCREEN: Titles become "merchants (build)", "hash table: id mod 4", "payments (probe)"; captions name each part.

## Scene 7 · What it costs · 3:40–4:00 · [SHOW]

VO: On the large data set, the hash table held all 2,500 shops in about 130 kilobytes. Then one pass over the million
payments: 174 milliseconds on one core, and 67 with two workers sharing it. The loop needed about 40 seconds.

SCREEN: Output rows fade; two bars: the loop, about 40 s (red, long); the hash join, 0.174 s (green, a sliver).

## Scene 8 · Limits · 4:00–4:30 · [GUARDRAIL]

VO: Three limits. Pigeonholes only answer "equal", so a hash join needs an equals sign in the join condition. The rack
has to fit in the memory the work_mem setting allows, 4 megabytes by default, or PostgreSQL splits the work into
batches on disk. And there are other fast ways, such as looking each shop up in an index. The planner, the part of
PostgreSQL that decides how to run a query, estimates the cost of each, and EXPLAIN shows its choice.

SCREEN: Captions, one per limit; the rack's outline glows for the memory limit.

## Scene 9 · The moral, and a check · 4:30–5:00 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, does the database run the loop? The loop says what a join means. The planner decides how to run it. File the
small side once, and send each row of the big side to one bucket.

One quick check. A payment for shop 8 arrives. Which pigeonhole, and what comes out? Pause and think.

(three seconds)

8 divided by 4 leaves 0: pigeonhole 0, where Volt sits. 4 isn't 8, so nothing comes out.

SCREEN: "the loop says what a join means; the planner decides how to run it". A yellow guest "a payment · m8" below the
queue, a countdown, then an arrow to pigeonhole 0 and "4 ≠ 8" in red.

---

### Beat check

- FAMILIAR (the loop from section 0) and QUESTION first (scene 1), with the real bill.
- ANALOGY + MAP said out loud (scene 2), before any name.
- PREDICT with PAUSE (scene 4, and the check in scene 9); SHOW right after.
- BREAK: "the pigeonhole is the answer" run to a wrong pair (scene 5).
- NAME after the mechanism is seen (scene 6). GUARDRAIL (scene 8). MORAL last.
- Light moments: the queue reaching the car park (~1:05), the shortlist line (~3:10), nothing comes out (the check).

### Accuracy notes for the producer

- Every number is the lesson's: 1,000,000 payments and 2,500 shops in the `big` schema; brute force on the first
  10,000 payments took 0.44 s and 6.3 million comparisons (it stops at the first match); about 40 s for all; the hash
  table about 130 kB; 174 ms on one core, 67 ms with two parallel workers; `work_mem` 4 MB by default.
- The four-shop toy, `id mod 4`, the bucket order 1, 2, 3, 0 and the three output rows are the lesson's stepper.
  PostgreSQL's real hash function is not `mod 4`, and its table has far more buckets.
- Left to the lesson: the nested loop with an index scan (265 ms, with Memoize; named only as "other ways"), the merge
  join (named only), Hash Left Join and Hash Anti Join, and NOT IN's hashed SubPlan.
- check_audio: 98.0% at -16.1 LUFS; the differences are Whisper spellings (north wind, postgres, short list, meme for
  "mem", "shop 8" heard as one word). No SAY rule needed beyond work_mem and EXPLAIN.
