# A hundred customers, one loaf: stopping a cache stampede

- Slug / scene: `cache-stampede`, `videos/scenes/cache_stampede.py:CacheStampede`
- Lesson: `cache-06`, section 3, "A hundred requests miss the same key at once: the stampede"
- Audience / level: a complete newcomer. Knows the bakery picture from the lesson's opening and that a cache keeps
  copies; doesn't know what a TTL, a thread, a future or a lock is.
- Length: 5:42 (~900 words of narration at Kokoro's ~175 words a minute, plus two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=263.4` (the lock has given one call across four copies; the scoreboard is full)
- The learner's real question: a cache exists to save the database work. Can it ever make the database busier?
- Misconception to steelman and break: "the first request that misses reloads the key, and the rest find it in
  Redis". Broken by timing: the reload takes 200 ms and all hundred have already asked. Second wrong model: "single-flight
  fixes it", broken by four copies of the app that can't see each other's map.
- Concept chain: cache-aside and a TTL → a busy key expires and every request misses at once (stampede) → one
  leader per key inside a program (single-flight) → copies of the app can't see each other → a sign on a shared board:
  `SET lock NX PX` in Redis → the lock only saves work (hardest last)
- Analogy family: the lesson's bakery. The shelf by the door is Redis, the baker at the back is the database, a loaf is
  one copy of a row with a sell-by time (its TTL), customers are requests; "I've asked, wait here" is single-flight;
  a sign on a shared board is the Redis lock.
- Open loops: "can a cache make the database busier?" planted in scene 1 → answered in scene 10; "the first one
  reloads it" voiced in scene 4 → broken at once; the bakery's visible queue in scene 5 → broken in scene 6.
- Assumptions: all numbers are the lesson's (100 reads a second, 0.3 ms hits, 200 ms loads, 100 misses → 100 calls,
  pool of 20 so 80 wait, single-flight 1 call and about 210 ms, 4 pods → 4 calls, the lock → 1 call, PX 2000, polling
  every 10 ms for up to a second). The clock times are the stepper's. "Pod" is said as "copy of the app".

## The one picture

Left: one copy of the app, a box of 100 dots (one per request); later it splits into four strips of 25 ("copy 1" to
"copy 4"). Middle top: Redis, "the shelf", holding `merchant:m-17`; later a second line for the lock. Middle bottom,
on the road from the app to the database: the single-flight map (gold). Right: the database, "the baker", with
"queries running", a pool of 20 connection slots and "waiting in line". A clock on top, a scoreboard of database calls
under everything, captions at the bottom. Green is a hit or a reply, red a miss, yellow the leader, grey a request
that waits.

## Scene 1 · The question · 0:00–0:24 · [QUESTION] [LOOP-PLANT]

VO: A cache is there to protect the database. Every answer it gives is a query saved. So can a cache ever make the
database busier? At ten one morning, the database gets the same query a hundred times at once. And the cache is the
reason.

SCREEN: Title card. The caption "can a cache make the database busier?"; the database box appears on the right and a
burst of red dots hits it, "the same query x 100".

## Scene 2 · The bakery · 0:24–1:04 · [FAMILIAR] [ANALOGY] [MAP]

VO: Picture a bakery with a shelf of bread by the door. Customers take a loaf and go. When the shelf is empty, a
customer asks the baker at the back, who takes a while to bake one. In the payments app, the shelf is Redis, a program
that keeps data in memory. It holds copies of rows from the slower database, the baker. A loaf is one copy of a row,
with a sell-by time: its TTL, or time to live. When it runs out, the copy is gone. The rule: ask Redis first. If the
copy is there, that's a hit. If not, that's a miss: load the row from the database, put it back in Redis, and go.

SCREEN: The three boxes: customers (a box of dots), the shelf (a loaf icon), the baker. On the mapping, the labels
become "one copy of the app", "Redis" (subtitle "the shelf") and "database" (subtitle "the baker"); the loaf becomes
`merchant:m-17` with a TTL bar. A dot runs to Redis and back green (hit); then one runs, comes back red, goes along the
lower road to the database, and back to Redis (miss, load, set).

## Scene 3 · The busy shop · 1:04–1:24 · [SHRINK] [SHOW]

VO: Now take the busiest shop on a sale day, merchant m-17, read a hundred times a second. Every read is a hit, and
the database never hears about it. Then, at ten o'clock, the TTL runs out. And loading the row takes 200 milliseconds.

SCREEN: Clock 09:59:58. Dots stream to Redis and back green; "queries running: 0". The TTL bar drains; at 10:00:00.000
the key turns red, "expired". "200 ms a load" glows on the database.

## Scene 4 · Predict, then the stampede · 1:24–2:24 · [PREDICT] [PAUSE] [BREAK] [SHOW] [NAME] [JOKE:release]

VO: Within a few milliseconds, a hundred requests ask for the key, and all of them miss. Each one follows the rule.
How many database queries? Pause and guess. The hopeful answer is one: the first request reloads it, and the rest find
it in Redis. But the reload takes 200 milliseconds, and all hundred have already asked. None of them knows about the
others, so each one queries the database: a hundred queries. With a pool of 20 database connections, 80 queries wait
in line, and every other query waits behind them. This is a cache stampede, also called a thundering herd: a hundred
customers walking to the back of the bakery for the same loaf. The baker bakes the same bread a hundred times. Very
fresh, and ninety nine times pointless. So the moment a busy copy expires, the cache sends everyone at once.

SCREEN: Clock 10:00:00.005, all 100 dots red, Redis "(nil) x 100". Countdown. "the first one reloads it?" in purple.
Clock 10:00:00.010: 100 red dots run along the lower road; "queries running" counts to 100; the 20 pool slots fill;
"waiting in line: 80". Scoreboard: "no protection: 100". Caption "cache stampede (thundering herd)".

NOTE: The joke comes after the count, never during it, and is cashed back in the next sentence.

## Scene 5 · I've asked, wait here · 2:24–3:16 · [WISH] [ANALOGY] [SHOW] [NAME] [JOKE:reward]

VO: What we want is what polite customers do. The first one says: I've asked, wait here. Let's replay ten o'clock.
Inside one program, each request runs as a thread, one path of work. The threads share a map, a table of keys and
values: in Java, a ConcurrentHashMap. Each thread that misses makes an empty box for the result, a CompletableFuture,
and tries putIfAbsent: add my box under the shop's key, only if nothing is there yet. The first thread succeeds. It's
the leader, and it queries the database. The other 99 find the leader's box already there, and wait on it. After 200
milliseconds, the leader puts the row in Redis and in its box. All 99 wake up with the same value, and the leader
clears its entry. One query instead of a hundred, and everyone waited about 210 milliseconds. This is single-flight:
one load in flight per key. A hundred customers, one loaf, and a baker who gets to sit down.

SCREEN: Every dot back to red at 10:00:00.005. The gold map box drops onto the road. The first dot turns yellow and a
gold box "m-17: leader's future" appears in the map; the other 99 turn grey, "99 wait on it". One yellow dot to the
database: "queries running: 1", one pool slot gold. Clock 10:00:00.210: a dot back to Redis (cached again), the
future fills, all 100 dots turn green, the map entry goes ("(empty)"). Scoreboard: "single-flight: 1".

## Scene 6 · Four copies · 3:16–3:48 · [BREAK] [PREDICT]

VO: So far so good. But a busy app runs many copies of the same program, so one can fail and the work is shared. Say
four copies, 25 requests each, each with its own map. How many queries now? Four. Each copy's leader asks the
database, because no copy can see another copy's map. Here the bakery picture breaks. In a shop, everyone sees who's
at the counter. Copies of an app see nothing of each other: they need a sign on a shared board.

SCREEN: The box splits into four strips, "copy 1" to "copy 4", 25 dots each, a small gold map at the end of each. All
red; one yellow leader per strip; four yellow dots to the database, "queries running: 4". Scoreboard: "4 copies: 4".
Caption "each copy sees only its own map".

## Scene 7 · A sign on the shared board · 3:48–4:24 · [SHOW] [NAME] [JOKE:is-the-explanation]

VO: Redis can be that board, since every copy talks to it. Replay ten o'clock once more. On a miss, the copy tries to
put up the sign: SET lock:merchant:m-17, a token, NX, PX 2000. NX means only if the key doesn't exist yet, so exactly
one copy wins. The token says whose sign it is. PX 2000 rubs the sign out after 2,000 milliseconds, in case its writer
wanders off. The winner loads the row and puts it in Redis. The others check Redis every 10 milliseconds, for up to a
second. In the lesson's demo, that made one database call across four copies.

SCREEN: Everything red again. Four dots race to Redis; one comes back yellow, three come back with a cross. A yellow
line in Redis: "lock:merchant:m-17 = token, NX PX 2000". One dot to the database ("queries running: 1"), back to
Redis; the waiting copies' small dots ping Redis and turn green. Scoreboard: "lock: 1".

## Scene 8 · What the sign is for · 4:24–4:50 · [GUARDRAIL]

VO: This lock only saves work. If the winner crashes before it fills the cache, the others stop waiting after a second
and load the row themselves. That's wasted work, not a wrong answer. A lock that must never fail is a harder problem,
for a later lesson. And keep single-flight too, so only one thread per copy even reaches for the sign.

SCREEN: The winning copy's strip goes grey with a cross; the lock line fades after a 2 s bar; the waiters' 1 s bar
ends and two dots go to the database, "harmless: the same row twice". Caption "single-flight first, then the sign".

## Scene 9 · The code, in Java and Kotlin · 4:50–5:08 · [SHOW]

VO: Here are both pieces, in Java and in Kotlin. putIfAbsent picks one leader inside a copy, and everyone else joins
its future. SET with NX and PX picks one copy across all of them. Both languages send Redis the same command.

SCREEN: The diagram dims. Two panels side by side, `SingleFlight` lines and the lock line, Java on the left and Kotlin
on the right, as in the lesson's demo. The `putIfAbsent` lines glow, then the `nx().px(2_000)` lines.

## Scene 10 · The moral, and a check · 5:08–5:40 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, can a cache make the database busier? For a moment, yes: when a busy copy expires, everyone misses together.
The fix is to send one customer to the back: single-flight inside each copy, and a sign in Redis across all of them.
One quick check. Twenty copies, each with single-flight, and no sign in Redis. The busy key expires. How many database
queries? Pause and think. Twenty: one leader in each copy, because no copy can see another's map. Next, we'll bake the
next loaf a little before the shelf runs out.

SCREEN: The diagram returns. "one customer to the back" in yellow over the scoreboard. The four strips become "20
copies"; countdown; "20" appears on the database's counter. Last caption: "one customer to the back".

---

### Beat check

- Opens with QUESTION (scene 1). FAMILIAR + ANALOGY + MAP before any term (scene 2).
- PREDICT with PAUSE (scene 4, and the check in scene 10); the hopeful answer is steelmanned and broken at once (scene
  4); the bakery's limit is broken in scene 6.
- NAME after each SHOW: cache stampede (scene 4), single-flight (scene 5), the lock's NX and PX (scene 7).
- GUARDRAIL (scene 8), MORAL and the check (scene 10). Light moments: the hundred loaves (about 2:15), the baker who
  sits down (3:10), the writer who wanders off (4:05).
- Open loop paid off by name: "can a cache make the database busier?" (scene 10).

### Accuracy notes for the producer

- Numbers are the lesson's section 3, its stepper and the `StampedeDemo` output: `no protection, 1 pod` 100 calls,
  `single-flight, 1 pod` 1, `single-flight, 4 pods` 4, `Redis lock (SET NX PX), 4 pods` 1; every line about 205 to
  245 ms; the body's "about 210 ms".
- The demo's fake database never slows down, so its first line takes about 200 ms too. The video's queue of 80 is the
  lesson's description of a real pool of 20 connections.
- The 100 dots stand for 100 requests in one pod; the four strips for the demo's 4 pods with 25 requests each.
- The demo's single-flight leader checks Redis once more before it loads (another leader may have just filled it);
  the video leaves that check to the lesson.
- Releasing the lock (`DELEX ... IFEQ` in Redis 8.4, or a Lua compare-and-delete before) is left to the worked example.
- XFetch, the next section, is only named as the bridge ("bake the next loaf before the shelf runs out").
