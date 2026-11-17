# One line per shop: sort the receipts into envelopes, then fold each one

- Slug / scene: `group-by-rollup`, `videos/scenes/group_by_rollup.py:GroupByRollup` (the slug is kept; the video now
  covers section 0 only, so ROLLUP is left to the lesson)
- Lesson: `sql-04`, section 0, "One line per shop: GROUP BY sorts rows into piles and folds each pile"
- Audience / level: a complete newcomer who has never written SQL.
- Length: 3:51 (~680 words of narration at the Kokoro voice's ~180 words a minute, plus a guess, a check and
  the silent moves)
- Poster: `POSTER=182` (every envelope filled, the four lines out, the key column gold and the aggregates teal)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: every shop wants its own total. How do you turn many payment rows into one line per
  shop, without asking eight times or shipping every row out?
- Misconception to steelman and break: "after grouping, I can still show any column, like each shop's amount". It
  looks harmless for shops 1 and 7 (one receipt each) and breaks on shop 5 (three amounts: which goes on the front?).
- Concept chain: an aggregate folds many values into one → alone, it folds every row into one → GROUP BY makes one
  pile per key, and the aggregate folds each pile → WHERE runs before the piles exist → one line per group, so only
  the key and aggregates can be shown → a group needs at least one row → filtering whole piles needs HAVING (next)
- Analogy family: the lesson's shoebox of paper receipts, sorted into one envelope per shop, with the count and the
  total written on each envelope's front.
- Open loops: "one line per shop?" planted in scene 1 → answered in scene 7.
- Assumptions: the March rows, the groups and the four output lines are the lesson's stepper exactly; the 30 and
  720455 line and the shops 6 and 8 fact are the lesson's. Amounts are in cents, as in the stepper.

## The one picture

Left: a shoebox (grey) holding the ten March payments as receipts ("13 m5 64000", the failed and pending ones in red
and grey). Middle (from scene 3): four envelopes (gold), one per shop key (m1, m4, m5, m7), with a flap; the amounts
land inside. Right: the lines that come out (merchant_id, count, sum), one level with each envelope. The query sits
at the top. Captions on one line at the bottom.

## Scene 1 · The question · 0:00–0:45 · [FAMILIAR] [QUESTION] [PAIN] [WISH] [JOKE:amplify] [LOOP-PLANT]

VO: A small company's app records card payments. Each payment is one row in a table: which shop was paid, the
amount in cents, and whether it succeeded. Here are the ten from March.

Every shop wants to know what it took. So how do you turn many rows into one line per shop?

You could ask once per shop: the rows for shop 1, then shop 2, and so on. Eight trips, and you need the list of shops
first. Or you could fetch every payment into your own program and add them up there.

With ten rows, fine. With a million, you'd ship a million rows out to work out 2,500 numbers. That's like posting a
whole filing cabinet to someone, to ask for one total. Better to do the adding where the data lives.

SCREEN: The shoebox and ten receipts. Captions for the two workarounds; "1,000,000 rows out, for 2,500 numbers".

## Scene 2 · Many rows in, one row out · 0:45–1:15 · [SHOW] [NAME]

VO: The database starts with an aggregate function: one that takes many values and returns one. count counts rows,
and sum adds up a column.

Used alone, an aggregate folds every row it sees into one. Over all 37 payments in the course database, the succeeded
ones fold into a single line: 30 payments, 720,455 cents.

Many rows in, one row out. But that's one total for everyone, and we want one per shop.

SCREEN: The query `SELECT count(*), sum(amount_minor) FROM payments WHERE status = 'succeeded';` at the top and its
real result on the right: count 30, sum 720455, "all 37 payments".

## Scene 3 · The shoebox · 1:15–1:50 · [ANALOGY] [MAP] [NAME]

VO: Picture a shoebox of paper receipts at the end of the day. You'd sort them into one envelope per shop. Then you'd
count the receipts in each envelope, and write the total on the front.

That's what GROUP BY does. Each receipt is a row. Each envelope is a group, one for each different shop number, and
that number is the group's key. The total on the front is the aggregate.

SCREEN: Four empty envelopes draw in, with keys m1, m4, m5, m7. Captions map each part.

## Scene 4 · Run it on March · 1:50–2:50 · [SHRINK] [PREDICT] [PAUSE] [SHOW]

VO: Let's run it on March, for succeeded payments only. WHERE goes first, and it looks at one row at a time. Payment
15 failed, and payment 20 is still pending, so both are gone before any envelope exists.

Eight rows are left. How many lines will come out? Pause and guess.

(three seconds)

Four. GROUP BY makes one envelope per shop it finds: shop 5's three receipts in one, shop 4's three in another, and
one each for shops 1 and 7.

Now each aggregate folds its envelope. count counts the receipts, and sum adds them up. Shop 5: three payments,
147,500 cents. Shop 4: three, 56,997. Shop 1 and shop 7: one each.

SCREEN: The stepper's query at the top. 15 and 20 are struck and fade. Countdown. The amounts fly into the envelopes.
The output lines appear: 5 | 3 | 147500, 4 | 3 | 56997, 1 | 1 | 5310, 7 | 1 | 1325.

## Scene 5 · Show the amount too? · 2:50–3:30 · [BREAK] [NAME] [JOKE:soften]

VO: Now a tempting idea. Why not show each shop's amount on its line too? For shops 1 and 7, there's only one amount,
so it looks harmless.

But shop 5's line stands for three receipts, with three amounts. Which one goes on the front? PostgreSQL won't play
favourites. It stops with an error: the column must appear in the GROUP BY clause, or be used in an aggregate
function.

That's the rule that trips up everyone at first. After grouping, one line stands for a whole envelope. So a column can
appear there only if it has one value per envelope: the key you grouped by, or an aggregate.

SCREEN: Caption "show each shop's amount on its line too?"; the single amounts of shops 1 and 7 glow; then shop 5's three amounts turn red and "which amount? 64000, 31500 or 52000"
appear under its line. The header's key column glows gold, count and sum teal.

## Scene 6 · Before the fold and after it · 3:30–3:50 · [GUARDRAIL]

VO: One more limit. WHERE ran before the envelopes existed, so it can only judge single rows. To drop whole envelopes,
say shops that took 100.00 or less, you need a second filter that runs after the fold. It's called HAVING, and it's the
next section.

SCREEN: "HAVING sum(amount_minor) > 10000" joins the query at the top; dark bars dim the envelopes and lines of shops 1
and 7, then lift.

## Scene 7 · The moral, and a check · 3:50–4:20 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, one line per shop? Sort the rows into groups by a key, then fold each group into one row. And the adding
happens where the data lives.

One quick check. Shop 6, Paper Lantern Books, took no payments at all. Does it get a line with a zero? Pause and
think.

(three seconds)

No. No receipts, no envelope, and no line. A group exists only if at least one row has its key.

SCREEN: "sort into groups by a key, then fold each group into one row". For the check, a dashed envelope "m6" with no
receipts, crossed out.

---

### Beat check

- QUESTION and the felt PAIN first (scene 1), from the familiar table of payments.
- NAME of the aggregate after a plain sentence and its result (scene 2); ANALOGY + MAP before GROUP BY's meaning
  (scene 3).
- PREDICT with PAUSE (scene 4, and the check in scene 7); SHOW right after each.
- BREAK: "show the amount too", steelmanned on shops 1 and 7, broken on shop 5 (scene 5).
- GUARDRAIL (scene 6): WHERE judges rows before the fold; dropping groups needs HAVING. MORAL last.
- Light moments: the filing cabinet in the post (~0:40), PostgreSQL won't play favourites (~3:10), no receipts, no
  envelope (the check).

### Accuracy notes for the producer

- The March rows (13 to 22), the dropped 15 (failed) and 20 (pending), the four groups and their lines (1 | 1 | 5310,
  4 | 3 | 56997, 5 | 3 | 147500, 7 | 1 | 1325) are the lesson's stepper. HAVING sum > 10000 keeping shops 4 and 5 is
  its last frame.
- `30 | 720455` is the lesson's real psql output for all 37 payments.
- The error is described in words, with the wording of the real PostgreSQL message the lesson shows for `status`;
  no error output is invented for `amount_minor`.
- Shops 6 and 8 took no payments (lesson); the check uses shop 6, Paper Lantern Books (seed).
- Left to the lesson: the primary-key exception (group by `m.merchant_id`, show `m.name`), aggregates skipping NULL,
  `sum` over no rows being NULL, HashAggregate and GroupAggregate, and ROLLUP (section 3).
- Pronunciation: Kokoro dropped the possessive after a digit ("shop 5's" came out as "shop five"), so a `SAY` rule
  says the digit as a word ("shop five's"); the two affected cached lines were deleted and re-synthesized.
- check_audio: 97.9% at -16.1 LUFS; the rest are Whisper spellings (some for sum, favorites, fives, 100 for 100.00).
