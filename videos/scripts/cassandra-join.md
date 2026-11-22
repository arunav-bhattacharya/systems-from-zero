# A new node joins, and nobody shreds: bootstrap, streaming and cleanup

- Slug / scene: `cassandra-join`, `videos/scenes/cassandra_join.py:CassandraJoin`
- Lesson: `shard-06`, section 2, "Adding and removing a node: which data moves, and from where"
- Audience / level: a complete newcomer who has met the token ring and gossip (Inside a Cassandra cluster); doesn't
  know bootstrap, streaming, `UJ`/`UN`, replicas being replaced, or cleanup.
- Length: about 4:45 (~820 words of narration, plus two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: just after cass4 shows `UN`: four disks, the three old ones still full at 1.16 MiB, cass4 holding its share,
  "owns 73.2%" and "owns about 75%" under the old ones, "data on 4 disks, only 3 copies count".
- The learner's real question: when a new node joins, what actually moves, from where, and what is left behind?
- Misconception to steelman and break: (1) "any copy of a range will do as a source", broken by a write that only two
  of three copies hold; (2) "the database tidies up after itself, the join ends at NORMAL", broken by the old nodes'
  Load staying at 1.16 MiB until `nodetool cleanup`.
- Concept chain: three nodes, three copies → cass4 learns the map and picks 16 tokens (BOOT, `UJ`), gets new writes
  during the copy → streams each range from the replica it replaces → `UN`, but the old copies stay → cleanup deletes
  exactly what was streamed (hardest last) → guardrails: one join at a time, cleanup after the last join
- Analogy family: the lesson's office of clerks with full copies of the account files. A fourth clerk takes over a
  share of the alphabet and copies those files from the colleagues handing them over; nobody tells the old clerks to
  shred, so the cabinets run out of space.
- Open loops: "the join ends at NORMAL, which sounds like the end" planted in scene 1 → broken in scene 5; "which
  colleague hands over which files?" planted in scene 3 → scene 4.
- Assumptions: all numbers are the lesson's lab: 50,000 ledger entries, 1.16 MiB per node, 48 tokens, 16 new tokens,
  `ring_delay` 30 seconds, 47 ranges (16 from cass1, 16 from cass2, 15 from cass3, 276, 300 and 280 KiB), 73.2% and
  about 75% owned, cleanup on cass1 from 5,000 partitions to 3,729, 90 seconds for the join. Token positions on the
  ring are drawn at random. The write in scene 4 (confirmed by two of three copies) is the lesson's reason, told as one
  example.

## The one picture

Left: the token ring, 48 ticks in the three old nodes' colours; cass4's 16 green ticks are added. Right: four node
boxes in a row (cass1 blue, cass2 teal, cass3 purple, cass4 green), each with its status chip (`UN`, `UJ`), a disk
filled to its Load, and an "owns" line. Streams are dots running along arcs above the boxes into cass4. A line under
the boxes for counts; captions at the bottom. Red marks a cost or a risk, green what's done.

## Scene 1 · The office that ran out of cabinets · 0:00–0:45 · [QUESTION] [ANALOGY] [LOOP-PLANT]

VO: Picture an office with three clerks, each with a full copy of the account files. For the busy season, a fourth
clerk is hired. She takes over a share of the alphabet, and copies those files from the colleagues handing them over.
Soon the office runs out of cabinet space. Nobody told the old clerks to shred the files they gave away.

Cassandra, the database where no machine is in charge, does the same. When a new node joins, the old ones keep every
row they handed over. And the join ends with a log line saying the new node is NORMAL, which sounds like the end. So
what actually moves, from where, and what's left behind?

SCREEN: Title card. Three node boxes with full disks; captions carry the office story; a fourth box arrives; its disk
fills from the others; the old disks stay full; a red "cabinets full". A log chip "cass4: NORMAL" with a "?" beside it.

## Scene 2 · Three nodes, three copies · 0:45–1:10 · [FAMILIAR] [SHRINK]

VO: Here's the lab cluster. Three nodes, and three copies of every row, so each node holds all of it: 50,000 ledger
entries, 1.16 megabytes on each disk. Each node has 16 tokens, its places on the ring, and a range is the stretch of
ring between two tokens. Every node owns all of it: a hundred percent.

SCREEN: The ring with 48 ticks; boxes show `UN`, a full disk "1.16 MiB" and "owns 100%". Captions "token: a node's
place on the ring", "range: the stretch between two tokens".

## Scene 3 · cass4 gets ready · 1:10–2:00 · [SHOW] [NAME]

VO: cass4 starts with the same cluster name, cass1 as its seed, empty data folders, and its own address not in the
seed list. That last part means it will bootstrap: copy its share of the data on its first start.

It asks the seed for the map, and learns all 48 tokens. It picks 16 tokens of its own and announces them by gossip.
Everyone now shows it as UJ: up, and joining. From this moment, every new write for the ranges it's about to own
gets a copy sent to cass4 too, so nothing written during the copy is missed. Then it waits 30 seconds, so the whole
cluster has heard.

SCREEN: A dashed cass4 box fills in; "seed: cass1"; an arrow from cass1 to cass4 carries "map: 48 tokens". Sixteen
green ticks appear on the ring, cutting slices off existing ranges. cass4's chip "UJ" (yellow). A new-write dot goes
to cass1 and a copy branches to cass4. A 30-second ring delay bar empties.

## Scene 4 · From the replica it replaces · 2:00–3:05 · [PREDICT] [PAUSE] [BREAK] [SHOW]

VO: Now the copy. cass4 takes over 47 ranges. For each one, three nodes have a copy. Which one should it copy from?
Does any copy do? Pause and guess.

(three seconds)

Cassandra insists on one: the replica it replaces, the node that held that range before and won't afterwards. Here's
why. Say a write was confirmed by cass1 and cass2 only: two of three, a majority, so the app was told it's safe. cass4
is taking cass1's place for that range. If it copied from cass3, which missed the write, only cass2 would still have
it. A later read that asks cass3 and cass4 would miss a write the app was promised.

So it copies 16 ranges from cass1, 16 from cass2 and 15 from cass3, about 280 kilobytes from each, all at the same time.
This is called streaming.

SCREEN: "?" over the three old boxes; countdown. Then the example: a gold write chip lands on cass1 and cass2, cass3
shows a grey gap; a dashed red arrow cass3 → cass4 with "only cass2 left"; crossed out. Then three arcs stream dots
into cass4; counts "16 from cass1 · 16 from cass2 · 15 from cass3 (about 280 KiB each)"; cass4's disk fills.

## Scene 5 · NORMAL is not the end · 3:05–3:45 · [BREAK] [LOOP-PAYOFF] [JOKE:release]

VO: cass4 switches to NORMAL, and shows UN. It owns 73.2 percent of the data, and the old nodes about 75 percent each.
But look at their disks. Still 1.16 megabytes. Cassandra never deletes data just because a node stopped owning it. So
three quarters of the rows now sit on four disks, and only three of those copies count. The office's cabinets, exactly.

SCREEN: cass4's chip turns `UN` (green), "owns 73.2%"; the old boxes' "owns" become "about 75%"; their disks pulse
red, still full. Caption "data on 4 disks; only 3 copies count".

## Scene 6 · Cleanup, and the guardrails · 3:45–4:35 · [NAME] [GUARDRAIL]

VO: The shredding is one command, nodetool cleanup. On each old node, it rewrites its files without the ranges it gave
away. cass1 went from 5,000 partitions to 3,729. What each node streamed to cass4 is exactly what its cleanup deleted.
Here the office picture breaks: a clerk would notice the full cabinet. A node never does.

A few rules. Run cleanup after the last new node has joined, on one old node at a time, because rewriting files costs
disk work. Join one node at a time, and wait for UN, because two joins at once would each plan against a ring that's
about to change. And expect hours, not seconds: the lab join took 90 seconds, a real node takes hours. Removing a node
is a join in reverse: it streams its ranges to the new owners, then leaves.

SCREEN: "nodetool cleanup" chip; the old disks shrink one at a time (cass1, then cass2, then cass3) to about three
quarters; "cass1: 5,000 partitions → 3,729". Captions for each rule. Then dots stream back out of cass4 to the three on
"in reverse", and back.

## Scene 7 · The moral, and a check · 4:35–5:05 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So a join is not one step. Learn the map, pick tokens, take new writes, copy each range from the node it replaces,
and only then switch to NORMAL. And the old copies stay until someone runs cleanup. Nothing tidies itself.

One quick check. Next week you add cass5. When do you run cleanup, and on which nodes? Pause and think.

(three seconds)

After cass5 shows UN, on every old node, one at a time.

SCREEN: The steps light up in order as a short list on the right of the ring. Caption "nothing tidies itself: run
cleanup" (yellow). Then the check caption; countdown; "after cass5 is UN: every old node, one at a time" (green).

---

### Beat check

- QUESTION with ANALOGY (scene 1), FAMILIAR and SHRINK (scene 2).
- SHOW and NAME (scene 3): bootstrap, `UJ`.
- PREDICT with PAUSE (scene 4, and the check), BREAK of "any copy will do" (scene 4) and of "NORMAL is the end"
  (scene 5).
- NAME after SHOW: streaming (scene 4), cleanup (scene 6).
- GUARDRAIL (scene 6) and MORAL (scene 7) last. Light moments: the cabinets (0:30, called back at 3:40), the clerk who
  would notice (4:00).

### Accuracy notes for the producer

- Sizes are KiB and MiB in the lab; the narration says kilobytes and megabytes.
- The write in scene 4 is one example of the lesson's reason ("two majorities would no longer be sure to share a
  node"); `cassandra.consistent.rangemovement` is true by default.
- The ring's tick positions are random; the lab's token allocator chooses tokens to even out the load.
- Cassandra 6.0's Transactional Cluster Metadata (no 30-second sleep) and `removenode` are left to the lesson.
- Decommission's numbers (7 SSTables to each node) are left to the lesson.
