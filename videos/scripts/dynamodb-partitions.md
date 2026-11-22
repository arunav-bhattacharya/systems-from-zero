# Room in the table, a queue at one window: why DynamoDB refuses a busy key

- Slug / scene: `dynamodb-partitions`, `videos/scenes/dynamodb_partitions.py:DynamoDBPartitions`
- Lesson: `shard-08`, section 1, "Every partition has a ceiling, so partitions split"
- Audience / level: a complete newcomer. Has met items, partition keys and the idea of a partition in section 0;
  doesn't know about ceilings, splits, throttling or throttling reasons.
- Length: about 5 minutes (~820 words of narration, two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: the table may take 40,000 writes a second and uses 6,000, so why are updates to one
  shop's running total refused?
- Misconception to steelman and break: "a table's capacity is one big pool" (broken by the box office's ten windows
  and the one-item ceiling); "lowering capacity takes you back to fewer partitions" (they never merge); "when
  throttled, raise the capacity" (broken by the hot-partition reason).
- Concept chain: a table is partitions, each with a ceiling → partitions split for capacity, size and traffic →
  one item or an in-order key range can't be split → a refused request is a throttle with a reason → read the
  reason before raising capacity; Local never throttles (hardest last)
- Analogy family: the lesson's concert box office. Ten windows by surname range, a hundred people a minute each; a
  tour company's 300 guests under one name queue at one window; a new window can't split one name.
- Open loops: "how can a table with so much room say no?" planted in scene 1 → paid off in scene 6 (one item, one
  ceiling, about 500 refused).
- Assumptions: all numbers are the lesson's (40,000 allowed, 6,000 used, 1,500 updates a second on the shop total,
  about 500 refused; 1,000 write units, 3,000 read units, 10 GB per partition; 3,200 → 4 × 800, 3,600 → 900,
  6,000 → 8 × 750, 5,000 → 8 × 625; 1,000 units and 15 GB → 2 × 500, a range wanting 800; Local: 1 write unit, 1,000
  writes, throttled 0). Meter heights are to scale; the traffic split's heights are illustrative.

## The one picture

A row of partition meters in the middle (blue fill = the share or the load; the red dashed line at the top = the
1,000-write ceiling; red fill = over the ceiling or over the share). First the box office's ten windows stand in the
same row. A table chip top centre. Captions and a counter line at the bottom. Right half in scene 7: the two
throttling reasons.

## Scene 1 · The puzzle · 0:00–0:25 · [QUESTION] [LOOP-PLANT]

VO: Here's a puzzle. A payments table in DynamoDB, a database that Amazon runs for you, may take 40,000 writes a
second. It uses 6,000. Yet one record, the running total for the busiest shop, gets 1,500 updates a second, and about
500 of them are refused. How can a table with so much room say no? Hold that question.

SCREEN: Title card. "table: 40,000 writes a second allowed", "used: 6,000", a gold chip "one shop's running total:
1,500 updates a second", "about 500 a second refused" in red, a "?".

## Scene 2 · The box office · 0:25–1:20 · [FAMILIAR] [ANALOGY] [MAP] [NAME]

VO: Picture a concert hall's box office. Ten windows hand out booked tickets, each for a range of surnames: A to C, D
to F, and so on. Each serves a hundred people a minute, so the office serves a thousand. Tonight a tour company
booked 300 seats under one name, and its guests come one by one. All of them queue at one window, while nine sit
quiet. The thousand a minute was never one big pool. It was ten windows of a hundred.

DynamoDB cuts each table into pieces like those windows, called partitions. It hashes each item's partition key, the
part of the key that says whose item it is, into a big random-looking number, and each partition owns one stretch of
those numbers. The windows are the partitions, a booking name is a partition key, and the office's total is the
table's capacity.

SCREEN: Ten windows "A–C" ... "Y–Z"; caption "each window: 100 a minute; the office: 1,000". A queue of dots under one
window, "300 guests, one name"; the other nine dim. Then the mapping captions.

## Scene 3 · A ceiling on every partition · 1:20–1:50 · [NAME] [SHRINK]

VO: Each partition has a ceiling. It serves at most 1,000 write units and 3,000 read units a second, and holds about
10 GB. A write unit pays for one write a second of up to 1 KB. So why doesn't DynamoDB just add partitions when one
gets busy? It does, for three reasons. Let's take them one at a time.

SCREEN: The windows become four empty meters with the red dashed ceiling "ceiling: 1,000 write units a second";
caption "per partition: 1,000 write units, 3,000 read units, about 10 GB".

## Scene 4 · Reason one: the capacity you ask for · 1:50–2:55 · [SHOW] [PREDICT] [PAUSE] [BREAK] [JOKE:release]

VO: Reason one is the capacity you ask for. On a provisioned table, you set the write units yourself, and each
partition gets an equal share. DynamoDB's design paper gives the example: 3,200 write units need 4 partitions of 800.
Raise the table to 3,600, and each share becomes 900.

Now raise it to 6,000. What happens to the four partitions? Pause and guess.

Each would need 1,500, over the ceiling. So each splits in two: 8 partitions of 750.

Now lower it back to 5,000. Back to four? No. You keep 8, at 625 each. Partitions only ever split. They never merge.
A cut cake doesn't glue itself back together. So lowering the capacity gives you smaller shares, not fewer partitions.

SCREEN: Table chip "provisioned: 3,200 write units"; four meters fill to 800; 900. Chip 6,000; countdown; each
meter fills to 1,500 with red above the ceiling; eight meters of 750. Chip 5,000; eight meters of 625; caption
"partitions only split; they never merge".

## Scene 5 · Reason two: size · 2:55–3:30 · [SHOW] [NAME]

VO: Reason two is size. When a partition nears 10 GB, it splits in two. In DynamoDB's original design, its share of
the units was divided between the halves. A table with 1,000 write units and 15 GB had two partitions of 500. A key
range taking 800 writes a second was refused, while the other half sat idle. The paper calls this throughput
dilution, throughput being the work done per second.

SCREEN: Two meters with a yellow dashed share line at 500. The left fills to 800, red above 500; the right stays
empty, "idle". Caption "throughput dilution (the original design)".

## Scene 6 · Reason three: traffic, and what no split can fix · 3:30–4:25 · [SHOW] [BREAK] [LOOP-PAYOFF]

VO: Reason three is traffic. When a partition stays busy, DynamoDB splits it for consumption. It cuts at a point
chosen from the keys it has seen used, not the middle, so the busy keys land on both sides. That takes minutes.

But two patterns can't be helped. One is a single item that takes all the traffic. The other is a key range written
in order, such as one partition key with a time as its sort key, so every new write lands at the same end. In the
box office, a new window can't split one booking name.

And there's our puzzle. The shop's running total is one item, so it lives in one partition. 1,500 updates a second
against a ceiling of 1,000: about 500 a second are refused, however much room the table has.

SCREEN: One busy meter; a cut off-centre; two meters each carrying part of the load. Then one meter with a gold chip
"one item"; a dashed cut with a red cross. The shop total's meter fills to 1,500, red above the ceiling; "1,500
asked − 1,000 ceiling = about 500 refused".

## Scene 7 · Throttled, and the reason · 4:25–5:20 · [NAME] [GUARDRAIL] [JOKE:is-the-explanation]

VO: Refused has a name: DynamoDB throttles the request. It answers with HTTP 400, the web's code for a request it
won't carry out, and changes nothing. Amazon's library for your code, the AWS SDK, retries a few times, waiting longer
before each try. So first you see slower answers, then an exception.

The exception carries throttling reasons, which name the limit. Table write key range throughput exceeded means a hot
partition. Table write provisioned throughput exceeded means the whole table used up its units. More capacity fixes
the second. It does nothing for the first. Adding windows to the box office doesn't shorten the tour group's queue.
So read the reason before you raise the capacity.

SCREEN: Dots bounce off the hot meter with growing gaps; "HTTP 400: nothing changed". Right: the two reasons in mono
(red, gold) with their meanings and a red cross / green tick for "more capacity".

## Scene 8 · Local never throttles · 5:20–5:50 · [GUARDRAIL] [PREDICT] [PAUSE] [SHOW]

VO: One more trap. DynamoDB Local is a single Java program for testing on your laptop. It has no partitions and
ignores capacity. In the lesson's lab, a table of 1 write unit gets 1,000 writes from eight threads. How many are
throttled? Pause and guess.

Zero. Local can't throttle. So to test how your code handles a throttle, use the lab's model or a real table.

SCREEN: A terminal panel: `provisioned: 1 RCU, 1 WCU`; countdown; `write units consumed: 1,000.0`, `throttled: 0`.

## Scene 9 · The moral, and a check · 5:50–6:20 · [MORAL] [PREDICT] [PAUSE]

VO: So the moral of the story: a table's capacity is a sum of partition ceilings, and one record lives behind one of
them. One quick check. Your exception says table write provisioned throughput exceeded. Will raising the table's
capacity help? Pause and think.

Yes. That reason is the table's own budget, not one hot partition, so more units are the fix. Next, we'll see how
DynamoDB lends a busy partition the table's spare units, and where that help stops.

SCREEN: Moral captions in yellow over the meters; the reasons panel returns, the second reason pulses, a green tick.

---

### Beat check

- QUESTION (1) → FAMILIAR + ANALOGY + MAP (2) → NAME the ceiling (3).
- PREDICT with PAUSE (4, 8, 9); SHOW after each. BREAK: the four partitions over the ceiling and the "back to four"
  idea (4); a split that can't divide one item (6).
- LOOP-PAYOFF of the puzzle (6). GUARDRAIL: read the reason (7), Local never throttles (8). MORAL and check (9).
- Light moments: "ten windows of a hundred" (1:15), the cut cake (2:50), the tour group's queue (5:10).

### Accuracy notes for the producer

- Split examples and throughput dilution are from the 2022 DynamoDB paper as the lesson reports them; dilution is
  the original design. The next section covers adaptive capacity, which lends spare units to a busy partition.
- "About 500 refused" is the lesson's warm-up answer (1,500 against the 1,000 ceiling).
- The traffic split's meter heights carry no numbers; the lesson gives none.
- Local's output is the lesson's Try-it (`throttled: 0`; the rate line depends on the machine and is left out).
- Read units: 3,000 a second per partition for strongly consistent reads of up to 4 KB, or twice as many eventually
  consistent ones; the video mentions only the 3,000.
