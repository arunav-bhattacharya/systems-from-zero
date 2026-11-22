# The right route for the wrong traffic: how a planner picks a join order

- Slug / scene: `join-order`, `videos/scenes/join_order.py:JoinOrder`
- Lesson: `store-10`, section 3, "Searching for the cheapest order of joins, with the guesses it has"
- Audience / level: a complete newcomer. Knows a table has rows and that a join pairs rows of two tables; doesn't know
  what a planner, a join order, dynamic programming or EXPLAIN ANALYZE is.
- Length: about 4:30 (~740 words of narration, two pauses, silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: a database picks one plan out of many without running any. How does it search, and
  why does it sometimes pick the plan that does more than four times the work?
- Misconceptions to steelman and break: (1) "list every order and price it" (6 orders for 3 tables, 3.6 million for
  10); (2) "the slow plan means the search is broken, so force the order yourself" (the search was right for its
  guesses; with the right guess, the same search picks the other plan)
- Concept chain: the order of joins changes the in-between work → the number of orders explodes → orders share parts,
  so solve small groups once and build up (dynamic programming) → the search prices plans with guessed row counts →
  a wrong guess at the bottom travels up and picks the wrong plan (hardest: predict the real count) → fix the guess,
  not the search
- Analogy family: the lesson's map app. It picks a route in a second, knowing the roads and guessing the traffic, and
  sends you past the stadium before a match. The fastest way to the bridge stays the fastest, whatever comes after.
  Where it breaks: the app re-routes you on the way; PostgreSQL never changes a plan once it starts.
- Open loops: "was the search broken?" planted in scene 1 → paid off in scene 6 ("the search was right for what it was
  given") and scene 7
- Assumptions: all numbers are the lesson's (10,000 shops, three conditions at 10% each, est 10, actual 1,000;
  1,000,000 payments; 20,000 chargebacks; pairs est 1,000 and 20,000; plan A 1,020 vs B 20,020 estimated, 102,000
  vs 22,000 real, 4.6 times; 6, 720 and 3.6 million orders; 1,023 groups for 10 tables; System R 1979; 12 tables;
  103,172 vs 6,542 buffers, 16 times fewer; the benchmark's 38% and about 1 in 10). The map is a drawing, with no
  times besides the lesson's forty minutes.

## The one picture

After the map prelude: the lesson's stepper as a lattice. Bottom: three tables (merchants with its three filters,
payments, chargebacks), each with its row count. Middle: the two pairs a join condition connects. Top: all three. The
right panel holds the order counts, then the two plans' prices (A gold, B teal), first guessed, then real. A query chip
across the top. Captions at the bottom. Yellow is a guess, red a wrong guess or wasted work, green the fixed guess.

## Scene 1 · The map app · 0:00–0:35 · [FAMILIAR] [ANALOGY] [QUESTION] [LOOP-PLANT]

VO: Your phone's map app picks the fastest way to a friend's birthday dinner in a second, out of hundreds of routes,
without driving any of them. It knows how long each road is, and it guesses how busy each one will be. Tonight it sends
you past the football stadium an hour before a match. Forty minutes in traffic. So, was the search broken? Hold that
thought. A database has the same job every time you ask it a question.

SCREEN: Title card. Home and dinner dots; two roads, one past a stadium. The top road lights yellow ("expected:
quiet"), then fills with red dots ("a match crowd: 40 minutes in traffic"); caption "was the search broken?".

## Scene 2 · Three tables, many orders · 0:35–1:30 · [SHRINK] [NAME] [PAIN]

VO: Every night, a report counts chargebacks, payments that customers disputed, at shops in Amsterdam. It joins three
tables: 10,000 shops, a million payments, and 20,000 chargebacks. A join pairs the rows of two tables that belong
together. Before anything runs, the planner, the part of the database that picks how to run a query, has to choose
which two tables to join first. The order changes how many rows pile up in the middle. And the number of orders
explodes. Adding one table at a time, 3 tables can be joined in 6 orders, 6 tables in 720, and 10 tables in 3.6
million. Pricing every one works for 3 tables and is hopeless for 12.

SCREEN: The three tables fade in at the bottom with their sizes; the query chip `city = 'Amsterdam' AND country =
'NL' AND currency = 'EUR'`. Right panel: "3 tables: 6 orders", "6 tables: 720", "10 tables: 3.6 million", growing.

## Scene 3 · Small groups first · 1:30–2:20 · [ANALOGY] [MAP] [NAME]

VO: But orders share parts. Think of the map again. The fastest way to the bridge is still the fastest way to the
bridge, whatever road you take after it. So the planner finds the best plan for each small group of tables once, and
builds bigger groups only from those. Single tables first, then every pair that a join condition connects, then all
three. That's dynamic programming: solve each small problem once, keep the answer, and build the big one from it. IBM's
System R, one of the first SQL databases, introduced it in 1979. It visits about 1,000 groups for 10 tables, instead of
3.6 million orders, and PostgreSQL searches this way up to 12 tables.

SCREEN: Lines draw up from the tables to two pair boxes, then to "all three tables". The pair "shops + chargebacks"
appears dimmed with "no join condition: skipped". Right panel: "10 tables: 1,023 groups, not 3.6 million orders".

## Scene 4 · Pricing with guesses · 2:20–3:05 · [SHOW]

VO: Now each box gets a guess. The shops have three conditions, and each keeps a tenth, so the planner multiplies: 10
shops. Shops with their payments: about 1,000 rows. Payments with chargebacks: 20,000. The lab's price is the rows the
joins produce along the way. Plan A, shops with payments first: 1,000, then 20, so 1,020. Plan B, payments with
chargebacks first: 20,020. Plan A wins by a mile.

SCREEN: "est 10", "est 1,000", "est 20,000", "est 20" appear in yellow. Price cards: "A: 1,000 + 20 = 1,020", "B:
20,000 + 20 = 20,020"; A's path through the lattice lights gold; a tick by A.

## Scene 5 · Predict, then run · 3:05–3:45 · [PREDICT] [PAUSE] [BREAK] [SHOW] [JOKE:release]

VO: Here's the catch. Every shop in Amsterdam is in the Netherlands and takes euros. So how many shops really pass the
three conditions? Pause and guess. (three seconds) 1,000, not 10. The second and third conditions removed nobody. And
the error climbs: the first join makes 100,000 rows, not 1,000, and the answer is 2,000, not 20. Priced with the real
counts, plan A does 102,000 rows of work, and plan B would have done 22,000. The chosen plan did 4.6 times the work.
Well, that's the stadium.

SCREEN: Countdown. "est 10" turns red with "actual 1,000"; the error travels up the gold path ("actual 100,000",
"actual 2,000"). The price cards update: "A, as it ran: 100,000 + 2,000 = 102,000" in red, "B: 20,000 + 2,000 =
22,000" in green; "4.6 times the work".

## Scene 6 · Fix the guess · 3:45–4:15 · [LOOP-PAYOFF] [SHOW]

VO: So, was the search broken? No. It found the cheapest plan for the numbers it was given. In PostgreSQL itself, the
same wrong guess picked a loop that looked up the payments a thousand separate times: 103,172 pages touched. Tell it
that the city decides the country and the currency, with CREATE STATISTICS, and it guesses 1,000 shops. The same search
picks plan B, reads the payments once, and touches 6,542 pages, 16 times fewer.

SCREEN: Caption "the search was right; the guess was wrong". "1,000 separate lookups: 103,172 pages". The shops box
turns green, "est 1,000"; B's path lights teal with a tick; "one pass: 6,542 pages, 16 times fewer".

## Scene 7 · Check the guesses first · 4:15–4:45 · [GUARDRAIL] [NAME] [BREAK of the analogy]

VO: It's tempting to force the order yourself. Don't start there. When a plan is slow, check the guesses first. Run
EXPLAIN ANALYZE, which prints each step's guessed and actual rows, read it from the bottom up, and fix the first step
that's off by 10 times or more. Often a plain ANALYZE, which refreshes the statistics, is enough. In one benchmark,
about 1 in 10 queries ran more than 10 times slower on PostgreSQL's own guesses. And here the map app is ahead: it
re-routes you on the way. PostgreSQL never changes a plan once it starts.

SCREEN: Rule captions; a bottom-up arrow beside the lattice landing on the shops box; "about 1 in 10 queries: more than
10 times slower on its own guesses"; "the map re-routes; PostgreSQL never changes a plan once it starts".

## Scene 8 · The moral, and a check · 4:45–5:10 · [MORAL] [PREDICT] [PAUSE]

VO: So the moral of the story: the planner picks the best plan for its guesses. A wrong plan usually means a wrong
guess. One quick check. The shops step says 10 guessed, 1,000 actual. The join above it says 1,000 guessed, 100,000
actual. Which one do you fix? Pause and think. (three seconds) The shops. The join above is only passing the same error
up.

SCREEN: The moral in yellow. The two mismatches as red labels on the lattice; countdown; the shops box pulses, an
arrow from it to the join above labelled "the same error, passed up".

---

### Beat check

- Opens with FAMILIAR + ANALOGY + QUESTION (scene 1), SHRINK + PAIN (scene 2: orders explode).
- ANALOGY + MAP (the bridge) before NAME dynamic programming (scene 3); SHOW (scene 4).
- PREDICT + PAUSE and BREAK (scene 5); LOOP-PAYOFF (scene 6); GUARDRAIL and the analogy's limit (scene 7); MORAL and a
  check with PAUSE (scene 8).
- Light moments: "Forty minutes in traffic" (0:20), "Well, that's the stadium" (3:42), "the map app is ahead" (4:40).

### Accuracy notes for the producer

- The lattice and all its numbers are the lesson's stepper, which runs the lab's dynamic programming with cost = rows
  the joins produce. "Shops with payments: about 1,000" is 10 x 1,000,000 / 10,000.
- 1,023 groups for 10 tables is the lesson's "about 2^n groups"; the narration says "about 1,000".
- The orders counted are left-deep ones (n!); bushy plans add more. Not said.
- "A loop that looked up the payments a thousand separate times" is the Try it's Nested Loop with a Bitmap Heap Scan
  (loops=1000). Buffers 102,339 + 833 = 103,172 against 6,542; times were about equal in that run because every page
  was in memory, so the video compares pages, as the lesson does.
- The benchmark is Leis and colleagues' Join Order Benchmark (2015), unnamed here; "about 1 in 10 ran more than 10
  times slower" is the lesson's figure. GEQO above 12 tables is named only as "up to 12 tables".
- "The fastest way to the bridge" is the analogy for the lesson's "the cheapest plan for a smaller group stays the
  cheapest, whatever is built on top of it".
- PostgreSQL is spoken through a scene SAY rule ("post-gress"), because sfz's "postgres" comes out as "POST-gurz".
- "chargebacks" is spoken through a scene SAY rule ("charge-backs"): the voice put an extra vowel in it
  ("charge-ih-backs"), which Whisper heard as "charge of backs".
