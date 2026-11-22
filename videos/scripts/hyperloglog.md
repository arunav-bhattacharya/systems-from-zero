# Counting cards without a list: a HyperLogLog in 12 KB

- Slug / scene: `hyperloglog`, `videos/scenes/hyperloglog.py:Hyperloglog`
- Lesson: `cache-04`, section 1, "Counting different cards in 12 KB with a HyperLogLog"
- Audience / level: a complete newcomer. Can read a little code; knows nothing about hashes, bits or Redis.
- Length: 5:05 (~800 words of narration at Kokoro's ~150 words a minute with sentence gaps, two pauses, silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=169` (the register row after card:C: register 3 at 4, register 5 at 1, the hash line above)
- The learner's real question: how can you count how many different cards paid without keeping a list of them?
- Misconceptions to steelman and break: (1) "a count needs a list, because exact feels safe" (broken by 4.4 MB for
  100,000 cards against 14 KB, off by 1.06%); (2) "just INCR on every payment" (counts the regular three times);
  (3) "one record is enough" (one lucky card with 20 zeros says a million).
- Concept chain: an exact distinct count needs memory that grows → the longest run of tails estimates a crowd → a
  hash is a coin that gives the same flips for the same card, so repeats are free → many registers, picked by a few
  bits, averaged (hardest last) → HyperLogLog: 16,384 registers of 6 bits, 12 KB, 0.81% → it only counts
- Analogy family: the lesson's fair. Each visitor flips a coin until heads; you keep only the longest run of tails.
  Where it breaks, in our favor: a visitor who flips again gets a new run; a card that pays again gets the same one.
- Open loops: "can you count without the list?" planted in scene 1 → paid off in scene 7 (14,364 bytes, 1.06% off)
- Assumptions: numbers are the lesson's (4.4 MB and 4,361,843 bytes for 100,000 cards in a set; 101,058 from
  PFCOUNT, 1.06% high; STRLEN 12,304, MEMORY USAGE 14,364; 16,384 registers, 14 bits, 50 bits, rank at most 51, 6
  bits, 12,288 bytes; 0.81%; 10 tails about once in 1,024; the stepper's toy hashes for card:A, card:B and card:C and
  its eight registers after many cards: 3 2 5 1 4 3 2 3). The café's five payments (card 7 three times, cards 9 and
  3) and the hash `...1011 0100` in scene 4 are made up for the picture; the coin flips at the fair are made up.

## The one picture

First the café (gold) feeding a blue "cards seen" box; then the fair: six gold visitors with their flips under them
and a yellow board with the longest run. Then the toy HyperLogLog: a hash line at the top (rest of the bits in
white, the index bits in yellow, notes under each), a row of eight teal registers r0 to r7 in the middle, and a note
line under them for what PFADD returned. At the end, two bars to scale: the set (red, long) and the HyperLogLog
(teal, a sliver). The command just run sits at the top in yellow; captions along the bottom.

## Scene 1 · The question · 0:00–0:40 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: Picture a café owner who wants one new number on her screen: how many different cards paid at her café today. A
regular who buys three coffees counts once.

The company keeps numbers like this in Redis, a program that holds data in memory and answers commands from other
programs. The obvious answer is a list of every card that paid. It's exact, and tiny for one café.

But there are 20,000 shops, counted every hour. And the list grows with every new card: 100,000 cards took about 4.4
MB. Can you count without the list? Hold that question.

SCREEN: Title card. The café box; five card chips fly into "cards seen", which lists card 7, card 9, card 3;
"different cards: 3". Captions "20,000 shops, every hour", "a set of 100,000 cards: about 4.4 MB" (the box turns
red), "can you count without the list?".

## Scene 2 · Counting payments, not cards · 0:40–1:01 · [PAIN] [BREAK] [WISH]

VO: Try the simplest counter: INCR, add one, on every payment. It counts payments, not cards. The regular counts three
times.

To skip the repeats, you must remember which cards you've seen. That's the list again. An exact count of different
things needs memory that grows with the count.

So let's give up a little exactness.

SCREEN: "INCR on every payment: 5" in red; caption "card 7 counted three times: 5, not 3". The list comes back;
"an exact count of different things: memory that grows with the count"; the wish in yellow.

## Scene 3 · The fair · 1:01–1:30 · [ANALOGY] [JOKE:is-the-explanation]

VO: Picture a fair, where you want to know how many people came, without writing down a single name.

You ask each visitor to flip a coin until it lands heads, and to tell you how many tails came first. You keep one
number: the longest run of tails anyone has reported.

A run of 10 tails turns up about once in 1,024 tries. So if your record is 10, about a thousand people have probably
come.

It's the laziest head count ever taken, and it works.

SCREEN: Six gold visitors; their flips appear under them (H, T H, H, T T T H, T H, H). The board "longest run of
tails": 0, then 1, then 3 as those visitors are outlined. Then 10, "a run of 10 tails: about once in 1,024 tries",
"record 10: about a thousand people".

NOTE: The lazy head count is the light moment, and it is the method: nobody's name is kept.

## Scene 4 · The hash is the coin · 1:30–1:50 · [MAP] [NAME]

VO: In code, the coin flips come from a hash function. It turns any text into a number that looks random, and the same
text always gives the same number.

Read its bits from the right. A 0 is a tail, a 1 is heads. Count the zeros before the first 1, and add one. That's the
hash's rank.

A rank of r turns up about once in 2 to the power r different cards.

SCREEN: Caption "the coin = a hash function". `hash("card:A") = ...1011 0100` under the fair; outlined from the
right; "two zeros, then a 1: rank 3"; "rank = the zeros before the first 1, plus one"; "rank r: about once in 2 to the
r different cards".

## Scene 5 · Repeats are free · 1:50–2:13 · [PREDICT] [PAUSE] [ANALOGY breaks]

VO: Now the regular pays again. Does her card push the record up? Pause and guess.

(three seconds)

No. A visitor who flips again gets a new run. A card that pays again has the same hash, so the same rank. Here the
fair picture breaks, in our favor: repeats are free.

SCREEN: Countdown. The hash line glows green; "same card, same hash, same rank: the record can't move"; "where the
fair picture breaks, in our favor: repeats are free".

## Scene 6 · Many records · 2:13–3:07 · [BREAK] [SHRINK] [SHOW]

VO: One record is a wild guess, though. A single lucky card with 20 zeros would make you believe in a million cards.

So keep many records. Split the cards into groups by a few bits of their hash, and keep the highest rank in each
group.

Card:A. Its lowest three bits, 0 1 1, pick register 3. The rest ends in one zero, then a 1: rank 2.

Card:B lands in register 5, rank 1. Half of all hashes look like that.

Card:C also lands in register 3, with three zeros: rank 4. The register keeps the larger, so 4.

And card:A pays again: same register, rank 2, and 2 isn't above 4. Nothing changes.

After thousands of cards, each register holds the longest run it saw. A kind of average combines them, one that stops
a lucky register from pulling the answer too far.

SCREEN: The board jumps to 20 and turns red: "one lucky card, 20 zeros: a million cards". The fair fades; eight
registers r0 to r7 at 0. Each PFADD from the stepper: `hash(card:A) = 10110 011`, "index 011 = r3", "rest: one 0,
then a 1: rank 2", r3 becomes 2, "PFADD returns 1"; card:B to r5 at 1; card:C to r3 at 4; card:A again, "PFADD
returns 0". Then `PFCOUNT visitors` and the registers 3 2 5 1 4 3 2 3; "the estimate: a careful average of all the
registers".

## Scene 7 · The name, and the real numbers · 3:07–4:14 · [NAME] [SHOW] [LOOP-PAYOFF]

VO: Redis does this with 16,384 registers. Fourteen bits of the hash pick the register. A rank fits in 6 bits, so all the
registers take 12,288 bytes.

That structure is a HyperLogLog. It takes at most 12 KB, and its standard error is 0.81 percent: about two times in
three, the estimate is within 0.81 percent of the truth, for a thousand cards or a billion.

The commands start with PF, for Philippe Flajolet, who invented the method. PFADD adds cards, and PFCOUNT gives the
estimate.

On the lab server, 100,000 cards went into a set and into a HyperLogLog. The set says exactly 100,000. The HyperLogLog
says 101,058: 1.06 percent too high.

And the memory? The set takes 4,361,843 bytes. The HyperLogLog takes 14,364, about 300 times less.

SCREEN: "16,384 registers x 6 bits = 12,288 bytes"; "64-bit hash: 14 bits pick the register, 50 bits give the rank";
"HyperLogLog" in teal; "standard error 0.81%...". `PFADD key card ...  PFCOUNT key`. The registers give way to two
bars: "set: SCARD 100000, 4,361,843 bytes" grows across the frame in red; "HyperLogLog: PFCOUNT 101058, 14,364
bytes" is a sliver; "about 300 times less memory, off by about 1%".

## Scene 8 · Guardrails · 4:14–4:40 · [GUARDRAIL]

VO: In exchange, it can't list the cards it has seen, and it can't say whether one card is among them. It only counts. So
use it when one percent either way is fine.

One more gift. PFMERGE keeps the larger value of each register, so 24 hourly counters merge into one for the day, and
a card that paid in two hours still counts once.

SCREEN: "it can't list the cards, or say if one card is in: it only counts"; "use it when 1% either way is fine";
`PFMERGE day hour:00 hour:01 ... hour:23`; "each register: the larger of the two, so a repeat still counts once".

## Scene 9 · The moral, and a check · 4:40–5:05 · [MORAL] [PREDICT] [PAUSE]

VO: So the moral of the story: you don't need a list to count. Keep the longest runs, and the count comes out of them, in
12 KB, whatever the crowd.

One quick check. The owner asks: did card:A pay today? Can the HyperLogLog answer? Pause and think.

(three seconds)

No. It kept only the longest runs, never the cards. It can count them, but it can't name one.

SCREEN: The moral in yellow. `> did card:A pay today?`; countdown; "no: it keeps runs, not cards". Last caption "a
HyperLogLog: count different things in 12 KB, about 1% off".

---

### Beat check

- Opens with QUESTION on the café (scene 1); FAMILIAR (a list) and its PAIN; BREAK of INCR and the WISH (scene 2).
- ANALOGY (scene 3) and MAP (scene 4: coin = hash, run = rank); NAME of rank after the picture.
- PREDICT with PAUSE (scene 5), and the analogy's break said out loud. BREAK of "one record" and SHOW on the
  stepper's toy (scene 6). NAME HyperLogLog only after the mechanism (scene 7), with the loop paid off.
- GUARDRAIL (scene 8), MORAL and a check with PAUSE (scene 9). Light moment: the laziest head count (scene 3).
- No code on screen: the lesson's section works at the redis-cli prompt, so the video shows its commands.

### Accuracy notes for the producer

- Ranks: Redis reads the 50 bits above the 14 index bits from the low end and counts trailing zeros plus one; the
  video's "read from the right" is that. The fair's tails map to zeros, heads to the 1.
- "A kind of average" is the harmonic-mean formula with bias corrections; the video doesn't show the formula.
- 0.81% is the standard error (1.04 / √16384): about two times in three within it, as the lesson says. The lab's run
  was 1.06% high, inside what that allows.
- 12 KB is the full (dense) form; small HyperLogLogs start sparse (27 bytes for three cards in the Try it).
- STRLEN 12,304 = 12,288 bytes of registers plus a 16-byte header; MEMORY USAGE 14,364 counts Redis's own overhead.
- The bars are to scale (4,361,843 against 14,364); the HyperLogLog's bar is drawn at its scaled width.
- PFMERGE gives exactly the HyperLogLog of the union, so a card in two hours counts once (the stepper's last frame).
