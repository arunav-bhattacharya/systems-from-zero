# A full page splits, and the tree grows at the top

- Slug / scene: `btree-split`, `videos/scenes/btree_split.py:BTreeSplit`
- Lesson: `store-04`, section 2, "A full page splits, and the tree grows at the top"
- Audience / level: a complete newcomer who has met sections 0 and 1: the library with a board by the door, floor
  signs and shelves; a B+tree whose root and internal nodes hold signposts and whose leaves hold every key; a search
  reads one page per level. Knows nothing about inserts.
- Length: 4:41 (~790 words of narration at the Kokoro voice's ~180 words a minute, plus a guess, a check and silent
  moves)
- Poster: `POSTER=157` (the three-level tree just after the new root: 70 over 30 50 and 90, five leaves)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: a page has a fixed size. What happens when a key has to go into a page that's
  already full? And how does the tree ever get taller?
- Misconception to steelman and break: "when a page is full, give it more room": a bigger page (pages have a fixed
  size) or an overflow page chained to it (keys pile into a chain that has to be read page by page, the slow search
  the tree exists to avoid).
- Concept chain: an insert is a search → the leaf is full → bigger page and overflow chain both fail → split the
  leaf, copy its first key up → the parent overflows → split it, push its middle key up → the root splits, so a new
  root grows on top → every leaf stays at the same depth → real pages: 407 keys, then 408 splits; 90% on the right
  edge, about two-thirds for random keys → the cost
- Analogy family: the lesson's library. The board by the door (the root), floor signs (internal nodes), shelves in
  order (leaves). A full shelf gets a new shelf to its right, and the floor sign gets a new line.
- Open loops: "how does the tree get taller?" planted in scene 1 → paid off in scene 6.
- Assumptions: the tree, the insert of 100 and every step are the lesson's stepper (order 4: at most 3 keys a node;
  root 30 50 70; leaves 10 20, 30 40, 50 60, 70 80 90). The PostgreSQL numbers are the lesson's Try it output (407
  keys in one leaf; key 408 splits it; leaves of 367 and 42 items; 767 and 1,038 leaf pages for 200,000 time-ordered
  and random UUIDs at about 90% and 67% full). The check (insert 85) is worked out from the stepper's final tree.

## The one picture

A tree on three levels of the frame. Top band (empty at first): where a new root will appear. Middle: the root, a
gold node "30 50 70". Bottom: four teal leaves. Each node is a row of key cells with grey pointer lines to its
children. The key being inserted is yellow; a node with one key too many turns red; a copied key is green, a pushed
key purple. The request chip sits at the top left; captions on one line at the bottom, with a band above them for
the real numbers.

## Scene 1 · An insert is a search · 0:00–0:40 · [FAMILIAR] [QUESTION] [LOOP-PLANT]

VO: Here's a small B+tree. Each node is one page, and in this toy a page holds at most three keys. The root's
signposts send each search to one leaf, and the leaves hold every key, in order.

Let's insert 100. An insert starts as a search. At the root, 100 isn't below 30, 50 or 70, so we follow the last
pointer, to the leaf 70, 80, 90.

But that leaf is full. Where does 100 go? And while we're at it: this tree has two levels. How would it ever get a
third?

SCREEN: The tree draws in. A yellow chip "insert(100)". The root's cells light one by one, then the last pointer and
the rightmost leaf glow.

## Scene 2 · More room? · 0:40–1:25 · [PAIN] [BREAK] [JOKE:amplify]

VO: 100 goes into the leaf in key order. Now the leaf has four keys, and a node may hold three. On a real page,
the new entry doesn't fit in 8 KB.

The first idea: make the page bigger. But pages have a fixed size. That's the whole point of pages.

The second idea: hang an extra page off the full leaf, an overflow page. Every key that lands there piles into the
chain, which has to be read page by page. That's the slow search we built the tree to escape. It's a full shelf
with a cardboard box next to it, then another box next to that.

SCREEN: 100 slides into the leaf, which turns red: "4 keys, a node holds 3". The leaf stretches; a red cross and
"a page has a fixed size". A dashed overflow box hangs below the leaf, then a second one; red cross.

## Scene 3 · The library · 1:25–2:00 · [ANALOGY] [MAP]

VO: Think of the library from the last section. The board by the door says which floor, a sign on each floor says
which shelf, and each shelf keeps its books in order. When a shelf is full, the librarian puts a new shelf right
next to it, moves the upper half of the books onto it, and adds one line to the floor sign: from here on, the new
shelf.

So the shelves are the leaves, the floor signs are the internal nodes, and the board by the door is the root.

SCREEN: Captions map each part; the leaves, the root and the empty top band glow in turn.

## Scene 4 · Split the leaf · 2:00–2:45 · [SHOW] [PREDICT] [PAUSE] [NAME]

VO: Let's do that to our leaf. A new leaf appears on its right, and the upper half, 90 and 100, moves into it. The
two leaves are linked, side by side.

Now the parent needs a pointer to the new leaf, and a signpost that says where it starts. Which key goes up, and
does it leave the leaf? Pause and guess.

(three seconds)

90, the new leaf's first key. And it's copied, not moved: 90 stays in the leaf, because the leaves must hold every
key. This is a split.

SCREEN: The red leaf splits into 70 80 and 90 100. Countdown. A green copy of 90 rises into the root, which becomes
30 50 70 90, with a new pointer to the new leaf. Caption "leaf split: 90 is copied up, and stays in the leaf".

## Scene 5 · The root overflows · 2:45–3:25 · [SHOW] [BREAK of the leaf rule]

VO: But now the root has four keys, one too many. So it splits too, with one difference. Its keys are only signposts,
so the middle key, 70, doesn't need to stay below. It's pushed up, and it leaves both halves. 30 and 50 keep three
children. 90 keeps two.

And the node that split was the root, so 70 has nowhere to go. A new root is made above it, with one key and two
children.

SCREEN: The root turns red. It splits into "30 50" (left) and "90" (right), with their pointers; 70 rises purple
into the empty top band and becomes the new root, with two pointers down. Caption "internal split: 70 is pushed up,
and stays in neither half".

## Scene 6 · Growing at the top · 3:25–4:00 · [LOOP-PAYOFF] [BREAK of the analogy] [JOKE:is-the-explanation]

VO: That's the only way a B+tree gets taller: at the top, never at the bottom. So every leaf is always at the same
depth, and every search reads the same number of pages. A search for 60 now reads three: the root says below 70,
the next node says at least 50, and the leaf holds it.

Here the library picture breaks. A library grows at its edges, with a new wing. This tree grows by putting a new
sign above the board at the door, so every shelf stays the same number of signs from the entrance.

SCREEN: A yellow path for get(60): root, "30 50", leaf "50 60", with "3 page reads". Caption "a library adds a wing;
a B+tree adds a sign above the door".

## Scene 7 · Real pages · 4:00–4:40 · [SHOW] [GUARDRAIL]

VO: On a real PostgreSQL page, a leaf holds 407 of these entries. In the Try it, keys 1 to 407 fit in one leaf, which
is also the root. Key 408 splits it, and the tree grows a level: a new root on top, one leaf with 367 entries, and a
new leaf with 42.

Why so uneven? The leaf that split was the rightmost one. When every new key is bigger than the last, PostgreSQL keeps
the left page 90% full, because nothing will land there again.

SCREEN: Band lines: "PostgreSQL: 407 entries fit in one leaf", "key 408: a new root above leaves of 367 and 42
entries", "rightmost leaf: left page kept 90% full".

## Scene 8 · What your keys cost · 4:40–5:20 · [GUARDRAIL]

VO: So the kind of key decides how full your pages are. Random keys split pages in the middle, and pages settle about
two-thirds full. In the Try it, 200,000 random ids took 1,038 leaf pages. 200,000 time-ordered ids, each bigger than
the last, took 767. That's a third more pages for the same rows. And each split writes three pages, the old leaf,
the new leaf and the parent, and logs every change first.

SCREEN: Two bars: "time-ordered ids (uuidv7): 767 leaf pages, about 90% full" (green) and "random ids
(gen_random_uuid): 1,038 leaf pages, about 67% full" (red).

## Scene 9 · The moral, and a check · 5:20–5:55 · [MORAL] [PREDICT] [PAUSE]

VO: So: a full leaf splits and copies its first key up. A full internal node splits and pushes its middle key up.
And when the root splits, the tree grows at the top.

One quick check. Insert 85 into the new tree. Does anything split? Pause and think.

(three seconds)

No. The root sends 85 right, the node 90 sends it left, and the leaf 70, 80 has room. One page changes.

SCREEN: Moral caption. Chip "insert(85)"; countdown; a yellow path root → "90" → leaf "70 80", which becomes
"70 80 85" in green.

---

### Beat check

- FAMILIAR (the tree from section 1) and QUESTION first (scene 1), with the open loop "how does it get taller?".
- BREAK of two obvious fixes (scene 2), before the analogy.
- ANALOGY + MAP (scene 3), before the name "split".
- PREDICT with PAUSE (scene 4, and the check in scene 9); SHOW right after.
- NAME (split, copied up, pushed up) after each move is seen (scenes 4, 5). The analogy's breaking point used
  (scene 6). GUARDRAIL with the real numbers and the cost (scenes 7, 8). MORAL last.
- Light moments: the cardboard boxes next to a full shelf (~1:20), a new sign above the door (~3:55).

### Accuracy notes for the producer

- The tree and every step of insert(100) are the lesson's stepper; search(60) reading three pages is its last
  frame.
- PostgreSQL numbers are the lesson's Try it: 407 keys in one leaf (page 1, level 0); key 408 makes root page 3 at
  level 1 over leaf 1 (367 live items: 366 keys plus the high key 367) and leaf 2 (42 keys); rightmost-leaf splits
  keep the left page 90% full (the B-tree's default fillfactor); 200,000 UUIDs: `uuidv7` 767 leaf pages at 89.91%,
  `gen_random_uuid` 1,038 at 66.52% (another run gave 1,083 at 63.77%). "367 entries" in the narration counts the
  high key, as the Try it's `live_items` does.
- "Each split writes three pages and logs every change first" is the lesson's last paragraph (old leaf, new leaf,
  parent; the WAL).
- check_audio: 97.7% at -16.2 LUFS; the differences are Whisper spellings (plus for B+tree, sign post, postgres,
  kilobytes, "triate" for "Try it") and small function words.
- The check: root 70 sends 85 right; node 90 sends 85 to its first child, leaf 70 80; three keys fit in a node.
