# A scan that empties the shelf: LRU, and SIEVE's visited bit

- Slug / scene: `cache-eviction`, `videos/scenes/cache_eviction.py:CacheEviction`
- Lesson: `cache-05`, section 3, "Choosing what to throw away: LRU, LFU and newer bets"
- Audience / level: a complete newcomer. Can read a little code; has used a library; knows nothing about caches,
  eviction or threads.
- Length: 4:31 (~720 words of narration at Kokoro's ~150 words a minute with sentence gaps, four pauses, silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=169`, the end of the SIEVE scan (A, B and C on the shelf with their dots back, scan books at the
  newest end, the hand among them)
- The learner's real question: when a cache is full, which key should go, and why does the usual answer fail?
- Misconceptions to steelman and break: (1) "the least recently used key is the safe one to drop" (broken by a
  one-time scan that makes every key look recent and empties the shelf of popular books); (2) "a better policy must
  keep more records" (SIEVE keeps one bit and moves nothing, and wins).
- Concept chain: a full cache must guess → FIFO, LRU, LFU use different evidence → LRU moves a key on every hit, so a
  scan pushes the popular keys out → most keys are read once (one-hit wonders) → SIEVE: arrival order, a visited bit,
  a hand that spares in place (hardest last) → the lab's numbers → limits
- Analogy family: the lesson's library. A full shelf, a new book, a basement. Sticky dots on the spines stand for the
  visited bit; a hand walks along the shelf.
- Open loops: "which one goes?" planted in scene 1 → answered for LRU in scene 3 and for SIEVE in scene 5
- Assumptions: numbers are the lesson's (6,594 traces, 26% and 72% one-hit wonders, the S3-FIFO study of 2023, SIEVE
  of 2024; the lab's PolicyDemo at 10,000 slots: FIFO 29.8%, LRU 26.1%, SIEVE 21.6%, with scans 32.2%, 29.0%, 21.6%;
  scans changed little at 1,000 slots; twice LRU's speed on 16 threads). The six-book shelf and its order (D, A, E, B,
  F, C), the new book G and the scan books S1 to S6 are a toy, traced by hand with the lab's SIEVE code.

## The one picture

A shelf of six book slots across the middle, oldest on the left and newest on the right. Popular books A, B and C
are gold, ordinary books blue, scan books purple. A new book waits at the right end; an evicted one drops toward
the "basement" label and fades. SIEVE adds green dots on read books and a yellow hand above the shelf. A title line
at the top names the policy; a ticker line under the shelf says what just happened; captions at the bottom. For the
numbers and the code, the shelf steps aside for a table, then Java and Kotlin side by side, and comes back for the
check.

## Scene 1 · The question · 0:00–0:28 · [QUESTION] [ANALOGY] [LOOP-PLANT]

VO: Picture a library with full shelves. A new book arrives, and one book has to go down to the basement. Which one?

A cache faces the same choice. It keeps copies of data close by in memory, and when memory is full, it has to guess
which key it will need least soon, and throw that one out.

Every way of choosing, called an eviction policy, answers with a different kind of evidence about the past.

SCREEN: Title card. Six books slide onto the shelf (D, A, E, B, F, C); a new book G waits at the right; "basement"
appears bottom left. Captions "the shelf is full: which book goes?", the cache sentence, the eviction-policy sentence.

## Scene 2 · FIFO, LRU, LFU · 0:28–0:56 · [FAMILIAR] [SHRINK] [SHOW]

VO: FIFO, first in, first out, removes the book that arrived first, however often people read it.

LRU, least recently used, removes the book nobody has opened for the longest. LFU removes the one opened the fewest
times.

LRU is the usual choice. Here's how it keeps its order. The shelf runs from oldest to newest. When someone reads a
book, it moves to the newest end.

And the book that goes is the one at the oldest end.

SCREEN: Title lines for FIFO (the oldest outlined red), LRU, LFU. "oldest" and "newest" under the ends. Reads of A,
then B: each slides to the newest end. G arrives; the oldest, D, drops away; G takes the newest slot.

## Scene 3 · One scan · 0:56–1:40 · [PREDICT] [PAUSE] [BREAK] [JOKE:release] [PAIN]

VO: Now the three popular books, A, B and C, get read all day. Then, one night, a report reads every key once. That's
called a scan.

Before you watch, guess. What does a scan do to an LRU shelf? Pause and guess.

(three seconds)

Each scan book arrives, looks like the newest thing on the shelf, and pushes the oldest one out. Six scan books later,
every popular book is in the basement.

Tomorrow, the first reader of A misses. Well, that's not the shelf we wanted.

LRU has a second cost. Every hit moves a key, and the list it moves on has a lock, so only one thread at a time can
change it. Busy threads queue for it.

SCREEN: C, A and B are read and move to the newest end. "a one-time scan: every key read once" in purple. Countdown.
Scan books S1 to S6 arrive one by one; each pushes the oldest book out: E, F, G, C, A, B. Caption in red "the scan
made every key look recent, and pushed the popular ones out"; "read A: a miss". Then the lock caption.

NOTE: "That's not the shelf we wanted" is the understatement right after the failure; the lock is said plainly.

## Scene 4 · One-hit wonders · 1:40–2:03 · [WISH]

VO: How common are books read only once? A 2023 study looked at 6,594 recordings of the requests real caches received.

In the middle trace, 26 percent of keys were asked for once and never again. In a short stretch of a trace, 72 percent
were. So the evidence says: drop new keys quickly, unless they prove themselves.

SCREEN: Title "one-hit wonders: keys asked for once, never again"; captions with 6,594 traces, 26% and 72%; the wish
in yellow.

## Scene 5 · SIEVE · 2:03–2:51 · [NAME] [MAP] [PREDICT] [PAUSE] [SHOW] [LOOP-PAYOFF]

VO: SIEVE, from 2024, keeps the books in arrival order, and gives each one a sticky dot. A read puts a dot on the book,
and moves nothing.

To make room, a hand walks from the oldest book toward the newest. A book with a dot keeps its place, and loses its
dot. The first book without a dot goes.

In code, that dot is one visited bit per key.

Now run the scan. Pause and guess first: which books end up in the basement?

(three seconds)

The hand spares A, clears its dot, and drops E. It spares B and drops F. It spares C, and drops S1, the first scan
book. From then on, scan books push out scan books.

Books A, B and C are still on the shelf, and their next reads put the dots back.

SCREEN: The shelf resets to D, A, E, B, F, C. Reads of A, B and C put a green dot on each; nothing moves. S1 arrives;
the yellow hand appears over D, the oldest, which has no dot: D drops away, S1 enters at the newest end. Caption "the
dot = a visited bit; the hand = a pointer that walks the list". Countdown. S2: the hand moves to A, its dot vanishes,
then to E, which drops. S3: B spared, F drops. S4: C spared, S1 drops. S5 and S6: S2 and S3 drop. A, B and C remain;
their dots come back.

## Scene 6 · The lab's numbers · 2:51–3:31 · [SHOW] [PREDICT] [PAUSE]

VO: The lesson's lab races all three on a million requests with Zipf traffic, the skewed kind where a few keys get most of
the requests. The cache holds 10,000 keys, and we count misses, requests the cache can't answer.

SIEVE misses least: 21.6 percent, against 26.1 for LRU. Then the lab mixes in scans. Pause and guess the last column.

(three seconds)

FIFO rises to 32.2, and LRU to 29.0. SIEVE stays at 21.6. Scan keys arrive without a dot, so the hand drops them
before any key that was read.

SCREEN: The shelf steps aside. A table "miss ratio, cache of 10,000 keys": FIFO 29.8%, LRU 26.1%, SIEVE 21.6%;
countdown; the last column fills: 32.2% and 29.0% in red, 21.6% in green.

## Scene 7 · Limits, and the code · 3:31–4:02 · [GUARDRAIL] [SHOW]

VO: A few limits. With a cache of only 1,000 keys, the scans changed little for any policy. Every policy is a bet on the
past, and your traffic decides which bet wins. And throwing keys away is right for a cache, and wrong for data you
can't rebuild.

Here's the heart of the lab's SIEVE, in Java and Kotlin. A hit sets one bit. The hand clears bits until it finds a key
without one. Because a hit moves nothing, SIEVE ran at twice LRU's speed on 16 threads.

SCREEN: Captions for the limits. Java and Kotlin panels side by side: the hit line `visited = true` and the hand's
loop from the lab's `Sieve`. Caption "a hit moves nothing: twice LRU's speed on 16 threads (the SIEVE paper)".

## Scene 8 · The moral, and a check · 4:02–4:31 · [MORAL] [PREDICT] [PAUSE]

VO: So the moral of the story. LRU trusts the last read, so one scan can fool it. SIEVE asks a new key to prove itself
once before it may stay.

One quick check. The hand reaches B, and B has a dot. Where does B end up? Pause and think.

(three seconds)

Right where it was. It loses its dot and keeps its place. LRU would have moved it; SIEVE never moves anything.

SCREEN: The shelf returns as the scan left it: A, B, C, S4, S5, S6. The moral in two captions. B gets a dot and the
hand stops over it; countdown; the dot vanishes, B stays put (green outline), the hand moves on to C. Last caption
"drop new keys quickly, unless they prove themselves".

---

### Beat check

- Opens with QUESTION inside the lesson's library (scene 1). FAMILIAR + SHRINK + SHOW: FIFO, LRU, LFU on six books
  (scene 2).
- PREDICT with PAUSE, BREAK of LRU by a scan, understatement right after it, and the lock as a second PAIN
  (scene 3). Evidence and WISH (scene 4).
- NAME SIEVE with its MAP (dot = visited bit, hand = pointer), PREDICT with PAUSE, SHOW the scan, loop paid off
  (scene 5).
- SHOW the lab's numbers with a PREDICT (scene 6). GUARDRAIL and code last, Java and Kotlin side by side (scene 7).
  MORAL and a check with PAUSE (scene 8).

### Accuracy notes for the producer

- The miss ratios are the lab's `PolicyDemo` output (a million Zipf requests over 100,000 keys, a scan of 5,000 new
  keys after every 50,000 requests, only Zipf requests counted). At 1,000 slots: 53.5%, 49.3%, 40.0%.
- The six-book toy was traced by hand with the lab's `Sieve` code: the hand starts at the oldest key, spares and
  clears visited keys, evicts the first unvisited one, and resumes at the evicted key's newer neighbour; new keys
  enter at the newest end. LRU's trace uses `LinkedHashMap` in access order.
- "Twice LRU's speed on 16 threads" and "13 to 18% fewer misses on Zipf traffic" are the SIEVE paper's; the video
  quotes only the first. S3-FIFO (2023) is named only as the source of the one-hit-wonder counts.
- LFU's fading counts, ARC, W-TinyLFU and S3-FIFO's queues are left to the lesson. Redis's own sampled LRU and LFU
  are the next section's subject.
- Evicting is fine for a cache and wrong for data that can't be rebuilt, such as the lesson's payment notes (its
  closing).
