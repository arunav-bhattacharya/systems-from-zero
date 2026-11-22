# The refunded tea: keeping a stored answer right, one change at a time

- Slug / scene: `view-maintenance`, `videos/scenes/view_maintenance.py:ViewMaintenance`
- Lesson: `store-12`, section 2, "Keeping the answer right one change at a time"
- Audience / level: a complete newcomer. Knows what a table of rows is from earlier lessons; doesn't know what a
  materialized view, a refresh, a delta or an index is.
- Length: 5:01 (~765 words at Kokoro's ~165 words a minute, plus two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=176`, the rescan in scene 6 (table with the struck rows, the two remaining M-0042 rows lit, the view's min back
  to 300, the counter "2 table rows read")
- The learner's real question: if a stored total can be fixed one sale at a time, can every stored number? What
  goes wrong with "the cheapest sale"?
- Misconception to steelman and break: "every number on the board can be kept right the same way, one change at a
  time, because the first one can". Broken by deleting the minimum (scene 5), and by a batch that deletes 90% of the
  table (scene 8).
- Concept chain: a stored answer goes stale; a refresh redoes everything → a delta rule changes only what the change
  changes (count, sum, min on insert) → deletes mirror inserts for count and sum → deleting the minimum breaks MIN →
  rescan one group, or store more → deltas lose when a batch rewrites most of the data (hardest last)
- Analogy family: the lesson's café whiteboard by the till: today's takings, and "cheapest sale today: 1.20", a
  small tea that comes back for a refund. Receipts are the table; the board is the view; counting the whole till is a
  refresh; adding each sale as it rings up is a delta rule; a tray of receipts kept in order by the board is the
  "store more" way out.
- Open loops: "what should the second line say?" planted in scene 1 → scene 5 (the tea) and scene 9.
- Assumptions: all table and view numbers are the lesson's stepper (payments 1, 2, 3 for M-0042: 1,250, 300, 8,900;
  payment 4 for M-0007: 4,000; insert payment 9, M-0042, 150; then delete 3, 9 and 4; 2 base rows read and 4 view
  rows written). Lab numbers: 1,402 against about 20 million rows for 1,000 changes on 20,000 payments; 35,994 against
  2,200 for a batch deleting 90%. The whiteboard shows only the lesson's 1.20; the takings line has no number.

## The one picture

Left: the payments table (blue box: id, shop, amount). Right: the view (teal box, the whiteboard: shop, count, sum,
min). Top centre: the change arriving (yellow chip). Under the view: the delta rule for this change (yellow), and the
work counter ("table rows read", "view rows written"). Deleted rows are struck through in red and dimmed. Yellow marks
a change, red a problem, green a fix, purple the store-more tray.

## Scene 1 · The whiteboard · 0:00–0:35 · [FAMILIAR] [ANALOGY] [QUESTION] [LOOP-PLANT]

VO: Picture a busy café. On a whiteboard by the till, the owner keeps today's takings. Each sale, she adds the
amount. Each refund, she takes it off. When a regular asks how the day is going, she reads the board instead of
counting the till. One afternoon she adds a second line: cheapest sale today, 1.20, a small tea. Then the customer
brings the tea back for a refund. The takings are easy: take off 1.20. But what should the second line say now?
Hold that question.

SCREEN: Title card. The whiteboard in the centre: "takings today: + each sale, - each refund". The second line
"cheapest sale today: 1.20 (a small tea)". A gold chip "refund: the tea, 1.20". The takings line gets "- 1.20" and
a green tick; the cheapest line gets a yellow "?".

## Scene 2 · A stored answer, and a refresh · 0:35–1:15 · [MAP] [NAME] [PAIN] [JOKE:amplify] [WISH]

VO: A database can keep the same board. The receipts are a table of payments, in PostgreSQL, a free database
program. The board is a stored answer to a question people keep asking: for each shop, how many payments, their
total, and the smallest. A stored answer like that is called a materialized view. The plain way to keep it right is
a refresh: work the whole answer out again. In the lesson, that read a million payments to change one number. It's
counting the whole till after every sale. What we want is to change only what the new payment changes.

SCREEN: The whiteboard slides right and becomes the view (shop, count, sum, min); the table appears on the left.
Captions map: "the receipts = the table", "the whiteboard = a materialized view". On "refresh", a yellow bar sweeps
every table row and the view rows flash; "a refresh: a million payments read to change one number". Then "wanted:
change only what the new payment changes".

## Scene 3 · An insert · 1:15–2:05 · [SHRINK] [SHOW] [NAME]

VO: Let's shrink it. Four payments, two shops. Shop M-0042 has 3 payments, 10,450 cents in all, and the smallest is
300. Now a payment arrives: shop M-0042, 150. Watch the view. Count, plus 1. Sum, plus 150. Minimum, the smaller of
300 and 150: now 150. All of it came from the new payment and the old view row. Not one row of the table was read.
A change to the input is called a delta, and the rule that turns it into a change to the answer is a delta rule.
It's the owner adding each sale to the board as it rings up.

SCREEN: The view's M-0042 row glows. The chip "INSERT payment 9: M-0042, 150"; row 9 drops into the table. A yellow
dot runs from row 9 to the view; count 3 → 4, sum 10,450 → 10,600, min 300 → 150, each flashing as it's said. The
delta line "count + 1, sum + 150, min(300, 150) = 150". Counter "table rows read: 0   view rows written: 1".

## Scene 4 · A delete above the minimum · 2:05–2:25 · [SHOW]

VO: Now a refund deletes the 8,900. Deletes mirror inserts: count minus 1, sum minus 8,900. And 8,900 was above the
minimum, so the minimum can't have changed. Still nothing read.

SCREEN: Chip "DELETE payment 3: M-0042, 8,900"; row 3 struck through in red and dimmed. Count 4 → 3, sum 10,600 →
1,700; the delta line "count - 1, sum - 8,900; 8,900 > 150: min stays". Counter "view rows written: 2".

## Scene 5 · Delete the minimum · 2:25–3:05 · [PREDICT] [PAUSE] [BREAK] [LOOP-PAYOFF]

VO: So far so good. Now delete payment 9, the 150. That was the minimum. Count and sum are easy: 2 payments, 1,550.
What's the new minimum? Pause and guess.

(three seconds)

You can see it's 300, because the table is on screen. The view can't. It kept one number per shop, and the next
smallest was never in it. That's the refunded tea. The board said 1.20, and nothing on it says what came second.

SCREEN: Chip "DELETE payment 9: M-0042, 150"; row 9 struck. Count 3 → 2, sum 1,700 → 1,550; the min cell turns red
"?". Countdown. Rows 1 and 2 glow in the table; a dashed red line between table and view, "the view kept one number
per shop". The delta line "count - 1, sum - 150, but 150 was the min".

## Scene 6 · Two ways out · 3:05–3:50 · [SHOW] [JOKE:release]

VO: There are two ways out. One: go back to the receipts, but only this shop's. Through an index on the shop, a
lookup that finds rows by shop, the view reads M-0042's two remaining payments and takes the smaller: 300. That
costs one shop's rows, not the whole table. pg_ivm, an add-on for PostgreSQL, works this way. The other way: store
more. Keep every amount, sorted, for every shop, like a tray of receipts in order beside the board. The next smallest
is always at hand, and you pay in memory instead. Streaming databases, which keep answers updated as data flows in,
take that road.

SCREEN: Green dots run from rows 1 and 2 to the min cell; "min(1,250, 300) = 300, read through an index"; counter
"table rows read: 2   view rows written: 3". Then a purple tray under the view: "kept sorted:
150  300  1,250  8,900"; 150 and 8,900 struck, 300 glows: "the next smallest is at hand; the cost is memory".

## Scene 7 · The last change, and the name · 3:50–4:20 · [SHOW] [NAME]

VO: Last change: delete shop M-0007's only payment. Its count drops to 0, so its row leaves the view. Four changes
cost 2 table rows read and 4 view rows written. A refresh after each would have read the whole table four times.
Keeping a stored answer right one change at a time is called incremental view maintenance.

SCREEN: Chip "DELETE payment 4: M-0007, 4,000"; row 4 struck; the M-0007 view row fades out; "count reaches 0:
delete the view row". Counter "table rows read: 2   view rows written: 4". Caption "incremental view maintenance: a
delta rule for every step of the view's query".

## Scene 8 · When deltas lose · 4:20–5:00 · [GUARDRAIL] [JOKE:is-the-explanation]

VO: So should every view work by deltas? Not always. In the lesson's lab, 1,000 small changes to 20,000 payments
cost 1,402 rows of work as deltas, against 20 million for a refresh after each one. But a batch that deleted 90% of
the table cost 35,994 rows as deltas, against 2,200 for one refresh at the end. Most of it went on rescanning shops
whose minimum had just been deleted. Deltas are good with small change. When a batch rewrites most of the data,
work it out again.

SCREEN: Two bars: "1,000 changes, by deltas: 1,402 rows" (a sliver, green) and "a refresh after each: 20 million
rows" (red, long). Then they turn into "a batch deleting 90%, by deltas: 35,994 rows" (red, long) and "one refresh at
the end: 2,200 rows" (green, short). Caption "deltas win when changes are few; when a batch rewrites most of the
data, work it out again".

## Scene 9 · The moral, and a check · 5:00–5:40 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, what should the second line say? The board can't tell without the receipts. Counts and sums can be added
and taken back, one change at a time. The smallest can be added to, but not taken back, unless you look again or
kept more. One quick check. Shop M-0042 has two payments left, 1,250 and 300. A refund deletes the 1,250. Does the
view need to read the table? Pause and think.

(three seconds)

No. 1,250 is above the minimum, so the minimum stays 300. Only deleting the minimum sends you back to the receipts.

SCREEN: Captions "counts and sums: add and take back"; "the smallest: add to, but not take back". The check: the
chip "DELETE: M-0042, 1,250"; countdown; "1,250 > 300: min stays", count 2 → 1, sum 1,550 → 300, counter unchanged
at "table rows read: 2". Last caption "a stored answer stays right by deltas only if every part can be taken back".

---

### Beat check

- Opens with FAMILIAR + ANALOGY and the QUESTION (scene 1), from the lesson's whiteboard and refunded tea.
- MAP said out loud and NAME materialized view (scene 2) after the board is understood; PAIN and WISH (scene 2).
- SHRINK and SHOW (scenes 3, 4); NAME delta and delta rule after the first SHOW.
- PREDICT with PAUSE and BREAK of "every number can be kept the same way" (scene 5), paying off the tea.
- NAME incremental view maintenance (scene 7) after the whole run of changes.
- GUARDRAIL (scene 8), MORAL and check (scene 9). Light moments: counting the whole till (1:05), "nothing on it says
  what came second" (3:00), "good with small change" (4:55).

### Accuracy notes for the producer

- The stepper's view keeps count, sum and min per merchant; the average is computed on read (sum / count). The video
  leaves the average out.
- "Read a million payments to change one number" is the lesson's first Try it (1,000,001 payments, 24,000 view rows
  rewritten, about a quarter of a second). That view groups by shop and day; this section's view groups by shop.
- The rescan reads M-0042's remaining rows through an index on the shop; the stepper counts them as 2 base rows read.
- 20 million is the lab's 20,000,500 base rows read (20,200,500 rows touched) for a refresh after every one of 1,000
  changes. 35,994 rows touched with 498 minimum rescans, against 2,200 for one refresh.
- The tray is the lab's `MinTracker` (every amount per group in a sorted structure). Streaming databases taking the
  store-more road and pg_ivm taking the rescan road are the lesson's statements.
- Joins (a delta that must read the other table, and the three-part delta when both change) are left to the lesson.
- The check's result (count 1, sum 300) follows the stepper's delete rule.
