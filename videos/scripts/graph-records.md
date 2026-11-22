# A thousand times bigger, no slower: how Neo4j follows a link by multiplying

- Slug / scene: `graph-records`, `videos/scenes/graph_records.py:GraphRecords`
- Lesson: `store-13`, section 0, "Fixed-size records: how Neo4j follows a link by multiplying"
- Audience / level: a complete newcomer. Knows what a byte and a file are; doesn't know what a graph, a node, an
  index or a pointer is.
- Length: 5:21 (~770 words at Kokoro's ~165 words a minute, plus two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=205`, the end of the walk (both files with the five records read, the graph with A-3101's four relationships lit,
  "5 record reads for 4 relationships")
- The learner's real question: the fraud team's map will be a thousand times bigger next year. Will the same question
  take a thousand times longer?
- Misconception to steelman and break: "every lookup grows with the data, so a bigger graph means slower hops". True
  for a link table searched through an index (3 levels at 100,000 rows, 4 at 10 million); broken by the fixed-size
  record walk, whose cost depends only on the node's own number of relationships.
- Concept chain: a graph of nodes and relationships; a walk is hops → a link table makes each hop a search that grows
  with the graph → fixed-size records turn finding a record into a multiplication → pointers chain a node's
  relationships, newest first, doubly linked, one chain per end → where the lockers break, and why only fixed sizes
  allow it (hardest last)
- Analogy family: the lesson's wall of station lockers, all the same width and numbered from 0, where each locker
  holds a note naming the next ("open 28", "open 26").
- Open loops: "a thousand times longer?" planted in scene 2 → answered in scene 9; "what takes time is the read"
  planted in scene 7 → the next section.
- Assumptions: every id, byte offset and record size is the lesson's stepper and Try it, from the lab's real files:
  node 2 (A-3101) at byte 30, first relationship 28, first property 10; relationships 28 (A-3104 to A-3101, next 26),
  26 (A-3101 to A-3103, next 5, previous 28), 5 (A-3101 uses P-0177, next 4; P-0177's chain goes on to 7, A-3102),
  4 (A-3101 uses D-77, next minus one); P-0177 is node 24 at byte 360; 15, 34 and 41 bytes per record; 13 accounts,
  9 devices, 6 phones; 3 levels at 100,000 rows, 4 at 10 million. Relationship 7 at byte 238 (the check) is in the
  stepper. Where the graph's circles sit is made up for the picture.

## The one picture

Right: the graph (A-3101 in the middle, teal; its neighbours A-3104 and A-3103 above, phone P-0177 and device D-77
below, A-3102 beside the phone), each edge tagged with its relationship id. Left: the two files as rows of numbered
cells (node file in blue, "node N at byte N x 15"; relationship file in gold, "rel N at byte N x 34"). Under them: the
record being read. Yellow marks the record being read, green records already read, red the link table's search.

## Scene 1 · The lockers · 0:00–0:25 · [FAMILIAR] [ANALOGY]

VO: Picture a wall of lockers at a train station, all the same width, numbered from 0. Locker 2 holds a note from a
friend: open 28. Locker 28 says: open 26. You never need a map. Every locker is the same width, so you can count your
way to any one of them.

SCREEN: Title card. A row of lockers 0, 1, 2, 3, ..., 26, 27, 28. A yellow note "open 28" on locker 2; a dot hops to
28, which holds "open 26"; the dot hops to 26. Caption "same width, numbered from 0: count your way to any locker".

## Scene 2 · The question · 0:25–0:55 · [QUESTION] [LOOP-PLANT]

VO: Now picture a payments company's fraud team. Their map shows who is linked to whom: accounts, the phones and
devices they log in from, and the money they send each other. It finds the close links of a suspicious account in a
millisecond. Next year the map will be a thousand times bigger. Will the same question take a thousand times longer?
Most people guess yes. Hold that guess.

SCREEN: The lockers leave. The graph draws in on the right: A-3101 in the middle, links to A-3104, A-3103, P-0177,
D-77, and A-3102 by the phone. Caption "a thousand times bigger: a thousand times longer?".

## Scene 3 · Nodes, relationships, hops · 0:55–1:25 · [NAME] [SHRINK]

VO: A map like this is called a graph. Each thing is a node: 13 accounts, 9 devices and 6 phone numbers. Each link
is a relationship, with a type. USES, when an account logs in from a phone or a device. TRANSFERRED_TO, when one
account sends money to another. The fraud team's question is a walk: start at account A-3101, follow its
relationships to its neighbours, then theirs. Each step along one relationship is a hop.

SCREEN: The circles glow as "node" is said; the edges glow and get their type labels; a yellow dot runs out from
A-3101 along one edge and on: "a hop: one step along one relationship".

## Scene 4 · The link table · 1:25–2:05 · [FAMILIAR] [PAIN] [WISH]

VO: The obvious way to store this is a table of links, one row per relationship, with the ids of its two ends. To
find A-3101's links, the database searches that table with an index: a sorted tree of pages, walked from the top
down, one page per level. At 100,000 rows the tree is 3 levels deep. At 10 million, 4. So every hop costs a search,
and the search grows, slowly, with the whole graph. What we'd like is the lockers: go straight to the next link,
without searching.

SCREEN: Left: a "links (from, to)" table chip and a small tree (root, two inner pages, four leaves). A red dot walks
down three levels: "3 levels at 100,000 rows"; a fourth level fades in: "4 at 10 million". Caption "every hop: a
search that grows with the whole graph", then "wanted: the lockers, no searching".

## Scene 5 · Fixed-size records · 2:05–2:45 · [ANALOGY] [MAP]

VO: Neo4j, a database program built to store graphs, does exactly that. Every record in a file is the same size,
and has a number, its id. A node record is 15 bytes, so node N starts at byte N times 15. A relationship record is
34 bytes, so relationship N starts at byte N times 34. Finding a record is arithmetic. Let's map it: the files are
the wall of lockers, a record's id is the locker's number, and the pointer inside a record is the note.

SCREEN: The tree leaves. The node file appears (node 0 byte 0, node 1 byte 15, node 2 byte 30, node 3 byte 45, ...,
node 24 byte 360), then the relationship file (rel 4 byte 136, rel 5 byte 170, rel 7 byte 238, rel 26 byte 884,
rel 28 byte 952, ...). Captions map: "the file = the wall of lockers", "the id = the locker number", "a pointer = the
note".

## Scene 6 · Predict, then walk · 2:45–3:40 · [PREDICT] [PAUSE] [SHOW]

VO: A-3101 is node 2. How many records must Neo4j read to find all of its relationships? Pause and guess.

(three seconds)

Start at byte 2 times 15: 30. The node record says: first relationship, 28. Byte 28 times 34, 952: A-3104 sent money
to A-3101, and its note for A-3101 says next, 26. Byte 884: A-3101 sent money to A-3103. Next, 5. Byte 170: A-3101
uses the phone P-0177. Next, 4. Byte 136: A-3101 uses the device D-77, and its next says minus one: the end. Five
reads, four relationships, and nothing was searched. The count depends on how many links A-3101 has, and on nothing
else.

SCREEN: Countdown. Node 2 turns yellow; the panel "node 2 at byte 2 x 15 = 30: in use, first relationship 28, first
property 10, label Account". A dot runs to rel 28; the panel "rel 28 at byte 28 x 34 = 952: A-3104 TRANSFERRED_TO
A-3101; for A-3101, next 26"; in the graph edge 28 lights. The same for 26, 5 and 4 (the panel ends "next: -1, the end
of the chain"). Read records turn green. Counter "record reads: 1 ... 5". Caption "5 record reads for 4
relationships".

## Scene 7 · Two chains per relationship · 3:40–4:15 · [SHOW] [NAME]

VO: Notice the order: newest first. Each new relationship goes in at the front of its chain, like a new note on top.
And each one points back as well as forward, so the chain is doubly linked. A relationship belongs to two chains, one
for each end. Relationship 5 also carries on along P-0177's chain, to relationship 7: A-3102 uses the same phone.
Crossing to a neighbour is the same move: P-0177 is node 24, at byte 360. One multiplication, one read. Neo4j calls
this index-free adjacency: finding a node's neighbours without an index.

SCREEN: Captions "newest first", "each record points forward and back: a doubly linked chain". A back arrow from 26
to 28. Edge 5 glows; a dot runs on to rel 7; edge 7 (A-3102 to P-0177) lights. Node 24 lights: "node 24 at byte 24 x
15 = 360". Caption "index-free adjacency: neighbours without an index".

## Scene 8 · Where the lockers stop, and the price · 4:15–4:55 · [BREAK of the analogy] [JOKE:release] [GUARDRAIL]

VO: Here's where the lockers stop working. Walking to locker 30,000 takes longer than walking to locker 3. But 30,000
times 34 is no slower to work out than 3 times 34. The lockers give you tired legs. The multiplication doesn't. What
takes time is reading the record, and that's the next section. And why doesn't every database do this? It only works
when every record is the same size. A shop's name may be 3 letters or 300. In Neo4j, a long string spills into more
records and costs more reads. And an id says nothing about what's inside: to find the account called A-3101 in the
first place, Neo4j still searches a tree, once, at the start of the walk.

SCREEN: "30,000 x 34 = 1,020,000: no slower than 3 x 34 = 102". Caption "what takes time: reading the record (next)".
Then "fixed sizes only: a long string spills into more records"; the tree comes back small beside A-3101 with one red
search: "finding A-3101 by name: one search, at the start".

## Scene 9 · The moral, and a check · 4:55–5:25 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, a thousand times bigger, a thousand times slower? Not for the hops. Record N lives at byte N times its size.
Find the first node once, then multiply. One quick check. Where does relationship 7 start? Pause and think.

(three seconds)

7 times 34: byte 238. No search, at any size.

SCREEN: The moral in yellow; the five read records pulse. The check: "rel 7: which byte?"; countdown; the rel 7 cell
glows "byte 238", "7 x 34 = 238". Last caption "record N lives at byte N x size: find the first node once, then
multiply".

---

### Beat check

- FAMILIAR + ANALOGY first (scene 1, the lockers), then the QUESTION (scene 2).
- NAME graph, node, relationship and hop after the picture (scene 3). PAIN and WISH (scene 4, the link table).
- MAP said out loud (scene 5). PREDICT with PAUSE, then SHOW (scene 6). NAME index-free adjacency after the walk
  (scene 7).
- BREAK of the analogy (scene 8, tired legs) and GUARDRAIL (fixed sizes only; one search at the start).
- MORAL, LOOP-PAYOFF and the check (scene 9). Light moments: "most people guess yes" (0:50), "tired legs" (4:30).

### Accuracy notes for the producer

- Byte offsets assume the record's position in the file is id x size, which is what the lab's dump shows (node 2 at
  byte 30, relationship 28 at 952). The `aligned` format leaves the end of each 8 KB page empty, so for large ids the
  real offset adds a page skip; the lesson mentions it and the video leaves it out.
- The walk follows the lab's real chain for A-3101 (28, 26, 5, 4). Relationship 28's prev field holds the degree (4)
  because it heads the chain; the video doesn't say this.
- "Newest first" and "a new relationship goes in at the front" are the lesson's statements.
- "3 levels at 100,000 rows, 4 at 10 million" is the lesson's link-table figure.
- The memory-versus-disk cost of a read (100 ns against 100 µs) is the next section.
- Property records (41 bytes) and labels are left to the lesson.
