# One bad row in fifty million: a tree of hashes finds it

- Slug / scene: `merkle-audit`, `videos/scenes/merkle_audit.py:MerkleAudit`
- Lesson: `derive-05`, section 2, "A tree of hashes finds the drift without comparing every row"
- Audience / level: a complete newcomer. Knows from the lesson's opening that a café owner was paid 12.40 too little
  while every program said success; knows nothing about hashes, warehouses or trees of hashes.
- Length: 4:57 (~760 words of narration plus two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=197` (the walk done: root, right child, c88e and r6 red, matches green, the rest dimmed,
  "found: r6", "comparisons: 7")
- The learner's real question: the live balances and the rebuilt balances sit on different machines, 50 million rows
  each. How do you find the one that differs without sending them all across the network?
- Misconception to steelman and break: (1) "one hash of each whole view is enough", broken because it says something
  differs but not where; (2) "the tree always wins, and more ranges are always better", broken by the lab's 100 bad
  accounts in 256 ranges: 369 comparisons, more than a 256-range scan.
- Concept chain: row-by-row comparison is too costly → a hash is a short fingerprint of data → one hash says whether,
  not where → hashes of ranges, then hashes of hashes, up to a root (Merkle tree) → walk down only where the hashes
  differ: 1 + 2 per level → the cost follows the number of bad ranges, so it stops paying when most ranges differ
  (hardest last)
- Analogy family: two libraries in different cities checking over the phone that they hold the same books. Reading
  every page aloud is the row-by-row check; asking "the whole library? the east wing? this room? this shelf?" is the
  walk; a flooded library is the case where shelf by shelf no longer pays. One extra image at the break: a smoke
  alarm that won't say which room.
- Open loops: "how do you find it without sending fifty million rows?" planted in scene 1 → answered in scene 7 and
  the moral; "where?" planted in scene 4 → paid off by the walk.
- Assumptions: all numbers are the lesson's (50 million rows; SHA-256, 32 bytes; 8 ranges; 7 comparisons; 1,024
  ranges, 21 comparisons, about a thousandth of the rows; lab: 17, 101, 369 comparisons for 1, 10, 100 bad accounts
  in 256 ranges). The four-character hash values are made up stand-ins for 32-byte SHA-256 hashes; which range is bad
  (r6) follows the lesson's stepper.

## The one picture

Top: two stores, the live view (blue, left) and the rebuilt view (gold, right), joined first by a dashed network
line. Below, the tree: the root at the top, two children, four, then eight leaves over a bar of eight ranges r0 to r7.
Every node shows two short hashes: live on top in blue, rebuilt below in gold. Green outline means the two match,
red means they differ; a matching node's subtree is dimmed. A footer line on the left and a comparison counter on
the right.

## Scene 1 · The question · 0:00–0:35 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: Picture a café owner who was paid 12.40 too little, while every program reported success. One way to catch that:
work the balances out again from the log, the list of every payment, and compare them with the live ones, account by
account. Now make it real. The live view has 50 million rows, in the database that serves the app. The rebuilt view
sits in the warehouse, a separate database kept for analysis, on other machines. Somewhere one balance is off. How
do you find it without sending fifty million rows across the network? Hold that question.

SCREEN: Title card. Caption "paid 12.40 too little; every program said success". The live view and rebuilt view
boxes fade in, then the dashed network line between them.

## Scene 2 · Row by row · 0:35–1:00 · [PAIN] [JOKE:amplify] [WISH]

VO: The plain way is row by row. Every check sends all fifty million rows across, to find one bad balance. That's two
libraries checking they hold the same books by reading every page to each other over the phone. Bring snacks. What
we want is a fingerprint for data: something short that the two sides can compare instead.

SCREEN: A red counter "rows sent" runs to 50,000,000 while red dots stream along the network line. Caption "wanted: a
short fingerprint to compare instead".

## Scene 3 · A fingerprint · 1:00–1:30 · [NAME] [SHOW]

VO: There's a tool for that, called a hash function. SHA-256 is a widely used one. It turns any amount of data into a
short number of a fixed size, 32 bytes, called its hash. The same data always gives the same hash. Change even one
bit, and the hash comes out different.

SCREEN: A stack of rows, an arrow into a "hash function, SHA-256" box, an arrow out to "9e41..." with "32 bytes". The
same rows again give 9e41 again; one row turns red ("one bit flipped") and the hash becomes 52c7 in gold.

## Scene 4 · One hash for everything · 1:30–1:55 · [BREAK] [JOKE:is-the-explanation] [LOOP-PLANT]

VO: So, the obvious plan. Each side hashes its whole view and sends one hash. They differ. Good, something's wrong.
Where? One hash can't say. It's a smoke alarm that won't tell you which room. We're back to fifty million rows.

SCREEN: The demo leaves. One node at the top: live 9e41 (blue), rebuilt 52c7 (gold), outlined red. Caption "something
differs. where?".

## Scene 5 · The librarians · 1:55–2:35 · [ANALOGY] [MAP]

VO: Back to the two libraries on the phone. A smarter pair asks: is the whole library the same? No. The east wing?
Same, so skip it. The west wing? Different. Then its rooms, then their shelves, until they're down to one shelf. Only
then do they read books aloud, from that one shelf.

Let's map it. The library is the view. A shelf is a range of keys. A shelf's fingerprint is the hash of everything on
it. A room's fingerprint is a hash of its shelves' fingerprints, and so on up. The phone line is the network.

SCREEN: The phone conversation as four lines in the middle: "the whole library the same? no", "the east wing? same:
skip it", "the west wing? different", "its rooms... its shelves... one shelf". Then mapping captions one at a time.

## Scene 6 · Build the tree · 2:35–3:10 · [SHRINK] [SHOW] [NAME]

VO: Let's build it small. Each side cuts its keys into 8 ranges. A key's range comes from a hash of the key, so the
ranges come out even. Each leaf is the hash of every entry in its range, in key order. Live on top, in blue. Rebuilt
underneath, in gold. Above them, each parent is the hash of its two children, level by level, up to a single root.
That's a Merkle tree. Each side builds its own, where its data lives.

SCREEN: The bar of eight ranges r0 to r7, then eight leaves, then the levels above ("rooms", "wings" in grey in the
gaps), joined up to the root that was already there. Footer "50 million rows, 8 ranges, cut by a hash of the key".

## Scene 7 · Walk down · 3:10–4:00 · [PREDICT] [PAUSE] [SHOW] [LOOP-PAYOFF]

VO: One balance is off by a flipped bit. How many comparisons to find its range among the eight? Pause and guess.

(three seconds)

Compare the roots. They differ. One comparison. Compare the root's two children. The left one matches, so the first
four ranges are the same, and nothing below it needs a look. The right one differs. Three. Under it, left matches,
right differs. Five. At the bottom, range six differs and range seven matches. Seven comparisons, and only hashes
crossed the network.

Now, and only now, compare rows, only inside range six: an eighth of the keys.

SCREEN: Countdown. Nodes turn red or green pair by pair; a matching node's subtree dims; the counter reads 1, 3, 5, 7.
"found: r6". Footer "rows compared: range r6 only, an eighth of the keys"; a red dot runs along r6.

## Scene 8 · Scale it up · 4:00–4:25 · [SHOW]

VO: Each level costs two comparisons. So with 1,024 ranges, ten levels deep, it's one plus two times ten: 21
comparisons, instead of 1,024 ranges, or fifty million rows. And it leaves about a thousandth of the rows to compare.

SCREEN: The red path glows level by level. Chip "1,024 ranges: 1 + 2 x 10 = 21 comparisons, then about a thousandth
of the rows".

## Scene 9 · When the tree stops paying · 4:25–5:05 · [BREAK] [GUARDRAIL] [JOKE:soften]

VO: So more ranges are always better, and the tree always wins? Let's be fair. The cost grows with the number of bad
ranges, not the size of the view. In the lesson's lab, with 256 ranges, one bad account took 17 comparisons. Ten took
101. A hundred took 369: more than the 256 ranges a plain scan would compare.

When most ranges differ, a plain scan is cheaper. And then you don't have a hundred small bugs. You have one big one,
and a few ranges are enough to find it. If the whole library is flooded, nobody checks it shelf by shelf.

Could two different ranges share a hash by chance? With SHA-256, the odds are far too small to worry about.

SCREEN: A small table on the right of the footer area: "bad accounts / comparisons (256 ranges)": 1 → 17, 10 → 101,
100 → 369 (red), "a plain scan: 256". Every range pulses grey on "a plain scan".

## Scene 10 · The moral, and a check · 5:05–5:35 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So, how do you find one bad row in fifty million? Exchange hashes, not rows, and go down only where they differ.
Git, which keeps a project's code history, uses the same kind of tree.

One quick check. The two roots match. How many more comparisons do you need? Pause and think.

(three seconds)

None. Equal roots mean equal views. The audit is done after one comparison.

SCREEN: Caption "exchange hashes, not rows; go down only where they differ". For the check, the root shows 9e41 on
both sides, green; countdown; "comparisons: 1", "equal roots, equal views".

---

### Beat check

- Opens with QUESTION (scene 1) from the lesson's café owner; FAMILIAR is the rebuild-and-compare audit.
- PAIN + WISH (scene 2), the name hash right after the wish (scene 3), then the obvious fix and its BREAK (scene 4).
- ANALOGY + MAP (scene 5) before the tree is drawn or named; NAME "Merkle tree" after the build (scene 6).
- PREDICT with PAUSE (scenes 7 and 10), SHOW right after each.
- Second BREAK and GUARDRAIL (scene 9): the lab's 369 > 256, and hash collisions. MORAL last (scene 10).
- Light moments: bring snacks (0:50), the smoke alarm (1:45), the flooded library (4:55).

### Accuracy notes for the producer

- Hash values on screen are four-character stand-ins; SHA-256 hashes are 32 bytes. The lesson's stepper names the
  nodes n2, n3, n6, n7; the video says "left" and "right" instead.
- 50 million rows, 8 ranges, 7 comparisons, 1,024 ranges and 21 comparisons, and "about a thousandth of the rows" are
  the lesson's. The lab figures (17, 101, 369 for 1, 10 and 100 bad accounts in 256 ranges) are from the lesson's
  demo output.
- "A key's range comes from a hash of the key" follows the lesson; the video doesn't show the key hashing.
- Cassandra, the 4,096-range column and the "ranges found" column are left to the lesson. Git is named once with a
  plain sentence; the lesson lists it among Merkle tree users.
- Collisions: the lesson's aside says 2^256 possible values and that no SHA-256 collision has been published; the
  video says only that the odds are far too small to worry about.
- "12.40" is spoken "twelve forty", "SHA-256" "shah two fifty six" and "1,024" "one thousand and twenty four" through
  `SAY` rules.
