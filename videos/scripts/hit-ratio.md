# Nine points or ten times? Count the misses

- Slug / scene: `hit-ratio`, `videos/scenes/hit_ratio.py:HitRatio`
- Lesson: `cache-01`, section 2, "Count the misses: why 99% hits is ten times better than 90%"
- Audience / level: a complete newcomer. Knows a program can ask a database for data; doesn't know what a cache,
  a hit, a miss or Redis is.
- Length: 3:54 (~570 words at Kokoro's ~165 words a minute, plus two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=162`, the end of scene 5 (the grid at 99.9%, the table's three rows filled: 1.45 ms and 10,000; 0.595 ms and
  1,000; 0.5095 ms and 100)
- The learner's real question: a cache that answers 99 lookups in 100 instead of 90 is "nine points better". Is that
  a small win or a big one?
- Misconception to steelman and break: "count the hits: 90 and 99 are close". Broken by counting the misses the
  database sees (10,000 a second against 1,000), and again by a payment that makes 30 lookups (74% all hit).
- Concept chain: a cache is a jug of copies by the counter → a hit pours, a miss walks to the storeroom → the average
  and the database's load are two formulas in h → the database feels only the misses (ten times fewer from 90 to 99)
  → near 100% the average stops moving but the load keeps falling → many lookups per request multiply the misses
  (hardest last)
- Analogy family: the lesson's barista with a jug of milk on the counter, who walks to the storeroom only when it runs
  out.
- Open loops: "nine points: a small win or a big one?" planted in scene 1 → answered in scene 8.
- Assumptions: the lesson's round numbers, labelled as made up for teaching: 0.5 ms from Redis, 10 ms from a busy
  database, 100,000 lookups a second; results 1.45 ms and 10,000, 0.595 ms and 1,000, 0.5095 ms and 100; 30 lookups at
  99% all hit with probability 0.99^30, about 74%. Which of the 100 dots are misses, and which of four payments meets
  a miss, are made up for the picture. The code is the two formulas, checked by computing the three rows.

## The one picture

Top: the flow, three boxes in a row: the payments program, the jug (the Redis cache, 0.5 ms, teal) and the storeroom
(the database, 10 ms, red), with arrows. Left: 100 lookups as a 10 by 10 grid of dots, green for hits, red for misses.
Right: the results table (hit ratio, average lookup, database queries a second), one row per hit ratio. Under the
table: the arithmetic for the current row. Green is a hit, red a miss and its cost, yellow the question.

## Scene 1 · The jug, and the question · 0:00–0:45 · [FAMILIAR] [ANALOGY] [QUESTION] [LOOP-PLANT]

VO: Picture a busy café. The barista makes a latte every thirty seconds, and never walks to the storeroom for milk.
A jug sits on the counter, and she goes to the back only when it runs out. Walking takes far longer than pouring.
The payments program behind the card reader has the same choice. For every tap, it needs the shop's details from a
database on another computer. So it keeps a copy close by. Say that copy answers 90 lookups in 100, and someone tunes
it to 99. Nine points better. Is that a small win, or a big one? Hold that thought.

SCREEN: Title card. The flow draws in: "the barista" → "the jug, on the counter" (pour: quick) → "the storeroom, at the
back" (walk: slow); a dot pours quickly, another walks slowly. The boxes relabel: "payments program", "a copy close
by", "database, on another computer". Caption "90 in 100 → 99 in 100: nine points. Small win or big?".

## Scene 2 · Map it · 0:45–1:25 · [MAP] [NAME] [SHRINK]

VO: Let's map the café. The jug is the cache: a small, fast store of copies. The storeroom is the database. A lookup
the jug can answer is a hit. One that sends you to the back is a miss. Here the cache is Redis, a program that holds
data in memory and hands it out over the network. Round numbers, made up for teaching: a lookup takes half a
millisecond from Redis, and 10 milliseconds from a busy database. At the busiest hour, there are 100,000 lookups a
second.

SCREEN: Captions map "the jug = the cache", "the storeroom = the database". A green dot to the cache and back: "a hit";
a red dot on to the database: "a miss". Labels "Redis cache: 0.5 ms", "database: 10 ms"; "100,000 lookups a second
(round numbers, made up for teaching)".

## Scene 3 · Ninety in a hundred · 1:25–1:55 · [SHOW]

VO: Take 100 lookups at 90% hits. Ninety pour from the jug. Ten walk to the storeroom. The average lookup is 0.9 times
0.5, plus 0.1 times 10: 1.45 milliseconds. And the database gets the misses: 10% of 100,000, so 10,000 queries a
second.

SCREEN: The grid fills: 90 green, 10 red. "0.9 x 0.5 + 0.1 x 10 = 1.45 ms"; "0.1 x 100,000 = 10,000 a second". The
table's first row: "90% | 1.45 ms | 10,000".

## Scene 4 · Predict 99% · 1:55–2:25 · [PREDICT] [PAUSE] [SHOW]

VO: Now 99% hits. Before we count, how many queries reach the database each second? Pause and guess.

(three seconds)

1,000. Ten times fewer: one red dot in a hundred, instead of ten. And the average drops to 0.595 milliseconds, more
than twice as fast.

SCREEN: Countdown. Nine red dots turn green; "0.01 x 100,000 = 1,000 a second"; "0.99 x 0.5 + 0.01 x 10 = 0.595 ms".
Row 2: "99% | 0.595 ms | 1,000".

## Scene 5 · Count the misses · 2:25–3:25 · [BREAK] [NAME] [JOKE:is-the-explanation] [SHOW]

VO: So where did nine points come from? We counted the hits, and 90 and 99 look close. But the database never sees a
hit. It sees only the misses, and 10 misses against 1 is ten times the load. The share of hits is the hit ratio, and
what's left is the miss ratio. 98% hits and 2% misses describe the same cache. Only the second tells you what the
database sees. Ninety-nine percent sounds like top marks, but the database only marks the one percent. Push on to
99.9%. The average hardly moves, 0.5095 milliseconds, because it's already close to the cache's own half a
millisecond. But the database load falls tenfold again: 100 a second.

SCREEN: Purple caption "nine points: counting the hits". The green dots dim and the red ones glow; "10 misses → 1:
ten times fewer". Captions "hit ratio h: hits / all lookups", "miss ratio: 1 - h", "98% hits = 2% misses: only the
misses reach the database". Row 3: "99.9% | 0.5095 ms | 100"; the average column glows ("close to 0.5 ms"), then
the database column ("10,000 → 1,000 → 100").

## Scene 6 · Thirty lookups · 3:25–3:55 · [GUARDRAIL]

VO: One more trap. A card payment doesn't make one lookup. Say it makes 30, each with 99% hits. All 30 hit only 74% of
the time: 0.99 multiplied by itself 30 times. So about one payment in four waits for at least one slow read. A cache
with a great average still leaves many requests slow.

SCREEN: The grid becomes four payments, each a row of 30 small squares; three rows all green, one with a red square.
"0.99^30 = 0.74: all 30 hit"; "about 1 payment in 4 meets a miss". Caption "a great average still leaves many
requests slow".

## Scene 7 · The formulas as code · 3:55–4:15 · [SHOW]

VO: Here are the two formulas as code, in Java and Kotlin. The average is h times the hit time, plus one minus h,
times the miss time. The database's load is one minus h, times the lookups.

SCREEN: Two panels side by side. Java: `double avgMs = h * hitMs + (1 - h) * missMs;` and `double dbPerSec = (1 - h) *
lookupsPerSec;`. Kotlin: `val avgMs = h * hitMs + (1 - h) * missMs` and `val dbPerSec = (1 - h) * lookupsPerSec`. Each
line glows as it's read; the table's rows pulse.

## Scene 8 · The moral, and a check · 4:15–4:50 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, nine points: small win or big? Big. Ninety to ninety-nine is ten times fewer misses, and the misses are what
the database pays for. Count the misses, not the hits. One quick check. A cache goes from 95% hits to 99%. How many
times fewer requests reach the database? Pause and think.

(three seconds)

Misses drop from 5 in 100 to 1 in 100: five times fewer.

SCREEN: The moral in yellow. The check: the grid shows 5 red dots; countdown; 4 turn green: "5 misses → 1: five times
fewer". Last caption "the database feels only the misses: count them".

---

### Beat check

- FAMILIAR + ANALOGY (the jug) and the QUESTION (scene 1); MAP said out loud and NAME cache, hit, miss (scene 2).
- SHOW (scene 3), PREDICT with PAUSE then SHOW (scene 4).
- BREAK of "count the hits" and NAME hit ratio and miss ratio after the counts (scene 5).
- GUARDRAIL (scene 6: many lookups per request). Code last and short, Java and Kotlin side by side (scene 7).
- MORAL, LOOP-PAYOFF and the check (scene 8). Light moments: "walking takes far longer than pouring" (0:12), "the
  database only marks the one percent" (2:55).

### Accuracy notes for the producer

- 0.5 ms, 10 ms and 100,000 lookups a second are the lesson's round numbers, labelled on screen as made up for
  teaching. 1.45, 0.595 and 0.5095 ms, and 10,000, 1,000 and 100 a second, were computed from them.
- 0.99^30 = 0.7397. "One payment in four" is the lesson's wording.
- The 95% to 99% check is the lesson's Try it (the issuer's load falls fivefold).
- The lesson's scale examples (Meta's TAO, Uber's cores) and Memcached's 1,740-item page views are left to the lesson.
- The aside on why Redis is faster than the database (no SQL to plan, no disk) is left to the lesson.
