# One drawer per account: how Cassandra finds 20 rows in 50 million

- Slug / scene: `wide-column`, `videos/scenes/wide_column.py:WideColumn`
- Lesson: `model-05`, section 0, "A table is a map of partitions, each a sorted list of rows"
- Audience / level: a complete newcomer. Can read a little code; knows nothing about clusters, hashing or CQL.
- Length: about 4:45 (~750 words of narration, two guesses, silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: how does a database hand back an account's 20 newest payments out of 50 million
  without touching the rest, and why does it refuse some questions outright?
- Misconceptions to steelman and break: (1) "a new row goes at the end and the read sorts" (broken by the 09:00
  payment, written last, landing between 09:40 and 08:15 with nothing rewritten); (2) "any question works, only
  slower" (broken by "every FAILED payment": no account, no token, CQL refuses without ALLOW FILTERING); (3) "the
  partition key is only about finding things" (broken by the sizes: by shop alone grows forever, the busiest day
  432,000 rows)
- Concept chain: a drawer per account (partition, partition key) → slips in date order (clustering columns) → the
  coordinator hashes the key to a token on the ring, which picks the replicas → a write lands in its sorted place → a
  time window is one slice, read from either end → no partition key, no token: refused → a drawer never splits, so
  size the key (hardest last) → the name wide-column
- Analogy family: an office with a drawer of payment slips for each account, filed by date, newest at the front.
  Where it breaks: a paper drawer has one copy; Cassandra keeps the whole drawer on each replica. Renaming joke:
  "deep drawer" would have been a better name than wide-column.
- Open loops: "why does it flatly refuse some questions?" planted in scene 1 → paid off in scene 6
- Assumptions: rows, the token and every number are the lesson's (stepper rows pay-81730, pay-81720, pay-81701,
  pay-81655 and the new pay-81723; token -4994511478997274402; 100,000 rows and 100 MB; 40,000 a day at about 6 MB;
  5 a second, 432,000 a day; 18,000 an hour; 168 hour partitions a week). The six nodes and where the token sits on the
  ring are drawn for the picture.

## The one picture

Left: the cluster, six nodes around a ring; later the drawer-size chart in the same place. Right: the drawer for
A-1001 (blue box, gold header), rows sorted newest first. Top: the table's key, first as two chips (partition key,
gold; clustering columns, green), at the end as the `PRIMARY KEY` line. Bottom: the query strip (the question on the
left, the verdict on the right) and a caption line. Yellow is a read or a write in progress, green a row returned,
red a refusal.

## Scene 1 · Twenty out of fifty million · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: Account A-1001 wants its 20 newest payments. The payments company keeps 50 million. They live in Cassandra, a free
database program that spreads its data over many computers. Each computer is called a node, and together they work as
one database, called a cluster. So how does it hand back 20 rows without touching the other 50 million? And why does
it flatly refuse some questions?

SCREEN: Title card. "50,000,000 payments" on the right. Six nodes appear around a ring on the left. Query strip:
"A-1001: the 20 newest", verdict "?". A red "some questions: refused" note.

## Scene 2 · A drawer per account · 0:30–1:15 · [FAMILIAR] [ANALOGY] [MAP] [NAME]

VO: Picture an office with a drawer of payment slips for each account, filed by date, newest at the front. To find
A-1001's newest slips, you open one drawer and lift the front few out. The other drawers stay shut. Cassandra keeps rows
the same way. The drawer is called a partition. Every row with the same account goes into it, so the account is the
partition key. The order inside comes from the clustering columns: the time it was created, newest first, then the
payment id, to break ties.

SCREEN: A cabinet of four drawer fronts (A-1001, A-2002, A-3003, "one drawer per account"). A-1001 glows and opens
into the drawer box with its four rows; the others fade. Captions map drawer = partition, account = partition key,
date order = clustering columns; the two key chips appear at the top.

## Scene 3 · Which node holds the drawer? · 1:15–1:55 · [SHOW] [NAME] [BREAK of the analogy]

VO: But which node holds the drawer? The node that takes your request, called the coordinator, hashes the partition
key. It turns A-1001 into a big whole number called a token, always the same for the same key. Picture every possible
token around a circle, with each node in charge of some stretches of it. The token's place picks the nodes that keep a
copy of the drawer, usually three, called replicas. Only they get asked. Where the office picture breaks: paper has one
copy, and each replica holds the whole drawer.

SCREEN: Node 1 glows as the coordinator. "hash('A-1001')" and "-4994511478997274402" in the ring's centre. A yellow
dot travels to its place on the ring; the next three nodes clockwise glow gold, each with a small "A-1001" copy.

## Scene 4 · Where does a late slip go? · 1:55–2:45 · [SHRINK] [PREDICT] [PAUSE] [SHOW] [BREAK]

VO: Now open the drawer. Four payments, newest first. The 20 newest are the first 20 rows; here, all four. A new
payment arrives, timed nine o'clock, and written last. Where does it go? Pause and guess. (three seconds) Between nine
forty and eight fifteen. Only the account was hashed. The time says where inside the drawer it goes, and no other row is
rewritten. If you guessed the bottom, that's the spreadsheet habit: add at the end, sort when you read. Here the order
is how rows sit, in memory and on disk.

SCREEN: Query "A-1001: the 20 newest", verdict "the first rows: all 4". A yellow pay-81723 chip at 09:00 hovers above
the drawer; countdown. The two older rows slide down, the chip lands in slot three. Verdict "lands in its sorted place ·
rows rewritten: none". A ghost row at the bottom, crossed out, for the spreadsheet habit.

## Scene 5 · This morning is one slice · 2:45–3:15 · [SHOW]

VO: So ask for this morning, from eight to ten. The node jumps to the first row before ten, reads on while rows are inside
the window, and stops at the first row before eight. Three rows read, three returned. The ten thirty row and yesterday's
row are never touched. Oldest first? Same three rows, read from the other end. Still no sort.

SCREEN: Query "A-1001, 08:00 to 10:00". An arrow beside the drawer runs down rows 09:40, 09:00, 08:15 (green); the
10:30 and 23:59 rows dim. Verdict "one slice: 3 read, 3 returned". Then the arrow flips: "same slice, other end · sort
step: none".

## Scene 6 · The question it refuses · 3:15–3:55 · [BREAK] [LOOP-PAYOFF] [JOKE:is-the-explanation] [NAME]

VO: Now the question it refuses. Every failed payment, without naming an account. No account, no token, no drawer. The
only plan is to open every drawer on every node. So CQL, the language you query Cassandra in, refuses, unless you add two
words: ALLOW FILTERING. That's the database asking: are you sure? You're about to open every drawer in the building. So
the rules follow from the picture. The partition key needs an equals, or there's no token. Clustering columns can be
limited only from the left. And a different question gets a different table.

SCREEN: Query "every FAILED payment, any account". The ring's centre reads "no account: no token"; every node flashes
red; verdict "refused, unless ALLOW FILTERING". Captions for the two rules.

## Scene 7 · How big can a drawer get? · 3:55–4:35 · [GUARDRAIL]

VO: One more catch. A drawer never splits across nodes, and the Cassandra docs advise under 100,000 rows and 100
megabytes. Its size is the write rate times how long the key stays the same. Key a shop's payments by shop alone, and
the drawer grows forever. Add the day: 40,000 payments a day, about 6 megabytes. Fine. But on the busiest day of the
year, the biggest shop takes 5 a second: 432,000 rows. One drawer per hour gives 18,000. The price: a week of history is
now 168 drawers, read in parallel and merged. Size it for your busiest key.

SCREEN: The ring gives way to four bars against a dashed "100,000 rows" line: shop alone (red, an arrow off the top),
shop + day 40,000 (green), busiest day 432,000 (red), shop + hour 18,000 (green). Captions for the sum and the price.

## Scene 8 · The name, the key, and a check · 4:35–5:10 · [NAME] [JOKE:soften] [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: This shape gives the family its name, wide-column, because one partition can hold a great many rows. It has nothing
to do with a column store, which keeps each column's values together. Deep drawer would have been a better name. Here's
the key, read from the inside out. Inside the double brackets, which drawer. After it, the order inside. So the partition
key picks the drawer, the clustering columns pick the place in it, and a good question opens one drawer and lifts out
one run. One quick check. A query names A-1001 and payment pay-81723, but no time. One run, or refused? Pause and think.
(three seconds) Refused. The rows are in time order, so an id with no time isn't one run. Without ALLOW FILTERING, CQL
says no.

SCREEN: The key chips become `PRIMARY KEY ((account_id), created_at, payment_id)` with the inner part gold and the rest
green. The ring returns, dimmed. Query "A-1001 and pay-81723, no time"; countdown; the drawer's rows flash red; verdict
"refused, unless ALLOW FILTERING".

---

### Beat check

- Opens with QUESTION (scene 1); FAMILIAR + ANALOGY + MAP (scene 2) before the names partition, partition key and
  clustering columns.
- PREDICT with PAUSE: the late slip (scene 4) and the check (scene 8), each followed by SHOW.
- BREAK: the spreadsheet habit (scene 4), the refused question (scene 6), the analogy's limit (scene 3), the drawer
  that grows forever (scene 7).
- NAME after the picture: coordinator, token, replicas (3), CQL and ALLOW FILTERING (6), wide-column (8).
- GUARDRAIL (scene 7) and MORAL (scene 8) last. Light moments: "are you sure? every drawer in the building" (3:35),
  "deep drawer" (4:45).

### Accuracy notes for the producer

- Every row, the token, and every number is from the lesson (section 0 and its stepper and Try it). The six nodes and the
  token's place on the ring are drawn for the picture; a real cluster maps tokens to nodes with many ranges per node.
- "Usually three" replicas is the lesson's wording (the replication factor is set per keyspace).
- The lesson's "limited only from the left, with at most one range at the end" is shortened to "only from the left".
- The check's answer follows the lesson: "a payment_id without a created_at is not" fine, and CQL refuses it unless you
  add ALLOW FILTERING.
- Left to the lesson and later sections: the commit log, memtable and SSTables (how the sorted row reaches disk),
  tombstones, and measuring ALLOW FILTERING.
- Times are spoken as people say them ("nine forty"); the screen shows 09:40:27 and so on.
