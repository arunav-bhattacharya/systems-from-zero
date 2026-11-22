# Why did more computers make the fraud check slower? The local index asks every shard

- Slug / scene: `secondary-indexes`, `videos/scenes/secondary_indexes.py:SecondaryIndexes`
- Lesson: `shard-04`, section 0, "Each shard indexes its own payments, so a search by card asks them all"
- Audience / level: a complete newcomer. Has met shards and `hash mod N` (Rebalancing and request routing); doesn't
  know what an index, a partition key, a secondary index, a local index or a scatter-gather read is.
- Length: about 4:30 (~750 words of narration, plus two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: the scatter-gather moment: eight shards, all eight ticked, card 242's ten gold payments on six of them,
  shards 2 and 6 saying "none", and "shards asked: 8".
- The learner's real question: the team added computers to go faster, so why did the fraud check get slower?
- Misconception to steelman and break: "an index works the same on 8 machines as on one", and its hopeful corollary
  "the check only needs to ask the shards that hold the card". Broken by shards 2 and 6, which hold nothing and still
  have to be asked, because no shard can tell what the others hold.
- Concept chain: an index finds a card in one step on one computer → split by payment number, a card's payments land
  anywhere → each shard indexes its own payments (local index): writes stay on one shard → a search by card asks every
  shard (scatter-gather), and the cost grows with the shard count (hardest last) → fine when the question names the
  partition key
- Analogy family: the lesson's city library with eight branches. Books (payments) placed at a branch by their number;
  each branch's catalogue (that shard's index) lists its own books only; finding every book by one author means
  phoning all eight branches.
- Open loops: "more computers, slower check" planted in scene 1 → paid off in scene 6; "it also costs time" planted in
  scene 8 → left to the next video (tail latency).
- Assumptions: the numbers are the lesson's demo (`ShardsContactedDemo`): 8 shards, card-242 has 10 payments on shards
  0, 1, 1, 3, 4, 4, 4, 5, 7, 7; 2,000 checks a second cost 16,000 shard requests on 8 shards and 64,000 on 32. The
  fraud rule (more than five in the last minute), one test every 50 milliseconds and "a millisecond on one computer"
  are the lesson opening's. The grey payments in each shard are a picture of other cards' payments, not a count.

## The one picture

Top: the fraud check, a yellow box "fraud check: card-242, last minute". Middle: eight shard boxes in two rows of four
(shard 0 to shard 7), each with a row of small payment tiles (gold for card 242, grey for other cards) and its own
index line at the bottom ("index: card-242 → 2" or "→ none"). Under the grid, one counter line ("shards asked: …").
Captions at the bottom. Yellow dots are requests going out, green ticks are answers, red is a cost. Before the split,
the same tiles sit in one big box, "one computer".

## Scene 1 · A thief and a guard · 0:00–0:35 · [QUESTION] [LOOP-PLANT] [JOKE:warmup]

VO: Picture a thief with a stolen card number. A program tests it with small payments at online shops, one every 50
milliseconds. A very busy, very small shopper.

The payments app has a guard for this. Before it says yes, it counts the card's payments in the last minute, and
refuses when there are more than five. On one computer, that count takes a millisecond. But the payments now live on
8 computers. The team added computers to go faster, and the check got slower. Why?

SCREEN: Title card. Small gold payment chips tick in one after another ("card-242, 1.00", every 50 ms). The fraud
check box appears with "more than 5 in the last minute? refuse". A grey "1 computer: 1 ms" note, then "8 computers:
slower?" with a yellow "?".

## Scene 2 · One computer, one index · 0:35–1:10 · [FAMILIAR] [SHRINK]

VO: Start with one computer. The payments sit in a table, rows of records, one row per payment. An index is a lookup
from a value to where its rows are, like the index at the back of a book. With an index on the card, the check finds
card 242's ten payments in one step, instead of reading every row.

Now split the table over 8 computers. Each piece, on its own computer, is a shard. A payment's shard comes from its
payment number: hash it, divide by 8, keep the remainder. The value that picks the shard is called the partition key.
Find a payment by its number, and you ask exactly one shard.

SCREEN: One big box "one computer" holding ~40 tiles, ten of them gold; an index line "index: card-242 → 10 rows";
a yellow dot runs from the check to the box, the ten gold tiles glow. Then the eight shard boxes appear and the tiles
fly out to them by payment number. The rule "shard = hash(payment number) mod 8" appears; a dot labelled "pay-1234"
goes to one shard.

## Scene 3 · Where does the card index live? · 1:10–1:55 · [PAIN] [ANALOGY] [MAP] [NAME]

VO: But the fraud check doesn't have a payment number. It has a card. An index on a column that isn't the partition
key is called a secondary index. And with shards, we have to decide where its entries live.

Picture a city library with eight branches. Each book sits at one branch, picked by its number, and each branch keeps
a catalogue of its own books only. Adding a book is easy: the branch that gets it files the card. But to find every
book by one author, you phone all eight branches and wait for each librarian to look.

The simplest index for shards works the same way. The branch is a shard, a book is a payment, and the branch's
catalogue is that shard's index. Shard 4's index knows card 242's payments on shard 4, and nothing else. This is a
local index.

SCREEN: "secondary index: an index on something that isn't the partition key" caption. Each shard's index line fades
in ("index: card-242 → 3" on shard 4, "→ none" on shards 2 and 6). Captions map the parts: "branch = shard", "book =
payment", "the branch's catalogue = that shard's index". Shard 4's index line glows; "local index" in yellow.

## Scene 4 · Writes stay simple · 1:55–2:15 · [SHOW]

VO: Writes stay simple. A new payment and its index entry go to the same shard, together or not at all. So the index
is never behind its payments.

SCREEN: A grey payment drops into shard 3; shard 3's index line and the new tile glow together. Caption "payment +
index entry: one shard, all or nothing".

## Scene 5 · Pause and guess · 2:15–3:05 · [PREDICT] [PAUSE] [SHOW] [BREAK] [NAME]

VO: Now the read. Card 242 has ten payments. How many shards does the fraud check have to ask? Pause and guess.

(three seconds)

All eight. The ten payments sit on six shards. But shards 2 and 6 hold none, and they still get asked. Could we skip
them? Only if someone knew they were empty, and shard 4's index knows nothing about shard 2. So the check asks every
shard and merges the answers. That's called a scatter-gather read. And a card with no payments at all? Still eight.
Seven librarians say "not here", and so does the eighth.

SCREEN: The check pulses; yellow "?" over the grid; countdown. Eight yellow dots fly out at once, eight green answers
come back (counts 1, 2, 0, 1, 3, 1, 0, 2); gold tiles glow on shards 0, 1, 3, 4, 5, 7; shards 2 and 6 glow grey with
"none". Counter "shards asked: 8, card 242 found on 6". Caption "scatter-gather: ask every shard, merge the answers".
Then the index lines all show "none" briefly and eight dots go out again.

## Scene 6 · More shards, more asking · 3:05–3:40 · [LOOP-PAYOFF] [JOKE:release]

VO: Now the cost. At 2,000 checks a second, that's 16,000 shard requests a second on 8 shards. Add a ninth shard, and
it gets all 2,000 checks a second too, just like the others. So adding shards adds no capacity for this question.
That's the slower check from the start. Hiring more librarians doesn't help when every call rings every branch.

SCREEN: "2,000 checks a second × 8 shards = 16,000 shard requests a second" (red). A dashed ninth shard outline at the
edge with "+2,000 a second". Caption "more shards: more asking, not less".

## Scene 7 · Two guardrails · 3:40–4:20 · [GUARDRAIL]

VO: A local index has another blind spot. It can't keep a value unique. No shard sees the others' entries, so none can
tell that a value is already used elsewhere. MongoDB, a popular database that splits its data over shards, says so in
its manual: a unique index works only if it starts with the partition key.

And none of this hurts when the question names the partition key. Split the payments by shop instead, and "card 242's
payments at shop M-0042" goes to that one shop's shard, and uses the local index there.

So: a local index is cheap when a question names the partition key, and costly when it doesn't.

SCREEN: Captions "unique? no shard can see the others' entries" (red), "MongoDB: a unique index must start with the
partition key". Then the rule becomes "shard = hash(shop) mod 8" and one dot goes to one shard: "card-242 at shop
M-0042: 1 shard". Rule caption in yellow.

## Scene 8 · Moral and a check · 4:20–4:55 · [MORAL] [PRINCIPLE] [LOOP-PLANT] [PREDICT] [PAUSE]

VO: So the index works on 8 machines, but each machine only knows its own. Ask a question without the partition key,
and you ask everyone. Asking eight shards costs eight times the work. It also costs time, in a way that surprises most
people, and that's next.

One quick check. The app grows to 32 shards, with the same local index. How many shard requests do 2,000 checks a
second cost now? Pause and think.

(three seconds)

64,000. Every check asks all 32.

SCREEN: Every shard's index line glows in turn. Caption "no partition key in the question: ask every shard"
(yellow). Then the check caption with countdown; "2,000 × 32 = 64,000 shard requests a second" (red).

---

### Beat check

- QUESTION (scene 1) from a felt problem; FAMILIAR and SHRINK (scene 2) from one computer.
- PAIN, ANALOGY and MAP (scene 3), each part mapped out loud; names (secondary index, local index) right after.
- PREDICT with PAUSE (scene 5 and the check in scene 8), SHOW right after.
- BREAK: "ask only the shards that have it", broken by shards 2 and 6 (scene 5).
- NAME after SHOW: scatter-gather (scene 5).
- GUARDRAIL (scene 7) and MORAL (scene 8) last. Light moments: the very small shopper (0:10), seven librarians saying
  "not here" (3:00), hiring librarians (3:35).

### Accuracy notes for the producer

- The lesson indexes a card fingerprint, a code worked out from the card number; the video says "the card".
- Card 242's shard list is the demo's output for 8 shards; shards 2 and 6 hold none of its payments. The grey tiles
  stand for other cards' payments.
- The "ninth shard" is a picture of the lesson's sentence "every new shard receives all 2,000 checks a second"; the
  demo counts 8 and 32 shards.
- MongoDB's rule is "the shard key, or a prefix of it"; the video says "starts with the partition key" after saying
  MongoDB calls it the shard key only implicitly (it uses the course's word).
- Tail latency (waiting for the slowest shard) and the global index are the next sections and the next video.
