# Follow the strings: one step in a table and on a pinboard

- Slug / scene: `graph-hops`, `videos/scenes/graph_hops.py:GraphHops`
- Lesson: `model-08`, section 0, "Every step through a shared phone costs a table two joins"
- Audience / level: a complete newcomer. Can read a little code; knows nothing about indexes, joins or graph databases.
- Length: 4:49 (~720 words of narration, two guesses, silent builds)
- Poster: `POSTER=200` (the walk done: steps 1, 2, 3 counted as 2, 2, 14 paths; every string the walk reached lit)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: a fraud team wants every account linked to a flagged one through shared phones, up to
  three steps out. Why is that awkward for tables, and what does a graph database do differently?
- Misconceptions to steelman and break: (1) "a table with an index on every column answers this as fast as anything,
  each lookup takes microseconds" (true per lookup; but every step is more joins and the rows multiply by about 6);
  (2) "a graph database makes the fan-out go away" (the walk jumps from 2 paths to 14 at step three, through a kiosk)
- Concept chain: links in a table with an index per column → one step is two trips through the table, a self join →
  every step multiplies the rows and the joins → the pinboard: photos and strings, follow them from one photo → Neo4j:
  nodes, relationships, pointer reads, index-free adjacency → the walk pays for paths explored (hardest: predict step
  three) → when to use which, and the cost of pointers
- Analogy family: a detective's pinboard. A photo for each account and each phone or device, a string between each
  account and every identifier it used; one step is a finger on a photo, following its strings. Where it breaks: the
  board has no price for tying strings, but a graph store must link every new relationship into the lists of both its
  nodes, and totals over everything read scattered records.
- Open loops: "let's see what one step really costs" planted in scene 1 → paid off in scenes 2 and 7
- Assumptions: the flagged account A-3101, its links and the walk's counts are the lesson's fraud graph and Try-it output
  (steps 1, 2, 3: 2, 2 and 14 paths; 1, 1 and 6 accounts). The pinboard shows the part of the graph the walk reaches.
  The fan-out of 6 (3 identifiers, 2 accounts each; 6, 216, about 47,000 rows) is the lesson's made-up illustration and
  is labelled so.

## The one picture

Left: the link table `account_identifier`, one row per link, with its two indexes; later the walk's counts (steps,
paths, accounts). Right: the pinboard, a cork-coloured board with account photos (boxes) and identifier pins (pills),
joined by strings. A-3101 is red (flagged). Yellow is a lookup or a string being followed, green an account found.
Bottom: the strip (the step on the left, its count on the right; its frame shows only while it has text) and a
caption line.

## Scene 1 · A flagged account · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: A Monday morning at the payments company. Overnight, one account, A-3101, made a run of odd payments, and the fraud
team, the people who look for cheating, flagged it at 09:12. Their question: which other accounts share a phone or a
laptop with this one, directly or through up to two other accounts? People who cheat together often share phones. Easy,
you'd think. Put the links in a table, index every column, and each lookup takes microseconds. Let's see what one step
really costs.

SCREEN: Title card. A red chip "A-3101 · flagged at 09:12"; the question beneath it; "up to 3 steps".

## Scene 2 · One step in a table · 0:30–1:35 · [FAMILIAR] [NAME] [PAIN] [BREAK] [SHOW]

VO: The table has one row per link: this account used this phone or device. Call either one an identifier. Each column has
an index, a sorted list of its values, like the index at the back of a book. One step crosses the table twice. Look up
A-3101's rows through the account index: device D-77 and phone P-0177. Then look up each identifier's other rows: A-3102,
twice. That's the table joined with itself. Two steps is four trips through the table, three steps is six. The query
grows with every step you allow. So does the work. Say each account has 3 identifiers, and each identifier is shared by 2 accounts. Those are
made-up numbers, to see the shape. Every step fans out by about 6. One step touches 6 rows. Three steps, 216. Six
steps, about 47,000. And the database has to guess the size of each join before it runs, and its guesses get worse with
every join.

SCREEN: The table `account_identifier` (rows from the lesson's fraud graph) with "index: account_id" and "index:
identifier_id". A-3101's two rows glow yellow; then the D-77 and P-0177 rows of A-3102 glow green. On the right, the
query as trips through the table: a small yellow table and a small green one, joined by a gold link ("1 step"); then
rows of four and six small tables ("2 steps", "3 steps"). Then the fan-out: "made-up numbers: every step fans out by
about 6", then 6, 216 and "about 47,000" over "1 step", "3 steps", "6 steps", each number larger than the last.

## Scene 3 · The pinboard · 1:35–2:05 · [ANALOGY] [MAP]

VO: Now store the same links the other way round. Think of a detective's pinboard: a photo for each account and each
phone, and a string between each account and every phone it used. To take one step, put your finger on A-3101's photo.
Follow its strings to its phones. Then follow each phone's strings to the other photos. You never search the board.

SCREEN: The fan-out leaves; the board draws in on the right: photos, pins and strings. A yellow finger dot sits on
A-3101, runs along its strings to D-77 and P-0177, then on to A-3102.

## Scene 4 · Nodes, strings, pointers · 2:05–2:45 · [NAME] [MAP]

VO: That's what a graph database stores. Neo4j is a database program built for graphs. Each photo is a node. Each string
is a relationship. A node's record leads to its relationships, and each relationship records the nodes at both ends. So
following one is a pointer read: the record says where the next record is, and Neo4j goes straight there. Neo4j calls this
index-free adjacency: finding a node's neighbours needs no index. You use an index once, to find the start photo. After
that, the cost of a step doesn't depend on how many accounts exist.

SCREEN: Captions map photo = node, string = relationship. A-3101's record shows two pointer arrows to its relationships;
a relationship shows its two ends. "index-free adjacency: neighbours without an index". The index glows once at the
start.

## Scene 5 · Walk three steps · 2:45–3:50 · [SHOW] [PREDICT] [PAUSE] [BREAK] [JOKE:release]

VO: So let's walk. Step one: two strings out, to D-77 and P-0177, and both lead to A-3102. Two paths, one account. Step
two: from A-3102, phone P-0199 leads to A-3103. Still two paths, because there were two ways to reach A-3102. Now step
three. How many paths, and how many new accounts? Pause and guess. (three seconds) Fourteen paths, and six accounts.
A-3104 and A-3105 through device D-81 and phone P-0181. And four customers through a store kiosk, a shared screen in a
shop, that A-3103 also used. The kiosk didn't find a fraud ring. It found four people who signed in at a shop. So the
fan-out doesn't go away. Both designs pay for every path they explore. What changes is the price of each step, and how
easily you can say "up to three steps".

SCREEN: The left panel becomes the walk's counts (the Try-it output: steps 1, 2, 3; paths 2, 2, 14; accounts 1, 1, 6),
one row per step as the board lights up. Countdown before step three. The kiosk's four strings flash; the four shop
customers turn grey-green.

## Scene 6 · Which one, when · 3:50–4:20 · [GUARDRAIL] [BREAK of the analogy]

VO: So when should you use which? If your questions are one or two steps of a known shape, stay with tables. When they're
paths of unknown length, rings or cycles, a graph store fits. And the strings aren't free. Every new one has to be tied
into the lists of both its ends, and a total over all payments reads records scattered across the board.

SCREEN: Captions for the rule of thumb, then for the costs: a new string drawn while both its ends glow; then many
scattered records flash.

## Scene 7 · The moral, and a check · 4:20–5:00 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, back to the flagged account. In tables, every step through a shared phone cost two lookups and a join. On the
board, it's strings followed from a photo. A graph store answers by walking: find the start node through an index, follow
relationships outward, and pay only for what you touch. In Neo4j's query language, Cypher, you even draw the step: an
account, an arrow to an identifier, and an arrow back from another account. One quick check. Keep the same strings around
A-3101, but put 13 million accounts on the board instead of 13. How many paths does step one find? Pause and think.
(three seconds) Still two. A step costs the strings you follow, not the size of the board.

SCREEN: The moral as captions. The Try-it's one-step Cypher pattern in the left panel, its arrows matched to the strings
around A-3101. Countdown; the board's edge dims with "13 million accounts" while A-3101's two strings stay lit: "step 1:
still 2 paths".

---

### Beat check

- Opens with QUESTION (scene 1); FAMILIAR + PAIN + BREAK (scene 2: the joins and the made-up fan-out).
- ANALOGY + MAP (scene 3) before the names node, relationship, pointer read, index-free adjacency (scene 4).
- PREDICT with PAUSE: step three (scene 5) and the check (scene 7), each followed by SHOW.
- BREAK: the fan-out in a table (scene 2) and on the graph (scene 5, the kiosk); the analogy's cost (scene 6).
- GUARDRAIL (scene 6) and MORAL (scene 7) last. Light moments: "easy, you'd think" (0:25), the kiosk (3:35).

### Accuracy notes for the producer

- The table rows and the board are the lesson's fraud graph (`nosql-11-fraud.cypher`); the board shows only what the
  three-step walk reaches. The Try-it's counts (2, 2, 14 paths; 1, 1, 6 accounts) are its real output.
- The fan-out of 6 and its 6, 216 and about 47,000 rows are the lesson's made-up illustration, labelled on screen.
- The lesson says "two steps is four joins, three steps is six". The video says "four trips through the table" (four
  table references, joined together), so step one's "two lookups and a join" and the counts 4 and 6 agree on screen.
- The check follows the lesson's statement that the cost of a step doesn't depend on how many accounts exist; it wasn't
  run on a larger graph.
- The costs of pointers (linking each new relationship into both nodes' lists, scattered reads for totals) are the
  lesson's aside.
- Left to the lesson: B+tree pages, the planner by name, and the rest of Cypher.
- Ids are spoken through `SAY` rules (A-3101 as "A thirty-one oh one", P-0177 as "P oh one seven seven").
