# A board by the door: how MongoDB finds the shard that holds a payment

- Slug / scene: `mongo-sharding`, `videos/scenes/mongo_sharding.py:MongoSharding`
- Lesson: `shard-07`, section 2, "When one replica set is too small: shards, a map and a router"
- Audience / level: a complete newcomer. Has met the lesson's cloakroom and the replica set (sections 0 and 1); doesn't
  know what a shard, a router, a shard key or a chunk is.
- Length: about 4:30 (~760 words of narration, two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: once the payments are split over several groups of servers, how does the app know
  which group holds the payment it wants?
- Misconception to steelman and break: "put the split rule in the app" (version 1), broken by adding a third shard:
  every copy of the program changes at once and data moves while payments arrive. Second: "mongos always knows
  where to go", broken by a query without the shard key, which asks every shard.
- Concept chain: one replica set has two limits (disk and cache, one primary) → split over several replica sets
  (shards) → the rule as data: a board (config servers) and a porter (mongos) → shard key and chunks, MinKey to
  MaxKey → targeted reads and scatter-gather reads (hardest last)
- Analogy family: the lesson's theatre cloakroom. The attendant with two assistants copying his notebook (a replica
  set), the board by the door with ticket ranges (the chunk map), the porter who reads it (mongos), the porter
  shouting at every counter for a red scarf (scatter-gather).
- Open loops: "which group holds this payment?" planted in scene 1 → answered in scene 6 (the board) and scene 7
  (one shard). "Everything hangs on the key" in scene 9 → bridges to the next section (a key on time).
- Assumptions: all numbers are the lesson's (16 GB server, about 7.5 GB cache, 3 TB; 8,000 writes a second at 70%,
  25,000 needed; accounts A-0000 to A-4999; the lab's 20,000 payments split 10,079 and 9,921 on a hashed `_id`,
  chunks `[MinKey, 0)` on shard2 and `[0, MaxKey)` on shard1; `SINGLE_SHARD` and `SHARD_MERGE`). The cloakroom ticket
  ranges (1 to 300, 301 to 600) are the lesson opening's.

## The one picture

Top left: the payments service (white) and, later, two mongos routers (purple). Top right: the board (gold, then
teal as the config servers) holding the chunk table. Bottom: shards as boxes with P, S, S members (blue shard1,
gold shard2, a grey shard3 only in the break). Bottom right, after the break: the explain() result. Yellow dots are
requests; red is a cost or a broken rule. A query chip top centre; a counter line and captions at the bottom.

## Scene 1 · The question · 0:00–0:20 · [QUESTION] [LOOP-PLANT]

VO: The payments app has grown. Three terabytes of payments, and on the busiest shopping day of the year, 25,000 new
ones a second. One group of servers can't keep up any more, so we'll split the payments over several groups. But
then a new question shows up. When the app wants one payment, how does it know which group has it? Hold that question.

SCREEN: Title card. The app box; one replica set box. Captions "3 TB of payments; busiest day: 25,000 writes a
second", then "which group holds this payment?".

## Scene 2 · One replica set, two limits · 0:20–1:15 · [FAMILIAR] [ANALOGY] [PAIN] [JOKE:amplify]

VO: Start with what we have. MongoDB, a free database program, keeps its copies in a replica set: a group of servers
that hold the same data. One of them, the primary, takes every write, and the others copy it. In the lesson's
cloakroom, one attendant writes every coat in a notebook, and two assistants copy each line, so either can take over
if he faints.

That gives two limits. First, everything must fit on one machine. A 16 GB server gives its cache about 7.5 GB, so
with 3 TB of payments, most reads go to disk, which is far slower than memory.

Second, every write goes through one primary. Say it takes 8,000 payments a second at 70% of its processor. The busy
day needs 25,000. More secondaries don't help, because each one has to replay all 25,000 writes too. Hiring more
assistants to copy the notebook never made the attendant write any faster.

SCREEN: P, S, S inside the box; caption maps attendant = primary, assistants = secondaries. Dots from the app to P,
then P to each S. Stats to the right: "3 TB of payments", "cache: about 7.5 GB of 16 GB", "writes: 8,000 a second
at 70%", "needed: 25,000 a second" in red. A third S fades in and flashes red.

## Scene 3 · Split it · 1:15–1:30 · [WISH] [NAME]

VO: So we split the payments over several replica sets. That's called sharding, and each replica set that holds a
part is a shard: one attendant, with his own assistants copying his notebook.

SCREEN: The box becomes shard1; a copy slides out as shard2. Caption "sharding: split the data; each part is a shard".

## Scene 4 · The rule in the app · 1:30–2:00 · [BREAK] [JOKE:amplify]

VO: The obvious first version puts the rule in the app. Accounts A-0000 to A-4999 go to shard 1, the rest go to
shard 2. That works, until shard 1 fills up. Adding a third shard means changing every copy of the program at the
same moment, and moving payments while new ones keep arriving. It's like reprinting every ticket in the theatre while
the show is on.

SCREEN: Chip "A-0000 to A-4999 → shard1, else shard2" by the app; dots go straight to the shards. shard1's bottom
line turns red "full"; a grey shard3 appears; the chip turns red; caption "change every copy of the app at once;
move data while payments arrive".

## Scene 5 · The board and the porter · 2:00–2:45 · [ANALOGY] [MAP] [NAME]

VO: Here's the better idea. Take the rule out of the code and make it data: a table of key ranges, and the shard that
holds each one. In the cloakroom, that's a board by the door. Tickets 1 to 300, counter one. 301 to 600, counter two.
And a porter stands next to it, reads the board, and sends you to the right counter.

Let's map it. The board is a table that MongoDB keeps on the config servers. It's now the most important data in the
system, so it gets a replica set of its own. The porter is a router called mongos. It keeps a copy of the board in
memory and stores nothing on disk. The app talks only to mongos, so you run several, often one next to each copy of
the app.

SCREEN: shard3 and the chip leave. A gold board top right ("tickets → counter"); a purple "porter" box. Then the
board turns teal, "config servers: a replica set"; the porter becomes "mongos", a second mongos appears, arrows from
the app; a dashed "cached map" line from mongos to the board.

## Scene 6 · Shard key and chunks · 2:45–3:25 · [NAME] [SHRINK] [LOOP-PAYOFF]

VO: Which field does the board go by? You choose it, and it's called the shard key. All its possible values are cut
into ranges called chunks, and each chunk belongs to one shard. The first chunk starts at MinKey, a value below every
other, and the last ends at MaxKey, above every other. So every possible key has exactly one home.

In the lesson's lab, the key is a hash of the payment's id. MongoDB turns each id into a big, random-looking number,
and the chunks own ranges of those numbers. Below zero goes to shard 2. Zero and up goes to shard 1.

For an insert, mongos reads the key, finds the chunk that holds it, and sends the insert to that shard's primary.

SCREEN: Board rows become "hash(_id) range → shard": `[MinKey, 0)` shard2, `[0, MaxKey)` shard1. Each shard's bottom
line shows its chunk. A dot from the app to mongos; a row pulses; the dot runs to shard1's P.

## Scene 7 · Predict, then route · 3:25–4:25 · [PREDICT] [PAUSE] [SHOW] [NAME]

VO: Now we insert 20,000 payments. How do they split between the two shards? Pause and guess.

10,079 on shard 1 and 9,921 on shard 2. Almost half and half, and no data had to move.

Next, look up one payment by its id. The filter gives the shard key, so mongos hashes the id, reads the board, and
asks only one shard. explain, which reports how a query ran, says single shard. That's a targeted query.

Now ask for one shop's failed payments. That filter has no shard key. Which shards does mongos ask? Pause and guess.

Every one. Each shard runs the query, and mongos merges the answers. explain says shard merge. That's called a
scatter-gather read.

SCREEN: Countdown. A stream of dots splits between the shards; "10,079 payments" and "9,921 payments". Chip
`{ _id: "pay-101723" }`; a dot to mongos, a row pulses, one dot to shard2 and back; "explain(): SINGLE_SHARD".
Chip `{ merchantId: "M-0042", status: "FAILED" }`; countdown; dots to both shards and back; "SHARD_MERGE",
caption "scatter-gather: ask every shard, merge the answers".

## Scene 8 · What scatter-gather costs · 4:25–4:55 · [GUARDRAIL] [JOKE:is-the-explanation]

VO: Why can't mongos do better? Each shard indexes only its own payments, so nothing tells mongos where that shop's
payments sit. A scatter-gather read is as slow as the slowest shard, and every shard pays for it. It's the porter
shouting at every counter, has anyone seen a red scarf? Every attendant stops what they're doing to look. And one
more limit: if the config servers can't pick a primary, the board can't change. Reads and writes go on, but no data
moves.

SCREEN: Both shards flash red; caption "as slow as the slowest shard; every shard pays". Then the board pulses;
caption "no config primary: reads and writes go on, no data moves".

## Scene 9 · The moral, and a check · 4:55–5:30 · [MORAL] [PREDICT] [PAUSE] [RECAP]

VO: So the moral of the story: shards hold the payments, the config servers hold the board, and mongos reads the board
for every request. Give it the shard key, and it goes to one counter. Leave it out, and it asks them all. One quick
check. Support looks up a payment by its id and its status. Which shards does mongos ask? Pause and think.

Just one. The id is the shard key, so mongos can hash it and go straight there. The status only narrows the answer.
Everything hangs on that key. Next, we'll see what happens when the key is the time a payment was made.

SCREEN: Moral captions in yellow. Chip `{ _id: "pay-101723", status: "FAILED" }`; countdown; one dot to shard2;
"SINGLE_SHARD". Last caption "with the shard key: one shard; without it: every shard".

---

### Beat check

- Opens with QUESTION (scene 1); FAMILIAR and the lesson's ANALOGY (scene 2) before any new term.
- PAIN (scene 2), WISH (scene 3), BREAK of the obvious fix (scene 4).
- ANALOGY + MAP said out loud (scene 5); NAME after each picture: shard (3), config servers and mongos (5), shard key
  and chunks (6), targeted and scatter-gather (7).
- PREDICT with PAUSE three times (scenes 7, 7, 9); SHOW right after each.
- GUARDRAIL (scene 8), MORAL and check (scene 9). Light moments: the assistants (1:10), reprinting tickets (1:55),
  the red scarf (4:45).

### Accuracy notes for the producer

- The lab runs one member per replica set to fit on a laptop; the picture draws P, S, S as the lesson's figure does
  (three members for real use).
- The 20,000-payment split, the chunk bounds and both explain() stages are the lesson's Try-it output (MongoDB 9.0;
  a hashed key on an empty collection starts with one chunk per shard in 8.0 and later).
- "No data had to move": the lesson's words; the chunks were cut at 0 before any insert.
- The config-servers-without-a-primary rule is the lesson's: reads and writes go on, but no data moves.
- The lesson says the lookup of `pay-101723` is `SINGLE_SHARD` but not which shard; the picture sends it to shard2
  for illustration.
- The query by id and status is targeted because the filter has equality on the hashed shard key.
