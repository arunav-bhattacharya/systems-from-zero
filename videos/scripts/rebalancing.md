# One new machine, one share: number the lockers once, move them whole

- Slug / scene: `rebalancing`, `videos/scenes/rebalancing.py:Rebalancing`
- Lesson: `shard-03`, section 1, "Fixed partitions: far more partitions than machines, moved whole"
- Audience / level: a complete newcomer. Has seen `hash mod N` once (Splitting data); doesn't know what a
  partition, a node, rebalancing, Kafka, Redis or Notion's shards are.
- Length: about 4:30 (~800 words of narration, plus two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: the moment after the join: four nodes with three partitions each, D's three green, the table updated,
  "pay-7: p9, on D" and "pay-81701: p2, on C".
- The learner's real question: one new machine needs only one share of the data, so why does adding it move almost
  everything, and what design moves only that share?
- Misconception to steelman and break: "one new machine disturbs one machine's worth of payments". Broken by the
  `hash mod 11` count (91,032 of 100,000 move, most between old machines). Second, smaller break: the lockers picture
  itself, where handing over a key is instant but moving a partition is gigabytes of copying.
- Concept chain: `hash mod N` changes answers for most keys → split the map in two: key to partition (fixed), partition
  to node (a table) → a new node takes whole partitions, only the table changes → the number of partitions is chosen
  once, so choose it well (hardest last)
- Analogy family: the lesson's left-luggage office. Numbered lockers (partitions), attendants (nodes), the number
  stamped on a traveller's key (`hash mod P`), the manager's list of who looks after which locker (the table). A new
  attendant is handed whole lockers; nobody gets a new number.
- Open loops: "how many payments move?" planted in scene 1 → answered in scene 2 (91,032) and paid off at full size in
  scene 5 (8,955 with 1,000 fixed partitions); "a new number for a traveller" planted in scene 3 → the prediction in
  scene 4 and the check in scene 8.
- Assumptions: all numbers are the lesson's. Opening and closing demo: 100,000 payments, 10 machines to 11, 91,032
  move (9,150 of them to the new machine), 8,955 with 1,000 fixed partitions, from all 10 old nodes; 3 TB, 2.7 TB,
  270 GB. The stepper: 12 partitions on nodes A, B, C dealt in turn; `pay-7` in p9 on A, `pay-81701` in p2 on C; D
  takes p9 from A, p10 from B, p11 from C; `hash mod N` from 3 to 4 nodes would move three keys in four. Notion: 480
  shards, 32 to 96 machines; 512 on 96 machines gives 6 or 5 each, busiest 13% above average. Redis Cluster 16,384
  slots. The flying dots in scene 2 are a picture, not a count.

## The one picture

Top: a mono rule chip, "partition = hash(key) mod 12". Middle: node boxes (A blue, B teal, C purple, later D green),
each holding its partitions drawn as small lockers with a keyhole, two by two. Below: the table, a strip of twelve
cells, "p0 … p11", each showing its owner's letter in the owner's colour. Under it, the two payments ("pay-7: p9, on
A", "pay-81701: p2, on C"). Captions at the bottom. Yellow marks what's moving, red a cost, green what landed.
The opening hook is a row of ten small machines (then eleven) with the `hash mod 10` rule, which gives way to the
main picture.

## Scene 1 · One more machine · 0:00–0:30 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: The payments company keeps its payments on ten machines. Each payment lives on machine number hash mod 10. Turn
the payment's id into a big random-looking number, its hash, divide by 10, and keep the remainder. The busiest
shopping day of the year is a week away, and an eleventh machine has just arrived. The plan fits on one line: switch
to hash mod 11, and copy every payment whose answer changed. So how many payments move? Hold your guess.

SCREEN: Title card. Ten small machine boxes in a row; the chip "machine = hash mod 10"; a payment chip falls into one
machine. The eleventh machine slides in, green, "new"; the chip becomes "hash mod 11". A yellow "?" above.

## Scene 2 · Nine in ten pack up · 0:30–1:05 · [PAIN] [WISH] [JOKE:amplify]

VO: The new machine needs only its fair share, one payment in eleven. Out of 100,000 payments, that's about 9,100.
Now count what hash mod 11 actually moves. 91,032. Nine payments in ten pack up and leave, and most of them just go
from one old machine to another. It's like hiring one new cashier and making every cashier in the shop swap tills.
On three terabytes of payments, that's 2.7 terabytes of copying, when 270 gigabytes would do. Wouldn't it be nice if
the new machine took its share, and nothing else moved?

SCREEN: "fair share for the new machine: about 9,100" (green). Dots fly between old machines, a few into the new
one; "hash mod 11 moves 91,032 of 100,000" (red). "only 9,150 of them land on the new machine". "3 TB stored: 2.7 TB
copied, when 270 GB would do". Caption: "wish: the new machine takes its share, nothing else moves".

NOTE: The cashier line is the light moment, and it is the waste: moves between two old machines.

## Scene 3 · The left-luggage office · 1:05–1:55 · [ANALOGY] [MAP] [SHRINK]

VO: Picture the left-luggage office at a big station. A thousand numbered lockers, ten attendants, a hundred lockers
each. A traveller's locker number is stamped on their key, and it never changes. When an eleventh attendant starts,
the manager hands her the keys to 90 lockers, about nine from each of the others. No locker moves, and no traveller
gets a new number.

Let's shrink it to twelve lockers and three attendants, and map it. Each locker is a partition: a fixed bucket of
payments. Each attendant is a machine, and from here on we'll call a machine a node. The number on the key is hash mod
12, worked out once and never changed. And the manager's list is a table: which node looks after which partition.

SCREEN: A key with a tag "locker 417" in the centre; captions "1,000 lockers · 10 attendants · 100 each", then "an
11th attendant: 90 lockers, about 9 from each". Then three boxes A, B, C appear; twelve lockers are dealt into them
in turn; the headers become "node A", "node B", "node C"; the rule chip "partition = hash(key) mod 12" appears; the
table strip fills, p0 A, p1 B, p2 C and so on. Each mapping is captioned as it's said.

## Scene 4 · Node D joins · 1:55–3:05 · [PREDICT] [PAUSE] [SHOW] [BREAK]

VO: The payment pay-7 hashes to partition 9, which lives on node A. And pay-81701 is in partition 2, on node C.

Now node D joins. How many partitions should it get? And how many payments get a new partition number? Pause and
guess.

(three seconds)

Three partitions: twelve, split four ways. And not one payment gets a new number, because twelve didn't change. Only
the table is about to change.

They're all tied at four, so A goes first, and hands over its highest partition, p9. A copies p9 to D, and keeps
serving payments from it while it copies. When D has caught up, the table says p9 lives on D. Then B gives p10, and C
gives p11. Every node holds three.

Check both payments. pay-81701 is still in p2, and p2 never left C. pay-7 is still in p9, which now lives on D. It
moved, but only as part of a whole partition. Three partitions of twelve moved: a quarter, D's fair share, and three
nodes shared the sending. Hash mod N, going from three nodes to four, would have moved three payments in four.

SCREEN: pay-7 and pay-81701 notes under the table; p9 and p2 glow. Nodes slide left, D appears. Yellow "?" on D and on
the rule chip; countdown bar. "12 ÷ 4 = 3" in D; the rule chip glows green ("unchanged"). p9 is copied out along a path
above the nodes into D while the original pulses yellow ("A keeps serving p9"); a progress bar fills under the copy;
the table cell p9 flips from A to D; the original dims. p10 and p11 follow faster. Then the pay-7 note becomes "p9, on
D" and "3 of 12 partitions moved, all to D, from 3 senders" (green); "hash mod N, 3 nodes to 4: three keys in four
move" (red).

## Scene 5 · Where the lockers break, and the name · 3:05–3:50 · [BREAK] [NAME] [LOOP-PAYOFF] [JOKE:release]

VO: Here the lockers picture breaks. Handing over a key takes a second. Moving a partition means copying gigabytes
between machines that are busy serving payments, and the copying loads the very nodes it's meant to relieve. The new
attendant isn't handed keys. She's handed the luggage, by colleagues who are still serving the queue.

At full size, a thousand partitions on ten nodes, the eleventh node takes 90, and only 8,955 of the 100,000 payments
move. All of them go to the new node, sent by all ten old ones.

Moving data so every node holds a fair share is called rebalancing. And this design is called fixed partitions: far
more partitions than nodes, chosen once, and moved whole. It's the most common design. Kafka, a program that keeps
logs of messages, splits each log into a fixed number of partitions. Redis Cluster, a fast store that keeps its data
in memory, has 16,384 slots. And Notion, the notes app, runs 480 shards. Going from 32 machines to 96, whole shards
moved, and no workspace changed shard.

SCREEN: A red caption "a key: one second. a partition: gigabytes, copied while serving"; the three senders' boxes
glow red. Then "1,000 partitions, 10 nodes to 11: 8,955 of 100,000 move, all to the new node, from 10 senders"
(green). The names as captions: "rebalancing: moving data so each node holds its fair share", "fixed partitions:
many more partitions than nodes, chosen once, moved whole", then "Kafka: fixed partitions per log", "Redis Cluster:
16,384 slots", "Notion: 480 shards, 32 machines to 96".

## Scene 6 · The catch: P is chosen once · 3:50–4:35 · [GUARDRAIL] [JOKE:is-the-explanation]

VO: The catch is that the number of partitions, call it P, is chosen once. Pick too few, and you hit a wall. With
twelve partitions, a thirteenth node has nothing to hold. It gets a chair and no lockers. Pick too many, and every
partition's fixed cost adds up: its own files, its own line in the table. And changing P later means rehashing the
keys, which is the hash mod N mess all over again.

So pick a P with plenty of divisors. Notion chose 480 for the same reason an hour has 60 minutes. 480 spreads evenly
over 32, 40, 48 or 96 machines. 512 doesn't. On 96 machines, some hold six and some hold five, and the busiest
carries 13% more than the average.

SCREEN: "too few: 12 partitions, 13 nodes, one node holds nothing" (the four nodes' three lockers each glow, a red
"13th node: 0"); "too many: every partition has its own files and its own line in the table" (the table glows red);
the rule chip becomes "mod 13" in red and every table cell's owner becomes "?" for a moment, then back. Then "480 on
96 machines: 5 each" (green) and "512 on 96 machines: 6 or 5 each, the busiest +13%" (red).

## Scene 7 · The moral · 4:35–4:55 · [MORAL] [RECAP] [PRINCIPLE]

VO: So, how much should one new machine disturb? Only its share. Number the lockers once, hand them over whole, and
change only the list. Pick P once, for the size you expect years from now, with plenty of divisors.

SCREEN: D's three partitions glow green, then the table, then the rule chip. Caption "number the lockers once, move
them whole, change only the list" (yellow).

## Scene 8 · A quick check · 4:55–5:15 · [PREDICT] [PAUSE] [LOOP-PAYOFF]

VO: One quick check. A fifth node, E, joins our cluster. Does pay-81701 get a new partition number? Pause and think.

(three seconds)

No. It stays in p2, forever. At most, p2 gets a new node, and only the table changes.

SCREEN: Caption "a fifth node joins: does pay-81701 get a new partition number?"; countdown. Then the pay-81701 note
glows, p2's table cell glows, and the rule chip glows; "p2, forever" (green).

---

### Beat check

- Opens with QUESTION and FAMILIAR (scene 1): the plan the learner would write themselves.
- PAIN and WISH (scene 2) with the count, before any new idea.
- ANALOGY and MAP (scene 3), every part named out loud; SHRINK to 12 partitions.
- PREDICT with PAUSE (scene 4, and the check in scene 8); SHOW right after each.
- BREAK: the wrong model in scene 2 (91,032), and the analogy's limit in scene 5.
- NAME after the first SHOW: node (scene 3, as a plain word), rebalancing and fixed partitions (scene 5).
- GUARDRAIL (scene 6) and MORAL (scene 7) come last. Light moments: the cashiers swapping tills (0:50), the luggage
  carried by busy colleagues (3:20), a chair and no lockers (4:00), the hour's 60 minutes (4:20).

### Accuracy notes for the producer

- The opening and full-size numbers are the lesson's demo (`RebalanceDemo`): 91,032 of 100,000 move under
  `hash mod N`, 9,150 of them to the new node; 8,955 with 1,000 fixed partitions, from 10 senders.
- The stepper's tie-break ("the busiest node gives first; ties go to the first by name; it gives its highest
  partition") is simplified in the narration to "they're all tied, so A goes first, and hands over its highest".
- Copying while serving, then flipping the owner in the table, is the lesson's description; the real hand-off also
  sends the writes that arrived during the copy, which the stepper's "when D has caught up" covers.
- Elasticsearch and OpenSearch, and the cost box ("why not a million partitions?"), are left to the lesson.
  Kafka's key-order break when partitions are added is folded into "the hash mod N mess all over again".
- How a request finds a partition that moved (MOVED and ASK) is the lesson's last section, not this video.
