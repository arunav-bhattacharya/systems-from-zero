# 17 pages instead of 23,818: how an index finds one card's payments

- Slug / scene: `index-scan`, `videos/scenes/index_scan.py:IndexScan`
- Lesson: `store-07`, section 0, "One card's payments: every page of the table, or 17 pages through an index"
- Audience / level: a complete newcomer. Has used a book's index; doesn't know what a page, a sequential scan, a row
  address or a B+tree is.
- Length: 4:41 (~760 words of narration at Kokoro's ~175 words a minute, plus two pauses and silent builds)
- Poster: `POSTER=212` (the walk done: root, inner page and leaf lit, 14 green pages, "3 index pages + 14 table pages = 17")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: the table has a million payments and support wants one card's 14. How much does the
  database have to read to find them, and what does an index change?
- Misconception to steelman and break: (1) "why not keep the table itself sorted by card number?", broken by one order
  for three kinds of question and rows shuffled on every insert (the lesson's aside); (2) "an index helps any query on
  this table", broken by the cookbook's quick dinner and the one-shop check.
- Concept chain: a table is pages of rows in arrival order → without help, a sequential scan reads every page → an
  index is a sorted copy of card numbers with row addresses → its leaves get inner pages and a root on top, a B+tree
  → one walk down plus the rows' pages: 17 instead of 23,818 → only for questions about its own order (hardest last)
- Analogy family: the lesson's cookbook. Six hundred pages; lemons found through the index at the back in six page
  numbers; a recipe under 20 minutes that the index can't find; letter headings for the tree's upper levels.
- Open loops: "how much does it read to find 14 rows?" planted in scene 1 → scene 3 (23,818) and scene 7 (17); "keep
  the quick dinner in your pocket" planted in scene 2 → scene 8 and the check.
- Assumptions: all numbers are the lesson's (1,000,478 payments, 23,818 pages, 186 MB; 3 processes, 333,488 rows
  removed each, about 250 ms; ctid (339,35); 1,130 leaves, 4 inner pages, 1 root, about 283 leaves per inner page;
  3 + 14 = 17 pages, 0.25 ms; 1,136 pages and 9 MB for the index). The grid of 240 squares is a picture of the table
  (each square about 100 pages); which squares hold card 4242's rows, the six lemon pages and the "garlic"/"mint"
  index lines are made up for the picture.

## The one picture

Right: the table as a grid of 240 blue squares (later "each square: about 100 pages of 8 KB"); card 4242's 14 rows
in green; read pages grey. Left: first the cookbook's index card (gold), then the index (teal): 10 drawn leaves
("1,130 leaves"), 4 inner pages and a root, with a callout under the leaves showing the sorted entries around 4242.
A yellow query chip top left; one counter line under everything ("pages read: ..."); captions at the bottom. Yellow
marks the walk, red a cost, purple the wrong idea.

## Scene 1 · The question · 0:00–0:21 · [QUESTION] [LOOP-PLANT]

VO: A customer calls support about a coffee. The support screen asks the database for every payment made with card
4242. The table holds about a million payments, and 14 of them are this card's. How much does the database have to
read to find those 14? Hold that question.

SCREEN: Title card. Chip "card 4242: every payment"; the grid fades in, "payments: about a million"; 14 squares turn
green; a "?".

## Scene 2 · The cookbook · 0:21–0:45 · [FAMILIAR] [ANALOGY] [LOOP-PLANT]

VO: Start with a cookbook of six hundred pages. Which recipes use lemons? You could turn every page and look. Or you
could open the index at the back, find lemon, and read off six page numbers. Now ask the same book for every recipe
that takes under 20 minutes. The index is no help at all. It's sorted by ingredient, and cooking time isn't in it.
Keep that one in your pocket.

SCREEN: The grid turns gold, "a cookbook: 600 pages"; a flicker runs over every square. The index card (garlic,
lemon: 6 pages, mint); lemon turns yellow and six dots run to six squares. "under 20 minutes?" and a red cross on the
card; caption "sorted by ingredient: cooking time isn't in it".

## Scene 3 · Every page · 0:45–1:45 · [SHOW] [NAME] [PAIN] [JOKE:amplify] [WISH]

VO: A database table is a book too. PostgreSQL, a free database program, keeps it in pages of 8 KB, the block it
reads at a time. This table holds 1,000,478 payments in 23,818 pages. Each new row goes wherever there's room, in no
particular order. So card 4242's 14 payments are spread across the file. With nothing else to go on, there's one way
to find them: read every page, and test every row. That's called a sequential scan. PostgreSQL's report of the run
says three processes shared the work, and each threw away 333,488 rows. That's 23,818 pages for 14 rows, in a quarter
of a second. And the cost grows with the table. It's reading the whole cookbook every time someone wants lemonade.
What we want is the cookbook's trick: a list at the back that jumps straight to the right pages.

SCREEN: The grid turns blue, "payments: 1,000,478 rows in 23,818 pages", "each square: about 100 pages of 8 KB". The
14 green squares pulse. A yellow bar sweeps the rows; every other square turns grey; "pages read: 23,818". Captions
quote the plan (`Parallel Seq Scan on payments (... loops=3)`, `Rows Removed by Filter: 333488`).

NOTE: The lemonade line is the light moment; it restates the cost (every query pays for every page).

## Scene 4 · Why not sort the table? · 1:45–2:08 · [BREAK]

VO: First, the obvious idea: why not keep the table itself sorted by card number? Because a table can be in only one
order, and support asks by card, by shop and by date. Keeping it sorted would also mean moving rows to make room
whenever a payment lands in the middle. So PostgreSQL leaves the table in arrival order, and builds a separate sorted
copy.

SCREEN: Purple caption; chips "by card", "by shop", "by date", "a table has one order". Then "keep the table in
arrival order; build a sorted copy".

## Scene 5 · The index, and a row's address · 2:08–2:34 · [ANALOGY] [MAP] [NAME]

VO: That copy is the index. The cookbook's index lists every ingredient in order, with its pages. Ours lists every
card number in order, with the address of each of its rows. A row's address is its page and its slot on that page.
Card 4242's first payment is at 339, 35: row 35 on page 339. PostgreSQL calls this address a ctid.

SCREEN: Caption `CREATE INDEX payments_card_idx ON payments (card_id)`. Ten teal leaves, "1,130 leaves"; a callout
"... 4241: ...   4242: (339,35) and 13 more   4243: ...". A dot runs to one green square; "(339,35) = page 339, row
35".

## Scene 6 · The tree · 2:34–3:08 · [SHOW] [NAME]

VO: A million sorted card numbers still fill 1,130 pages, called leaves. That's still a lot to search. So above every
283 or so leaves, PostgreSQL adds an inner page that says which card number each leaf starts with, and one root page
above those. A big book's index does the same with letter headings: you find L before you look for lemon. The result
is a B+tree, a tree of pages where each level narrows the search: one root, 4 inner pages and 1,130 leaves.

SCREEN: The leaves pulse; 4 inner pages and their links appear, then the root. Caption "B+tree: 1 root, 4 inner pages,
1,130 leaves"; each level pulses as it's named.

## Scene 7 · Predict, then walk · 3:08–3:41 · [PREDICT] [PAUSE] [SHOW] [LOOP-PAYOFF] [JOKE:reward]

VO: So how many pages does card 4242 cost now? Pause and guess.

(three seconds)

One walk down the tree: the root, an inner page and a leaf. That's 3 pages, and the leaf holds the 14 addresses. Then
the 14 table pages they point to. 17 pages in all, instead of 23,818. A quarter of a millisecond instead of a quarter
of a second: about a thousand times faster. Same 14 rows, same coffee, a lot less reading.

SCREEN: Countdown. The root, one inner page and one leaf turn yellow ("index pages: 1, 2, 3"); 14 green dots run from
the leaf to the 14 squares; "3 index pages + 14 table pages = 17". Captions "17 pages instead of 23,818", "0.25 ms
instead of 250 ms: about a thousand times faster".

## Scene 8 · Its order, and its price · 3:41–4:04 · [GUARDRAIL] [LOOP-PAYOFF]

VO: Now, the question in your pocket. This index is sorted by card. Ask for payments by anything else, and its order
can't help, just as the cookbook's index couldn't find a quick dinner. And a copy has a cost. This one takes 9 MB,
next to the table's 186. Every new payment goes into it too, so indexes make reads cheap and writes more expensive.

SCREEN: "by anything else?" with a red cross beside it. "index: 1,136 pages, 9 MB   table: 23,818 pages,
186 MB"; one dot into the table and one into a leaf; "indexes make reads cheap and writes more expensive".

## Scene 9 · The moral, and a check · 4:04–4:41 · [MORAL] [PREDICT] [PAUSE]

VO: So the moral of the story: an index is a sorted copy of a few columns, each entry pointing to its row. A query is
fast when it can find one short run of entries in that copy. One quick check. Support now asks for every payment at
one shop. Does the index on card number help? Pause and think.

(three seconds)

No. One shop's payments are spread all over an index sorted by card. It's the quick dinner again, so it's back to
reading every page.

SCREEN: The moral in yellow; the callout pulses. "one shop: every payment"; countdown; a red cross beside the query; every leaf turns
purple and purple squares scatter over the grid; "pages read: 23,818". Last caption "an index answers the questions
its order answers".

---

### Beat check

- Opens with QUESTION (scene 1). FAMILIAR + ANALOGY (scene 2) before any term.
- PAIN and WISH (scene 3), BREAK (scene 4: sort the table; scene 9: a question the order can't answer).
- MAP said out loud (scene 5); NAME after each SHOW: sequential scan (scene 3), ctid (scene 5), leaves and B+tree
  (scene 6).
- PREDICT with PAUSE twice (scenes 7 and 9); SHOW right after each.
- GUARDRAIL (scene 8), MORAL and check (scene 9). Light moments: lemonade (1:38), same coffee (3:38).

### Accuracy notes for the producer

- Plan numbers are the lesson's run: `Rows Removed by Filter: 333488` with `loops=3`, `Buffers: shared hit=13203
  read=10615` (23,818), 249.862 ms; after the index 0.249 ms. The 17 is the lesson's count (3 index pages + 14 table
  pages); the Try it notes that a first run in a session reads a few more index pages.
- The index really has 1,130 leaves, 4 inner pages and a root; the picture draws 10 leaves.
- The second plan is a Bitmap Heap Scan over a Bitmap Index Scan; the next section reads it. The video says "one walk
  down the tree, then the 14 table pages".
- Deduplication (one entry per repeated card number, PostgreSQL 13+; 2,734 leaves without it) is left to the lesson.
- "Every new payment goes into it too": the lesson's section 3 measures it (89 MB of log copying 200,000 payments with
  three indexes, against 42 MB with none).
- "Back to reading every page" assumes no other index on the shop column, as in the lesson's data set at this point.
