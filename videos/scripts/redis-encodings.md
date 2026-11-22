# One more shop, eight times the memory: how Redis lays out a key

- Slug / scene: `redis-encodings`, `videos/scenes/redis_encodings.py:RedisEncodings`
- Lesson: `cache-03`, section 1, "Small keys are packed into one block, big ones become a hash table or a skip list"
- Audience / level: a complete newcomer. Can read a little code; has heard of Java's HashMap; knows nothing about
  memory layout, pointers or Redis.
- Length: about 4:55 (~690 words of narration at Kokoro's ~150 words a minute with sentence gaps, one pause, silent
  builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=211` (the skip list and the dict built, the search for 41 done, "MEMORY USAGE: 10,813 bytes")
- The learner's real question: one more item made a key eight times bigger. Where did the bytes come from?
- Misconceptions to steelman and break: (1) "one more item costs a few more bytes" (broken by 1,305 → 10,813);
  (2) "a hash table is always the right structure" (broken by 35 bytes of data in 215 bytes); (3) "shrink the key and
  it shrinks back" (broken by ZREM: still a skip list, 10,741 bytes).
- Concept chain: pointers and headers outweigh small data → a listpack packs entries back to back → walking a short
  block is fast, a long one isn't → past the limit, a dict and a skip list (hardest last) → the type stays, the
  encoding changes → it never converts back
- Analogy family: the lesson's café owner. One notebook page for a hundred regulars (the listpack); a box of index
  cards (the dict) and a ranked list on the wall (the skip list) at a few thousand. Where it breaks: she can go back
  to one page; Redis never does, said out loud.
- Open loops: "where do the extra nine thousand bytes come from?" planted in scene 1 → paid off in scene 5
- Assumptions: numbers are the lesson's (35 bytes of data, 77 bytes as a listpack, 215 as a hash table; the stepper's
  `merchants:approved`: 68, 76, 1,305 at 128 members, 10,813 at 129, 10,741 after ZREM; limits 128 and 64 bytes for
  sorted sets, 512 for hashes). The grid of 32 squares stands for 128 members; the notebook's names are made up for
  the picture.

## The one picture

Top: the command just run (yellow, mono), and under it two readouts, OBJECT ENCODING (left) and MEMORY USAGE
(right). Middle: first the HashMap (grey slots, blue entries, white pieces with grey header stubs, yellow pointers),
then the listpack as a strip of cells packed edge to edge (members white, scores teal, hdr and end grey), then the
skip list (a head column, four member boxes, teal express-lane towers and links) above a blue dict bar. Gold marks
the café owner's world. Captions at the bottom.

## Scene 1 · The question · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: Redis is a program that keeps data in memory and answers requests over the network. It keeps each piece of data under
a name, called a key.

Here's one key: a ranked list of shops, 128 of them, in 1,305 bytes.

Add one more shop. Now it takes 10,813. One more item, eight times the memory. Where do the extra nine thousand bytes
come from? Hold that question.

SCREEN: Title card. "merchants:approved"; a grid of 32 teal squares, "a ranked list of shops: 128 members"; "MEMORY
USAGE: 1,305 bytes". One yellow square joins; the readout turns red, 10,813. Captions "one more item, eight times the
memory", "where do 9,000 extra bytes come from?".

## Scene 2 · Pointers and headers · 0:30–1:11 · [FAMILIAR] [PAIN] [WISH]

VO: Start with something familiar. Java's HashMap stores three fields of a payment like this: a table of slots, an entry
for each field, and a separate piece of memory for each name and each value.

Pointers join them, 8-byte addresses that say where the next piece lives. And every piece carries a small header.

The real data here, status approved, amount 1250, currency EUR, is 35 bytes. On the lab server, the whole thing took
215. The bookkeeping weighs more than the data.

Multiply by ten million payments, and much of your memory holds pointers. What if we dropped the structure?

SCREEN: A column of slots, three entries, six pieces (status, approved, amount, 1250, currency, EUR), arrows from
slot to entry to piece. The arrows turn yellow on "Pointers"; grey header stubs appear on every piece. "the data: 35
bytes" in green, "as a hash table: 215 bytes" in red. Caption "wanted: drop the structure".

## Scene 3 · The notebook page · 1:11–1:41 · [ANALOGY] [MAP] [NAME]

VO: Picture a café owner who keeps her regulars on one notebook page. With a hundred names, the page is perfect: one
sheet, and a finger finds anyone in seconds.

Redis does the same. It writes the entries one after another into one block of memory, each with its length in front,
and finds a field by reading from the start.

That block is called a listpack. The same three fields take 77 bytes as a listpack, against 215 as a hash table.

SCREEN: The HashMap fades. A gold notebook page with five names; a yellow finger slides down. Below, the strip
hdr | status | approved | amount | 1250 | currency | EUR | end builds left to right, a small length over each entry;
an outline walks from the start. "listpack: one block, no pointers", "77 bytes, not 215"; caption "the notebook
page = one block of memory, a listpack".

## Scene 4 · A sorted set in one block · 1:41–2:19 · [SHRINK] [SHOW]

VO: Now the ranked list of shops. Redis calls it a sorted set: each member has a score, and the members stay in score
order.

Three shops: a listpack of 68 bytes.

Add shop m-51 with score 41. Redis walks the block from the start until it passes 40, then moves every byte after that
point to make room.

That walk sounds slow. But a short block sits side by side in memory, and the CPU streams through it fast.

After 124 more shops, the key holds 128 members: still one block, 1,305 bytes.

SCREEN: `> ZADD merchants:approved 42 m-17 40 m-03 12 m-88`; the strip hdr | m-88 | 12 | m-03 | 40 | m-17 | 42 | end;
the scores glow in order. "OBJECT ENCODING: listpack", "MEMORY USAGE: 68 bytes". `> ZADD ... 41 m-51`: a yellow
outline walks to 40; the cells after it slide right (red), m-51 and 41 drop in; 76 bytes. An outline streams
along the whole strip. `ZCARD ... (integer) 128`: hdr | m-88 | 12 | m-03 | 40 | ... 125 more entries ... | end;
1,305 bytes.

## Scene 5 · The page breaks; the 129th shop · 2:19–3:33 · [BREAK] [PREDICT] [PAUSE] [SHOW] [NAME] [LOOP-PAYOFF]

VO: Where does the page break? At size. Walking ten thousand entries on every lookup, on the one thread every client
shares, is too slow. And adding in the middle means moving every byte after it.

So at a few thousand names, the owner switches to a box of index cards and a ranked list on the wall. Add the 129th
shop. What does Redis do? Pause and guess.

(three seconds)

Inside that one ZADD, Redis copies all 129 members into two new structures, and frees the block.

A hash table maps each member to its score, like the box of cards: any shop's score in one step.

And a skip list keeps the members in score order, like the ranked list on the wall. It's a chain where some items
carry extra links that jump far ahead, like express lanes.

Find shop m-51, score 41. Ride the top lane: 42 is too far, so drop a lane. 40 is fine, move right. 42 again is too
far, so drop again. And there it is.

Two structures, pointers everywhere, holding the same 129 members. That's where the bytes went: 10,813 of them.

SCREEN: Caption "where the page breaks: size"; the long cell turns red. `> ZADD merchants:approved 2 m-129`;
countdown. "OBJECT ENCODING: listpack → skiplist", "MEMORY USAGE: converting". The strip's cells slide down into the
dict bar and vanish; the skip list builds above it (head, m-88 12, m-03 40, m-51 41, m-17 42, ...; towers on m-03
and m-17; teal links on the upper lanes). Captions map dict = box of index cards, skip list = ranked list on the
wall. A yellow dot searches for 41: top lane, 42 flashes red, down, right to 40, 42 red again, down, right to
m-51 (green). "MEMORY USAGE: 10,813 bytes".

## Scene 6 · The name, and the limits · 3:33–3:50 · [NAME]

VO: The type didn't change. TYPE still says zset, a sorted set. What changed is the encoding, the layout behind the type,
and OBJECT ENCODING reports it.

A sorted set switches past 128 members, or when any one member is longer than 64 bytes. A hash switches past 512
fields.

SCREEN: `> TYPE merchants:approved   zset`; "OBJECT ENCODING: skiplist"; caption "encoding: the layout behind the
type"; then the two config lines for sorted sets, then for hashes.

## Scene 7 · It never goes back · 3:50–4:17 · [BREAK] [JOKE:is-the-explanation]

VO: Now remove the 129th shop. Back to 128. Does it go back to a listpack?

No. It stays a skip list, at 10,741 bytes. Here the notebook picture breaks. The owner can go back to one page when
her list shrinks. Redis keeps the card box forever, just in case.

To get the small form back, you rebuild the key.

SCREEN: `> ZREM merchants:approved m-129`; the "..." pulses. "skiplist (stays)" and 10,741 bytes, both red.
Captions "where the notebook picture breaks: Redis converts up, never down", "to shrink it again: rebuild the key".

NOTE: The card box kept "just in case" is the light moment, and it is the rule: conversion is one way.

## Scene 8 · Guardrail and moral · 4:17–4:35 · [GUARDRAIL] [MORAL]

VO: So if you'll have millions of a key, keep each one under the limits: few fields, short members.

The moral of the story: in memory, the bookkeeping around small items often weighs more than the items. Redis packs a
small key into one block, and pays for the big structure only when the key outgrows it.

SCREEN: Captions "millions of keys? keep each under the limits: few fields, short members", then the moral in
yellow.

## Scene 9 · A check · 4:35–4:55 · [PREDICT] [PAUSE]

VO: One quick check. A payment's hash grows to 600 fields. Listpack or hash table? Pause and think.

(three seconds)

Hash table. 600 is past the hash limit of 512, and it won't come back down.

SCREEN: The skip list dims. `> HLEN payment:43   (integer) 600`; countdown; "OBJECT ENCODING: hashtable", "600 >
512". Last caption "small keys are packed; big keys pay for pointers".

---

### Beat check

- Opens with QUESTION (scene 1). FAMILIAR (HashMap) + PAIN + WISH (scene 2).
- ANALOGY + MAP and the first NAME, listpack, after the picture (scene 3). SHRINK + SHOW on the stepper's key (scene 4).
- BREAK of the page at size, PREDICT with PAUSE, SHOW, NAME (dict, skip list) and the loop paid off (scene 5).
- NAME of the idea itself, encoding, only after both layouts are seen (scene 6).
- The analogy's break said out loud (scene 7). GUARDRAIL and MORAL (scene 8), a check with PAUSE (scene 9).
- Light moments: "Redis keeps the card box forever, just in case" (~4:00); no joke inside the walkthroughs.

### Accuracy notes for the producer

- 35, 77 and 215 bytes are the lesson's lab numbers for the three-field hash; 68, 76, 1,305, 10,813 and 10,741 are
  the stepper's for `merchants:approved`. The section's own Try it uses another key (`board`: 1,076 → 10,888,
  "about ten times"); the video keeps to one key, so it says "eight times".
- The HashMap drawing is schematic: slot count, entry layout and header sizes stand for the idea, not Java's exact
  object layout. The lengths over the listpack cells are the strings' lengths; a real listpack also stores each
  entry's total length at its end, so it can be walked backwards.
- "Walking is fast for a short block": O(N), cheap for N up to 128 because the bytes are contiguous (the lesson's
  wording).
- The skip list drawn has hand-picked levels; Redis picks each node's level at random. The video omits that each
  link also stores a span, which gives ranks.
- Hash limits: `hash-max-listpack-entries 512` and `-value 64`. Sets, intsets and lists have their own limits and
  layouts (the lesson's table); the video leaves them to the lesson.
- The check's `HLEN payment:43 ... 600` is an imagined state, built for the question; the answer follows from the
  512 limit.
