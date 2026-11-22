# Where do the new payments go? Key ranges and the shard that does all the work

- Slug / scene: `range-vs-hash`, `videos/scenes/range_vs_hash.py:RangeVsHash`
- Lesson: `shard-01`, section 1, "Key ranges keep neighbours together, and pile new payments onto the last shard"
- Audience / level: a complete newcomer. Knows card payments and sorting by postcode; nothing about shards or keys.
- Length: 4:35 (~830 words of narration, two 3-second pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: shard 3 full and red, "0 0 0 10,000" under the shards (`POSTER=126`)
- The learner's real question: once the data is cut into shards, which shard does each payment go to, and why would
  that choice matter?
- Misconception to steelman and break: "the busy shard is just too big, so split it". Splitting at 14:25 makes the
  upper half the new last range, and every new payment goes there.
- Concept chain: one machine can't keep up and copies don't help → cut into shards → sort keys and give each shard a
  stretch (key ranges) → key = time sends every new payment to the last shard (hot spot) → splitting moves it →
  shop first spreads new payments and keeps a shop's day together → the bill: a time window asks every shard → the
  rule: the start of the key decides where new rows land
- Analogy family: the lesson's parcel depot, bays sorted by postcode; it bends to "sorted by the date on the label".
- Open loops: "which shard does a payment go to?" planted in scene 1 → answered by the rule in scene 6 and the check.
- Assumptions: numbers are the lesson's (25,000 payments a second, 3 TB of 4 TB, 40 GB a day; four range shards keyed
  by time; 10,000 afternoon payments all on shard 3; split at 14:25; 500 shops; M-0310#14:00:00.005#pay-20001; M-0042).
  The rain of dots is a picture, not a count, except the "0 0 0 10,000" line.

## The one picture

A sorted line of keys across the top (ticks where one shard's stretch ends), with the current key format above it.
Four shard boxes under it (five after the split), each with a fill bar for new rows and a count beneath. Gold dots are
new payments falling from their place on the line into the shard under it; teal marks one shop's run; purple marks
the 14:00 to 14:05 window. Captions at the bottom.

## Scene 1 · One machine, stuck · [QUESTION] [FAMILIAR]

VO: It's the busiest shopping day of the year. You tap your card at a café, and the reader thinks for four seconds
before it beeps. Behind it, one database machine records the card payments of thousands of shops. It can't store the
25,000 payments a second that are arriving. And its disk fills up by 40 GB a day. A copy won't help this time. Every
copy stores every payment and writes every payment, so a fourth copy is one more full disk that writes no faster. So
we cut the payments into parts, one machine per part. Each part is called a shard. Every payment lives in exactly one.
The question is: which one?

SCREEN: One machine box between "25,000 a second" and "3 TB of 4 TB, +40 GB a day"; copies stack behind it; then four
boxes ("bay 0" to "bay 3").

## Scene 2 · The depot · [ANALOGY] [MAP] [NAME]

VO: Picture a parcel depot with four bays and a van for each. It sorts by postcode. Bay 0 takes the postcodes from the
start of the list up to one boundary, bay 1 takes the next stretch, and so on. A driver who delivers to one street
finds all its parcels in one bay, because neighbouring postcodes sit together. Our store does the same with keys. A
key is the value we look a row up by. Keep the keys in sorted order, and give each shard one unbroken stretch of them.
That's key-range sharding.

SCREEN: The sorted line draws ("first postcode" to "last postcode"), cut where the bays meet. One street (teal) rains
into bay 1. Bays become shards; the line's ends become "smallest key", "largest key".

## Scene 3 · Key = time · [SHRINK] [PREDICT] [PAUSE] [SHOW] [NAME]

VO: Now pick the key. Say it's the time the payment was made. The boundaries were cut from the morning's payments, so
the four shards are the same size. It's the afternoon. A payment arrives, made at 14:00:00.005. Which shard does it go
to? Pause and guess.

(three seconds)

Shard 3. It's later than every key already stored, so it sorts past the last boundary. And the next payment? Same
story. All afternoon, every new payment is the newest one. Ten thousand new payments, and all ten thousand land on
shard 3. Four machines, and one does all the writing. The cluster writes no faster than one machine. A shard with far
more work than the rest is called a hot spot.

SCREEN: Equal grey fills; key "14:00:00.005"; countdown; one gold dot falls at the far right into shard 3, then a
stream; counts "0 0 0 10,000"; shard 3 outlined red, the others grey.

## Scene 4 · Split it? · [BREAK] [JOKE:release]

VO: The obvious fix: shard 3 is too busy, so split it in half. The store does exactly that, at its middle key, 14:25.
Let's see if it helps. Now there are five shards. Shard 4 holds everything from 14:25 on. And the next new payment
goes... to shard 4. And the next. And the next. Splitting moved the hot spot to the end. It couldn't spread it. Well...
we've built a brand new shard whose only job is the future.

Here the depot picture needs one change. Sort parcels by the date on the label, and every new parcel is today's, so
every one goes to the last bay. This one hides well in testing. Load a year of old payments in one go, and they spread
nicely, because the boundaries were cut to fit them. The trouble starts with live traffic, when every payment is the
newest one.

SCREEN: Four boxes become five, "14:25" under the new tick; dots fall into shard 4, which turns red. A grey rain fills
all five evenly ("a year of old payments"), then the gold rain goes only to the end.

## Scene 5 · Shop first · [SHOW]

VO: The fix is to put something before the time. Make the key the shop's id, then the time, then the payment's number.
Now the boundaries are shop ids. And the afternoon's payments come from all 500 shops, so they land in all the shops'
ranges, on every shard. And one shop's payments still sit together, sorted by time. All of shop M-0042's day is one
unbroken run, on one shard.

SCREEN: Back to four shards; key "M-0310#14:00:00.005#pay-20001"; the line runs "first shop" to "last shop"; gold
dots fall all along it; every shard fills; a teal band "M-0042" near the start, shard 0 glows.

## Scene 6 · The bill, and the rule · [GUARDRAIL] [PRINCIPLE]

VO: But there's a bill, and it arrives on the other question. Every payment from 14:00 to 14:05, across all shops. With
the time first, that sat on one shard. With the shop first, those payments are a small run inside every shop's range.
So the question has to ask all four shards. So neither key is better. Each one makes a different question cheap.
Here's the rule: whatever comes first in the key decides where new rows land. Choose it from the question that must
be cheap. One honest limit. The shop-first key spreads new payments only because they happen to come from many shops.
Next, we'll spread keys whatever they look like, with a hash.

SCREEN: Purple slivers all along the line; all four shards glow purple. Captions carry the rule.

## Scene 7 · Moral and a check · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, where do the new payments go? With key ranges, wherever the start of the key sends them. Time first, and
that's always the last shard. One quick check. A shop keeps its orders in ranges of the order number, which counts up
by one for each new order. Where do today's orders land? Pause and think.

(three seconds)

All on the last shard. A number that only grows is a time in disguise. Put something else first.

SCREEN: The time-first rain into shard 3 again; then the key "order number: 1, 2, 3..."; countdown; the rain goes to
shard 3, red.

---

### Beat check

- QUESTION from a felt pain (four seconds at the till), FAMILIAR (a copy, from the Replication track) dismissed fairly.
- ANALOGY + MAP (depot, bays, postcodes, one street's parcels) before NAME (key-range sharding).
- PREDICT + PAUSE (which shard for 14:00:00.005; where today's orders go), each followed by SHOW.
- BREAK: the obvious fix (split) run to its result; the analogy bent where it stops fitting (date on the label).
- NAME after SHOW: shard, key, key-range sharding, hot spot.
- GUARDRAIL: the other question gets expensive; the shop-first spread depends on many shops. MORAL and the check last.
- Light moments: the four-second beep; the new shard whose only job is the future.

### Accuracy notes for the producer

- The lesson's stepper uses four range shards keyed by time and says all 10,000 afternoon payments land on shard 3;
  the Try it uses eight shards (10,000 on shard 7; with the shop first, 1,178 to 1,329 per shard). The video uses the
  stepper's four and shows no per-shard counts for the shop-first case.
- The boundaries' actual times are not shown; the line is labelled "earlier" to "later".
- Binary search over the boundaries, MongoDB's 128 MB ranges and how stores pick boundaries are left to the lesson.
- "Next, with a hash" points to section 2 (hash sharding), which this video doesn't cover.
- The order-number check is the lesson's closing question.
