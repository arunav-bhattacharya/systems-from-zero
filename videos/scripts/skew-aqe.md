# One trolley holds up the shop: skew, AQE's split and salting

- Slug / scene: `skew-aqe`, `videos/scenes/skew_aqe.py:SkewAqe`
- Lesson: `batch-08`, section 2, "When one key is too big: skew, AQE's split and salting"
- Audience / level: a complete newcomer who has seen the shuffle and the sort-merge join video, nothing more.
- Length: about 4.5 min (~760 words)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: the salted bar chart (shop 7 spread over several tasks, the busiest at 125,793)
- The learner's real question: one task is eight times slower than the rest; why don't more partitions fix it?
- Misconception to steelman and break: "more partitions spread the work" (more tills). Broken: shop 7 is one key, so
  it lands in one partition out of 16 or out of 2,000. Also the backup copy of the slow task, which reads the same
  partition.
- Concept chain: hash partitioning sends a key to one task → one huge key makes one task long, and a stage waits for
  its slowest task (skew) → more partitions can't split a key → AQE splits the hot partition along block edges →
  salting splits the key itself → salt from the data (hardest last)
- Analogy family: the lesson's supermarket on a Saturday: 16 tills, one restaurant's trolley, the trolley packed in
  four bags (AQE can only hand out whole bags), the trolley unpacked over 8 tills (salting)
- Open loops: "open more tills?" planted in scene 1 → broken in scene 4; the four bags in scene 5 → the 4 pieces
- Assumptions: numbers are the lesson's demo output (median 43,593; busiest 346,023; AQE 19 tasks, busiest 86,635;
  salted busiest 125,793). The heights of the other bars and where the 8 salts land are hand-picked to match those
  numbers (see the accuracy notes). "Four bags" is an invented extension of the lesson's trolley.

## The one picture

A bar chart of the join tasks (left two thirds), one bar per task, grey for rows from ordinary shops, red for shop 7.
A dashed median line and a red "the stage ends here" line. Notes on the right. Above the chart: the payments (white)
and the shops (blue). The same bars are first the tills' queues (gold), then the tasks.

## Scene 1 · Saturday morning · [QUESTION] [ANALOGY] [LOOP-PLANT]

VO: Picture a supermarket on a Saturday morning, with 16 tills open. Fifteen queues move quickly. At the last till,
one customer is buying a restaurant's shopping for the week, and everyone behind them waits. One till got the work of
eight. The obvious fix is to open more tills. Hold that thought.

SCREEN: 16 gold bars ("16 tills: how much shopping each one scans"), one eight times taller; caption "open more tills?".

## Scene 2 · The join · [FAMILIAR] [MAP]

VO: Spark, the program that spreads a big job over many computers, meets the same thing. Our million payments are
joined with the shops in a sort-merge join, into 16 partitions. Each partition is one task, on one processor core.
Spark picks each row's partition from its shop number, so every payment of one shop goes to the same task. Now, shop 7
is a marketplace, one website through which thousands of small sellers take payments. It has 30 percent of all the
payments. The tills are the tasks, and shop 7 is the restaurant's trolley.

SCREEN: The bars go; the payments and shops boxes; dots flow into 16 slots; then a stream of red dots into one slot.

## Scene 3 · Predict, then count · [PREDICT] [PAUSE] [SHOW] [NAME]

VO: The median task fetches 43,593 rows. How many does shop 7's task fetch? Pause and guess. (three seconds) 346,023.
Eight times as many. And a stage ends when its slowest task ends. So fifteen cores finish early and wait for one. This
is skew: a few keys with far more rows than the rest. The busy key is called a hot key. Spark's web page for a running
job gives it away: the longest task runs far longer than the median.

SCREEN: Grey bars grow, the median line, a countdown, then the red bar and "346,023"; the "stage ends here" line;
dim idle space above every other bar; "skew" and "hot key" notes.

## Scene 4 · More tills · [BREAK] [LOOP-PAYOFF] [JOKE:is-the-explanation]

VO: So, open more tills? Shop 7 is one key, and one key lands in one partition, out of 16 or out of 2,000. More
tills, same trolley. A backup copy of the slow task doesn't help either. It reads the same hot partition, so it's just
as slow. Two cashiers, still one trolley. A groupBy mostly survives skew, because each task adds up its own rows
before the shuffle. A join can't add anything up early. Every payment must meet its shop's row. So the fix has to
split the key itself.

SCREEN: Notes "16 or 2,000 partitions: shop 7 is still one key", "a backup task reads the same partition"; caption
"more tills, same trolley"; then "the fix: split the key".

## Scene 5 · AQE's skew join · [SHOW] [NAME] [GUARDRAIL]

VO: The first fix is built in. AQE, short for adaptive query execution, is the part of Spark that changes the plan
once a shuffle shows the real sizes. It calls a partition skewed when it's more than 5 times the median and also
bigger than 256 MB. Then it cuts that partition into pieces and runs each piece as its own task, with a copy of shop
7's row. But it can only cut along the blocks the map tasks wrote. Picture the trolley packed in four bags: the
manager can send a whole bag to another till, but won't unpack one. Our payments came from 4 map tasks, so the hot
partition becomes at most 4 pieces. In the demo, with the thresholds scaled down, 16 tasks became 19, and the busiest
fetched 86,635 rows: a quarter of before. With the default settings, nothing happened, because the demo's hot
partition is only a few megabytes.

SCREEN: Caption "AQE: skewed = over 5 × median and over 256 MB"; the red bar splits into four bars; 19 bars; "busiest:
86,635"; the plan line `SortMergeJoin(skew=true)`; note "default thresholds: no change (a few MB)".

## Scene 6 · Salting · [SHOW] [PREDICT]

VO: The second fix is by hand, and it's called salting. On the payments side, add a salt: a number from 0 to 7 worked
out from the data, here the payment number's remainder after dividing by 8. On the shops side, copy each shop row 8
times, once per salt. Then join on the shop and the salt together. Now shop 7 is 8 keys, and they hash to different
tasks, like one trolley unpacked over 8 tills. The busiest task drops to 125,793. Why not an eighth? 8 salts in 16
partitions don't land on 8 different ones. A few share. The price is 8 copies of the small side and a few lines of
code.

SCREEN: Back to 16 bars. The Kotlin line `payments.withColumn("salt", pmod(col("payment_id"), lit(8)))`; the shops
box "× 8 copies"; the red bar splits into eight slices of 37,500 that fly to their partitions; two partitions get two
slices; "busiest: 125,793".

## Scene 7 · The guardrail · [GUARDRAIL] [JOKE:soften]

VO: One rule here matters more than the rest. Salt from the data, never from a random number. When a task fails,
Spark runs it again, and the new attempt must send every row where the first one did. Roll dice instead, and rows get
lost or counted twice. And before either fix, ask whether the shops fit in a broadcast. Then the payments never move,
and no partition can be hot.

SCREEN: Caption "salt from the data, never from a random number"; a retried slice going to a different partition in
red with "lost" and "counted twice"; "first: can the small side be broadcast?".

## Scene 8 · Moral and check · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So the moral of the story. A stage is as slow as its busiest task, and one hot key makes one busy task. More
partitions only open more tills. Split the key: let AQE cut the partition, or salt it by hand. One quick check. Shop 7
grows to 60 percent of the payments, and you double the partitions to 32. Does the hot task get much smaller? Pause
and think. (three seconds) No. Shop 7 is still one key in one partition. Same trolley, more tills.

---

### Beat check

- QUESTION + ANALOGY (1) → FAMILIAR + MAP (2) → PREDICT + PAUSE, SHOW, NAME skew (3) → BREAK, LOOP-PAYOFF (4) →
  SHOW, NAME AQE, its limits (5) → SHOW salting (6) → GUARDRAIL (7) → MORAL, check (8).
- Light moments: the restaurant's trolley (1), "two cashiers, still one trolley" (4), rolling dice (7).

### Accuracy notes for the producer

- Demo output (lesson): AQE off and AQE with default thresholds: 16 tasks, median 43,593, max 346,023 (7.9x). AQE with
  thresholds scaled down (1 MB, advisory 256 KB): `SortMergeJoin(skew=true)`, 19 tasks, max 86,635. Salted, 8 buckets:
  16 tasks, median 45,760, max 125,793.
- The other fifteen bar heights are hand-picked around the median; the hot partition is 46,023 rows of other shops plus
  shop 7's 300,000. The four AQE pieces are drawn about equal (86,635 and three near 86,450, summing to 346,023). The 8
  salts are drawn landing on 6 partitions (two pairs collide), and the busiest is 50,793 + 2 × 37,500 = 125,793; the
  real positions come from the hash.
- AQE's real piece size targets the advisory size (64 MB by default) and pieces are runs of whole map blocks; the
  "four bags" picture is that limit. Spark's docs describe skew handling for sort-merge joins only (left to the lesson).
- "Spark's web page for a running job" is the Spark UI.
