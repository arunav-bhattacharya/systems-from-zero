# One owner per key: how MapReduce counts across machines

- Slug / scene: `mapreduce`, `videos/scenes/mapreduce.py:MapReduce`
- Lesson: `batch-03`, section 1, "Map, shuffle, reduce: counting across machines, one key at a time"
- Audience / level: a complete newcomer. Knows a program can count words in a file; knows nothing about clusters,
  hashing, shuffles or reducers.
- Length: 5:52 (~940 words of narration, three pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=216`, the end of the reduce step: three nodes with tagged pairs, three reducers with `declined = 2`,
  `approved = 5`, `refunded = 2` and their output files
- The learner's real question: if `approved` sits on all three machines and three machines do the counting, who
  ends up with the total, and how does anyone know where to send what?
- Misconception to steelman and break: (1) "send everything to one counter", broken by the lesson's numbers (1 TB
  through a 125 MB/s link is over two hours; a billion counters in 2 to 4 GB); (2) "send each note to whichever
  counter is free", broken on screen: `approved` lands on all three counters and nobody has the total.
- Concept chain: count where the data sits → many counters need a rule every machine can work out alone → a hash
  modulo R picks one owner per key → map, shuffle (fetch and sort), reduce → a lost machine's map work is just done
  again, because map is deterministic (hardest last)
- Analogy family: the lesson's library. Forty branches counting books by author by morning; the central library too
  small for the books; short notes instead of books; every author has one owner branch, which every branch works out
  by itself; a lost note is written again from the books.
- Open loops: the warm-up guess ("how many counters count `approved`?") planted in scene 2 → paid off in scene 6;
  "the central library" in scene 1 → called back in scenes 3 and 4.
- Assumptions: all numbers are the lesson's: three blocks (`approved declined approved`, `approved refunded approved`,
  `declined approved refunded`), nine pairs, reducers by `(hashCode & Integer.MAX_VALUE) % 3` (declined 0, approved 1,
  refunded 2; with 4 reducers approved goes to 3), outputs `declined=2, approved=5, refunded=2`, hash code of
  `approved` 1185244855 (checked: Java's `String.hashCode`), 1 TB / 125 MB/s, 2 to 4 GB, the paper's 200 of 1,746
  killed, 933 s against 891 s. The "whoever is free" spread of `approved` is a made-up picture of a rule nobody uses.

## The one picture

Top row: three node boxes (blue), A, B, C, each holding one block of the log; later each block's words become
coloured pairs (`approved` green, `declined` gold, `refunded` purple) with a small owner tag under each. Bottom
row: three counters (teal), 0, 1, 2, later renamed reducers, each with one line of content and its output file
under it. The strip between the rows holds one thing at a time (the hash sum, the Java rule, the re-run of map 2).
Captions sit at the bottom. In the opening, the same top boxes are library branches with books, and the bottom
centre is the central library.

## Scene 1 · The library · 0:00–0:30 · [QUESTION] [ANALOGY] [JOKE:pivot]

VO: Picture a city library on the night of its yearly count. By morning, the council wants to know how many books
it owns by each author. And the books sit in forty branches across town.

The obvious plan: bring every book to the central library and count them there. With forty branches, that's a
building too small for the books, and a count still going next week.

The better plan sends the counting to the books. Each branch counts its own shelves, and sends on short notes,
never books.

SCREEN: Three branch boxes ("branch 1 of 40" ...) with rows of coloured books. A small "central library" box below.
Books fly down and pile up past its roof; its outline turns red; caption "a count still going next week". Then the
pile goes, each branch writes a yellow note, and the notes leave.

## Scene 2 · The same problem on computers · 0:30–1:00 · [FAMILIAR] [PREDICT] [PAUSE] [LOOP-PLANT]

VO: Computers have the same problem. A payment company keeps a log of payment events, and it's too big for one
machine. So it's cut into blocks, spread over three machines. Each machine in the group is called a node.

The question: how many times does each status appear? Approved, declined, refunded.

Say three machines do the counting. The word approved appears on all three nodes. How many of the counters end up
counting approved? Pause and guess.

(three seconds)

Hold on to your guess. Let's build the answer.

SCREEN: The books go; the branches become "node A, block 1" ... with their log lines. Caption "node: one machine in
the group". The three statuses light up in turn. Every `approved` glows; countdown bar.

## Scene 3 · Version one: one counter · 1:00–1:40 · [PAIN] [WISH] [LOOP-PAYOFF of the library]

VO: Version one: every node sends every status it reads to one counting machine. For nine words, that's fine.

Now ask a bigger question: how many payments per card, over a billion cards. The counter now receives the whole
input through one network link. One terabyte, through a link that moves 125 megabytes a second, takes over two
hours.

And it has to keep a billion counters in memory, on a machine with two to four gigabytes. That's the central library
again.

What we want is many counters, each with a share of the work. But then every node must know where to send each note,
without asking anyone.

SCREEN: One "counting machine" box at the bottom centre; arrows from the three nodes; dots run; it shows
"approved 5 · declined 2 · refunded 2". Captions "1 TB through one 125 MB/s link: over 2 hours" (arrows turn red)
and "a billion counters, in 2 to 4 GB" (box turns red). The box splits into counters 0, 1, 2; caption "where does
each note go?"

## Scene 4 · The easy rule, broken · 1:40–2:00 · [BREAK] [JOKE:release]

VO: Let's try the easy rule first. Send each note to whichever counter is free.

Watch approved. Its notes land on all three counters. Each one has part of the count, and nobody has the total. So
now we need one more step to add the parts up. Well... we just built the central library again, only smaller.

SCREEN: Green dots from every `approved` fly to different counters; each counter shows "part of approved" and a red
"?". Caption "if notes go to whoever is free".

NOTE: The spread is a made-up picture of a bad rule; no numbers are shown.

## Scene 5 · One owner per key · 2:00–2:45 · [ANALOGY] [MAP] [SHRINK] [NAME: hash]

VO: Back to the library. There, every author has one owner branch. Every branch sends its notes for that author to
the owner, and works out the owner by itself, from the name alone.

Let's map that. The branches are the nodes. The books are the log lines. A note is a pair: a word, and the number
one. The word is the key, whatever you group by. And the owner branch is a counter.

The rule that picks the owner is a hash function. It turns a value into a number, and the same value always gives
the same number, on every machine.

Divide that number by three and keep the remainder. That's a counter from zero to two. Approved gives one. Declined
gives zero. Refunded gives two.

Hadoop, the free copy of Google's design, writes the rule like this. A hash code can be negative, so the first part
clears the sign, to keep the remainder a real counter number.

SCREEN: Mapping captions, each with its part glowing; an example chip "approved, 1". The strip shows
`"approved".hashCode() = 1185244855` and `1185244855 % 3 = 1`; each counter gets "owns approved" (and so on). Then
the strip shows `(key.hashCode() & Integer.MAX_VALUE) % 3`.

## Scene 6 · Map, shuffle, reduce · 2:45–3:35 · [SHOW] [LOOP-PAYOFF] [NAME]

VO: Now run it. Map: each node reads its own block, and turns every word into a pair. Nine pairs in all. No node
knows what the others found.

Each node tags every pair with its owner, and writes them to its own disk. Approved is tagged one, on every node.

The shuffle: each counter fetches its pairs from every node, over the network. Then it sorts them by key, so equal
keys sit together. With millions of keys, that lets it finish one key and move on.

Reduce: each counter adds up each key, and writes one output file. Declined, two. Approved, five. Refunded, two.

So, your guess? Exactly one counter counts approved. No last step adds anything up, because every key lives in one
place.

This is MapReduce, published by Jeff Dean and Sanjay Ghemawat of Google in 2004. You write two small functions. Map
turns one record into pairs. Reduce turns one key and all its values into a result. Everything between them is the
shuffle. And the counters are called reducers.

SCREEN: Words become pairs; owner tags appear; nine pair copies fly to their counters ("approved: 1, 1, 1, 1, 1");
then "declined = 2", "approved = 5", "refunded = 2" and `part-00000` to `part-00002`. Counter 1 glows; caption
"exactly one counter counts approved". Counters are renamed reducers; captions for map, reduce and shuffle.

## Scene 7 · Lose a machine · 3:35–4:15 · [PREDICT] [PAUSE] [SHOW] [BREAK]

VO: Now let's lose a machine on purpose. Node B finishes its map, and then dies, before the reducers fetch its pairs.

Its map task already finished. Does it have to run again? Pause and guess.

(three seconds)

Yes. Those pairs sat on B's own disk, so they died with it. The master, the program that hands out the tasks, runs
map two again on node C, which keeps a copy of block two.

The reducers fetch from C instead, and the totals come out the same. That only works because map is deterministic:
same input, same pairs, every time.

Finished reducers never run again. Their files are already in the file system, in three copies. In the library, a
lost note is just written again from the books.

How much does a failure cost? In the paper's one terabyte sort, the authors killed 200 of the 1,746 workers a few
minutes in. The job took 933 seconds instead of 891. Five percent slower.

SCREEN: Node B turns red ("node B: crashed"), its pairs vanish, the reducers read "waiting for map 2". Countdown.
Under node C: "map 2, run again on C" with B's three pairs. Pairs fly again; the same three totals; green ticks by
the output files. Caption "1 TB sort: 200 of 1,746 killed. 933 s instead of 891 s".

## Scene 8 · Two guardrails · 4:15–4:35 · [GUARDRAIL]

VO: Two things to watch. Change the number of reducers, and keys move. With four, approved goes to reducer three,
not one.

And one key never splits. If most of the log is approved, one reducer gets most of the work, and the whole job waits
for it.

SCREEN: Node B comes back. Strip: `1185244855 % 4 = 3`; caption "4 reducers: approved moves from 1 to 3". Then a
stream of green dots into reducer 1; caption "one key, one reducer: a busy key slows the whole job".

## Scene 9 · Moral and check · 4:35–5:00 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So, the moral: count where the data sits. Send each key to one owner, picked by a rule every machine works out
alone. And if a machine dies, just do its work again.

One quick check. Declined appears on nodes A and C. How many reducers count it, and which one? Pause and think.

(three seconds)

One. Reducer zero, every time.

SCREEN: Captions for the moral. Both `declined` pairs glow; countdown. Reducer 0 glows; caption "one owner per key".

---

### Beat check

- QUESTION (scene 1), from the lesson's library; FAMILIAR (scene 2) with the warm-up's prediction and a pause.
- PAIN and WISH (scene 3) with the lesson's numbers; BREAK of the easy rule (scene 4) before the real rule.
- ANALOGY + MAP said out loud (scene 5); the hash named only after the owner-branch idea.
- SHOW (scene 6), the loop paid off by name ("so, your guess?"), then NAME (MapReduce, reducers, shuffle).
- PREDICT + PAUSE + SHOW on the failure (scene 7); GUARDRAIL (scene 8); MORAL and a check (scene 9).
- Light moments: the building too small for the books (0:20), the central library again, only smaller (1:55).

### Accuracy notes for the producer

- The pairs, tags and totals are the lesson's `MapReduceTraceDemo` output. The hash code 1185244855 and the
  remainders (3 reducers: 1, 0, 2; 4 reducers: approved 3) were computed with Java's `String.hashCode` rule.
- The library has forty branches; the picture shows three, labelled "of 40".
- "Writes them to its own disk": the lesson's map output goes to the map node's local disk, one region per reducer.
- The sort at the reducer is said, not shown: in the toy each reducer gets one key.
- The paper's 200 of 1,746 are worker processes ("programs doing the work" in the lesson); 933 s vs 891 s is about 5%.
- Left to the lesson: the combiner (next section), skew in depth (lesson 8), HDFS blocks and replication (section 0).
