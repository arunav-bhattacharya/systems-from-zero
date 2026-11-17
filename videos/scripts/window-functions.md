# Every row keeps its place: a window instead of a group

- Slug / scene: `window-functions`, `videos/scenes/window_functions.py:WindowFunctions`
- Lesson: `sql-06`, section 0, "Every payment keeps its row: a window instead of a group"
- Audience / level: a complete newcomer. Can read a little code; has met a table, a row and GROUP BY once in an
  earlier lesson, and nothing else about databases.
- Length: 5:05 (~780 words of narration at the Kokoro voice's ~180 wpm, plus one guess, one check and the
  silent moves)
- Poster: the default, 82% in (the shop blocks with every total, during the guardrail)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: GROUP BY folds rows away. How do you put a number worked out from many rows onto
  every row, and lose none of them?
- Misconception to steelman and break: "sum folds many values into one, so a query with sum gives one line per
  shop, or fails because payment_id isn't grouped". Broken by the prediction in scene 5: eight rows come back.
- Concept chain: GROUP BY folds a group into one line → so a single payment can't be shown → write the total on
  each row instead (OVER) → PARTITION BY says which rows are related → each row's window is its partition → the row
  stays, a column is added (window function) → the share falls out of it → OVER () makes one window (the check)
  → the sort is the cost (hardest last: the guardrail)
- Analogy family: the lesson's teacher marking a pile of exam papers (paper = row, class = partition, papers she
  looks through = window, number she writes = the result); GROUP BY is the head teacher who wants one line per
  class. Breaks on cost: PostgreSQL sorts the whole pile first.
- Open loops: the double charge (payments 17 and 18) planted in scene 1 → paid off in scene 10; "which number
  would shop 4's line print?" in scene 3 → answered by the window in scene 6.
- Assumptions: the eight succeeded March payments, the four GROUP BY lines, every merchant_total, the pct column
  and 211132 are the lesson's stepper and Try it output (re-run on the seed in SQLite). Times 16:40 and 16:42 on
  12 March are payments 17 and 18 in the seed.

## The one picture

After a short hook (a phone with the two identical charges), one table for the whole video: the eight March
payments as paper slips (payment, shop, amount, and an empty `merchant_total` slot), first in payment order, then
sorted into shop blocks. A coloured bar marks each shop's block (m1 blue, m4 gold, m5 teal, m7 purple). The query
sits at the top. The right side is a panel that changes: the GROUP BY lines, the teacher mapping, the guess, the
current row and its window, the names. Yellow means "look here" (the current row and its window), green means
correct, red means an error. At most six things on screen.

## Scene 1 · The double charge · 0:00–0:32 · [QUESTION] [LOOP-PLANT]

VO: Picture yourself scrolling through your bank app, and stopping. The same 189.99, at the same electronics shop, twice,
two minutes apart. You were charged twice. Support promises a refund, and to find every other customer it happened to.
For that, the database must keep every payment, and write something next to each one. So how do you put a number
worked out from many rows onto every row, and lose none of them? Keep that double charge in mind.

SCREEN: A phone, "your bank app", with two lines: Volt Electronics, -189.99, 12 March 16:40, and the same at
16:42 (outlined red). A yellow "?" and the caption "a number from many rows, on every row?".

## Scene 2 · Meet the rows · 0:32–1:04 · [FAMILIAR] [SHRINK]

VO: Let's start smaller. The company's app keeps each payment as one row in a table called payments, like one line in a
spreadsheet. Here are the eight that succeeded in March. Each row has the payment's number, the shop that was paid,
and the amount in cents. So 18999 means 189.99. And there's our double charge: payments 17 and 18, at shop 4, Volt
Electronics. Today's request: show every March payment, each one next to its shop's March total.

SCREEN: The phone leaves; the eight slips drop in (13, 14, 16, 17, 18, 19, 21, 22), with headers. Rows 17 and 18
pulse gold. The `merchant_total` slots appear empty, with the caption "every row stays, and gets its shop's total".

## Scene 3 · The tool we know folds · 1:04–1:42 · [FAMILIAR] [PAIN] [BREAK] [WISH] [JOKE:amplify] [LOOP-PLANT]

VO: An earlier lesson's tool for one number from many rows is GROUP BY. It folds each shop's rows into one line. Eight
rows in, four lines out. Ask for the payment number as well, and PostgreSQL, the database program here, refuses with
an error. And that's fair. After folding, a line stands for a whole shop. Shop 4's line holds three payments. Which
one should it print? You could work out the totals separately, then join them back onto the payments. It works, but
it's folding the laundry, then unfolding it all again to find one sock. What we want is to keep every row, and write
the total beside it.

SCREEN: Query `SELECT merchant_id, sum(amount_minor) ... GROUP BY merchant_id`. Copies of each shop's slips fly
right and merge into four lines (m1 5310, m4 56997, m5 147500, m7 1325). "8 rows in, 4 lines out". The query gains
`payment_id`; the m4 line shows "17? 18? 19?" in red; the error in red mono. A dashed arrow from the four lines
back to the slips, "join back: the grouping written twice". The lines dim.

## Scene 4 · The teacher · 1:42–2:16 · [ANALOGY] [MAP] [JOKE:pivot]

VO: Picture a teacher marking a pile of exam papers. For each paper, she looks through the papers from the same class,
writes the class average on this paper, and puts it back on the pile. Every paper comes back with one more number, and
none goes missing. Ours writes a total, not an average. Let's map it. A row is a paper. The class is the shop. The
papers she reads are the rows of that shop. And the number she writes is a new column. GROUP BY is the head teacher.
She wants one line per class, and never sees a single paper again.

SCREEN: Each slip gets a folded corner. Mapping lines appear one by one in the right panel: "a paper = a row",
"the class = the shop", "papers she looks through = rows of the same shop", "the number she writes = a new column".
On "head teacher", the dimmed GROUP BY lines glow, labelled "the head teacher: one line per class".

## Scene 5 · One word, and a guess · 2:16–2:41 · [SHRINK] [PREDICT] [PAUSE] [BREAK]

VO: In SQL, the teacher is one word. Write OVER after sum, then say which rows belong together: PARTITION BY merchant_id,
the same shop. Before we run it, a guess. sum folds many values into one. So do we get four rows, eight rows, or the
same error? Pause and guess.

(three seconds)

Eight. Let's watch why.

SCREEN: The query becomes the stepper's: `SELECT payment_id, merchant_id, amount_minor,` /
`sum(amount_minor) OVER (PARTITION BY merchant_id)`, with the OVER part yellow. Three chips: "4 rows", "8 rows",
"the same error"; a countdown bar. "8 rows" turns green.

## Scene 6 · Watch it run · 2:41–3:35 · [SHOW] [LOOP-PAYOFF]

VO: First, PostgreSQL sorts the rows, so each shop's payments sit together. Nothing is folded. Then it walks down the
rows. Payment 14 is the only one at shop 1, so it reads this row alone: 5310. Payment 17 is at shop 4. It reads 17, 18
and 19. Three times 18999 is 56997, written on row 17. Payment 18 reads the same rows, so it gets the same total. And
row 17 is still there. A column was added, and no row was taken away. Row 19 gets the same. Then 13 starts shop 5, so
the set changes to 13, 16 and 22: 147500. The rest fill in the same way. Eight rows in, eight rows out.

SCREEN: The slips slide into shop blocks (14 | 17 18 19 | 13 16 22 | 21) and a coloured bar marks each block. A
yellow marker points at the current row and a yellow frame surrounds the rows it reads; the right panel reads
"current row: 14", "reads rows: 14", "sum = 5310", and so on, as in the lesson's stepper. Totals land in the slots.
Then "8 rows in, 8 rows out".

## Scene 7 · Now the names · 3:35–3:52 · [NAME]

VO: Now the names. The class is called a partition. The rows read for the current row are its window. And a function that
reads a window, and keeps the row, is a window function. For every row, a window of related rows. The function reads
the window. The row stays.

SCREEN: Right panel: "the class: a partition" (the bars glow), "the rows it reads: the window" (the yellow frame
on shop 5), "reads a window, keeps the row: a window function" (the OVER part glows). Caption with the motto.

## Scene 8 · Do something with it · 3:52–4:01 · [SHOW]

VO: Now the total sits on the row, you can divide by it. Each of Volt's three payments is 33.3 percent of its March.

SCREEN: A `pct` column grows to the right of the slips (100.0, 33.3, 33.3, 33.3, 43.4, 21.4, 35.3, 100.0); caption
`100.0 * amount_minor / merchant_total`; Volt's three 33.3s glow.

## Scene 9 · Where the teacher breaks · 4:01–4:19 · [GUARDRAIL]

VO: Here the teacher picture breaks. She looks things up paper by paper. PostgreSQL first sorts the whole pile into shop
order, and on a big table, that sort is most of the work. So pick by what you want back. One line per group: GROUP BY.
Every row, with a number beside it: a window.

SCREEN: The pct column goes. Caption "first: sort the whole pile into shop order"; the slips lift and resettle, the
bars glow. Then "one line per group: GROUP BY" and "every row, plus a number: a window".

## Scene 10 · The moral, the double charge, and a check · 4:19–5:05 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, a number from many rows, on every row? Give each row a window. GROUP BY folds the rows. A window adds a column,
and never takes a row away. And the double charge? Partition by card, shop and amount, in time order, and payment 18
sits right after 17. Later in this lesson, a window function compares the two. One quick check. Leave the brackets
after OVER empty: no partition rule at all. What lands on row 21? Pause and think.

(three seconds)

The whole month's total, 211132. With no rule, every row is related, so the whole result is one window.

SCREEN: Caption "a window adds a column; it never takes a row away". Rows 17 and 18 glow gold with "partition by
card, shop and amount, in time order". The OVER part becomes `OVER ()`; row 21's total becomes a yellow "?";
countdown. Then the bars go, one yellow frame surrounds all eight rows, and every total becomes 211132 (green).

---

### Beat check

- Opens with QUESTION from a felt situation (scene 1), then FAMILIAR rows and the familiar tool (scenes 2, 3).
- PAIN and BREAK of GROUP BY (scene 3), WISH at its end; ANALOGY + MAP (scene 4) before any new name.
- PREDICT with PAUSE (scene 5) breaks the "sum folds" model; SHOW (scene 6); NAME only after (scene 7).
- GUARDRAIL with the analogy's breaking point (scene 9); MORAL, loop payoff and a check (scene 10).
- Light moments: the laundry and the sock (1:36), the head teacher who never sees a paper again (2:12).

### Accuracy notes for the producer

- Rows, totals and shares are the lesson's (stepper and Try it); re-run in SQLite on the seed: m1 5310, m4 56997,
  m5 147500, m7 1325; pct 100.0, 33.3 ×3, 43.4, 21.4, 35.3, 100.0; `OVER ()` gives 211132 on every row.
- The error text is the lesson's, quoted from PostgreSQL 18.
- "Partition by card, shop and amount, in time order" is the lesson's double-charge window (section 2); the video
  doesn't show `lag`, and says only that a window function compares the two.
- The video shows rows sorted by shop before the walk, as the stepper does; PostgreSQL does sort for PARTITION BY
  (the lesson's last section shows the Sort node). The order of rows inside a partition without ORDER BY is not
  promised; the video keeps payment order.
- The teacher writes a class average in the analogy; the query writes a sum. The narration says so.
- Left to the lesson: ranking functions, ORDER BY inside OVER and running totals, LAG, and filtering on a window's
  result one level up.
- Spoken forms via `SAY`: payment_id as "payment I D", merchant_id as "merchant I D", OVER, PARTITION BY and GROUP
  BY in lower case, 189.99 as "one eighty-nine ninety-nine", a digit's possessive as a word.
