# A crate per trip: why passing rows in batches is seven times faster

- Slug / scene: `volcano-vs-vector`, `videos/scenes/volcano_vs_vector.py:VolcanoVsVector`
- Lesson: `store-09`, section 3, "Version 3 of running a plan: pass a thousand values per call"
- Audience / level: a complete newcomer. Has seen a loop; doesn't know what a plan, an operator, a CPU cache or a
  function call's cost is.
- Length: about 4 minutes (~640 words of narration, two pauses, silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: one comparison takes under a nanosecond, and a plain loop does the whole report in
  3.3 ms. Why does the database's usual way take 139 ms, and what do batches change?
- Misconceptions to steelman and break: (1) "the comparisons are the slow part" (the plain loop needs 0.33 ns a row;
  X100's profile of MySQL: the arithmetic was under a tenth); (2) "bigger batches are always better" (1 value per
  batch brings the overhead back; above about 8,000 the batch falls out of the CPU cache)
- Concept chain: a plan of operators that pull one row per next() call → every row pays a call at every level →
  the machinery, not the comparison, is the cost → a batch of 1,024 values per call, one tight loop → about 7 times
  faster → the batch size has a sweet spot → which kind of database chooses which (hardest last: the cache)
- Analogy family: the lesson's second-hand bookshop. You at the counter, a friend fetching novels priced over 5 one
  at a time ("one more, please"); a crate per trip; a crate too big for the counter, books on the floor.
- Open loops: "where do the other 136 milliseconds go?" planted in scene 1 → paid off in scene 3
- Assumptions: the demo numbers are the lesson's Try it (10,000,000 rows; 139.3 ms and 13.93 ns a row one row at a
  time, 18.8 ms and 1.88 ns in batches of 1,024, 3.3 ms and 0.33 ns as a plain loop). The X100 numbers are the
  lesson's (2005; MySQL 4.1 26.6 s; arithmetic under 10%; X100 0.50 s; hand-written C 0.22 s; 6 million order lines;
  best batch size about 1,000, slower above about 8,000). The five amounts on the strip (4,200, 9,700, 1,100,
  9,900, 9,300) and the running sums they make are picked for the picture.

## The one picture

Left: the plan as three stacked boxes, Sum (blue), Filter: amount > 9000 (gold), Scan payments (teal), joined by
next() arrows, with a strip of example amounts under the scan. Rows (and later a crate of 1,024 amounts) travel up
the column beside the boxes. Right: a counter (calls to next() on the scan) and three time bars (one row at a time,
batches of 1,024, a plain loop), later the batch-size axis and the DuckDB / PostgreSQL chips. Captions at the bottom.
Yellow is the work itself, red the overhead, green a row that passes or the batch result.

## Scene 1 · Where does the time go? · 0:00–0:28 · [QUESTION] [LOOP-PLANT]

VO: A report adds up every payment above 9,000 cents, out of 10 million payments. Checking one amount takes the
processor well under a nanosecond, a billionth of a second. Written as one plain loop, the whole job takes 3.3
milliseconds. Run the usual way, one row at a time through a database's plan, it takes 139. So where do the other 136
milliseconds go? Hold that question.

SCREEN: Title card. The query `sum(amount) WHERE amount > 9000`; a short yellow bar "a plain loop: 3.3 ms"; a long
blue bar "one row at a time: 139 ms"; caption "where do the other 136 ms go?".

## Scene 2 · One more, please · 0:28–1:35 · [FAMILIAR] [ANALOGY] [MAP] [SHOW] [NAME]

VO: Start in a second-hand bookshop. You're at the counter, and a friend fetches novels priced over 5 for you to add
up. You say: one more, please. Your friend walks along the shelves, checks a price, and brings back one book. Then you
ask again.

A database runs our report the same way. Before it runs, the query becomes a plan, a tree of small steps called
operators. A scan reads the payments, a filter keeps amounts over 9,000, and a sum adds them up. Each operator gets its
input by asking the one below it for the next row. That ask is a function call, named next. So the sum is you at the
counter, the filter is your friend checking the price, and the scan is the walk along the shelves.

Watch one row. The scan reads 4,200 and hands it up. It fails, so the filter asks again. 9,700 passes, and the sum adds
it. Then the whole chain runs again for the next row. Every row costs a call at every level.

This is the iterator model, and PostgreSQL runs queries this way. For our report, the scan alone is called 10 million
times. The query takes 139 milliseconds, about 14 nanoseconds a row.

SCREEN: Scan, filter and sum boxes appear bottom up; each gets its bookshop label ("the walk along the shelves",
"your friend checks the price", "you, at the counter"). next() arrows with yellow dots going down; amounts rise up the
column, red if they fail, green if they pass; the sum ticks 9,700, 19,600, 28,900. The counter runs to 10,000,000.

## Scene 3 · The machinery · 1:35–2:25 · [PAIN] [BREAK] [LOOP-PAYOFF] [JOKE:amplify] [WISH]

VO: So, the other 136 milliseconds. You might think the comparison is the slow part. It isn't. The plain loop needs a
third of a nanosecond a row. The rest is machinery. Every call goes through the same door, so the chip can't guess
which code comes next. And the condition is worked out by walking a little tree, one node for each part of amount over
9,000.

Researchers in Amsterdam measured this in 2005, on MySQL, a popular free database program. A standard report over 6
million order lines took 26.6 seconds. The additions and multiplications were under a tenth of it. A program written
by hand took 0.22 seconds. Your friend spends the afternoon walking, and about a minute reading prices. Wouldn't it be
nice if every trip brought back more than one book?

SCREEN: The long bar splits: a thin yellow "the work itself" and a red "overhead". The three boxes pulse red; the
filter pulses again for the expression tree. Captions for the 2005 measurement, one fact at a time. Last caption
"wanted: more than one book per trip".

NOTE: The afternoon-walking line is the light moment; it restates "under a tenth is the work".

## Scene 4 · A crate per trip · 2:25–3:00 · [ANALOGY] [SHOW] [NAME]

VO: So send your friend with a crate. Vectorized execution changes what next returns: a batch of 1,024 amounts, all
from one column, in one plain array. The filter runs one tight loop over the array, with no calls inside. The chip can
overlap many rows at once, and the compiler can even compare several amounts in one instruction. A call is now paid
once per crate. That's under 10,000 calls for 10 million rows.

SCREEN: A crate (a column of amounts, "a crate: 1,024 amounts") rises from the scan. A yellow frame sweeps it; the
loop `for (i in 0 until 1024) if (a[i] > 9000) sum += a[i]` beside it; a purple frame takes four amounts at once.
The counter drops to 9,766, "instead of 10,000,000".

## Scene 5 · Predict, then show · 3:00–3:22 · [PREDICT] [PAUSE] [SHOW] [JOKE:reward]

VO: So how much faster is the report now? Pause and guess. (three seconds) 18.8 milliseconds, about 7 times faster
than 139. In 2005, the Amsterdam team's system, X100, ran its report in half a second, over 50 times faster than
MySQL. Same books, far fewer trips.

SCREEN: Countdown. The green bar "batches of 1,024: 18.8 ms, 1.9 ns a row" grows between the other two; "about 7
times faster". Caption "X100 (2005): 0.50 s, over 50 times faster than MySQL's 26.6 s".

## Scene 6 · Bigger crates? · 3:22–3:52 · [BREAK] [JOKE:is-the-explanation]

VO: So, bigger crates, always better? Let's be fair and try. One value per batch brings the call overhead right back.
Around 1,000 was fastest in X100's tests. Above about 8,000, the batch no longer fits in the CPU cache, the small,
fast memory on the chip, and it slows down again. The crate no longer fits on the counter, so the books go on the
floor.

SCREEN: A log axis of values per batch (1 to 10,000). A red marker at 1 ("the overhead is back"), green at about
1,000 ("fastest"), gold above 8,000 ("out of the cache: slower").

## Scene 7 · Which databases do which · 3:52–4:15 · [GUARDRAIL]

VO: DuckDB, a free database program built for reports, runs every query in batches of 2,048. PostgreSQL keeps one row
at a time. Its typical query finds a few rows through an index, where the cost per row is noise, and small operators
are easy to combine.

SCREEN: Chips "DuckDB: batches of 2,048 (reports over millions of rows)" and "PostgreSQL: one row at a time (a few
rows through an index)".

## Scene 8 · The moral, and a check · 4:15–4:45 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So the moral of the story: passing rows costs a call each time. Pass one row per call when there are few rows,
and a crate per call when there are millions, so the time goes to the amounts. One quick check. A support screen finds
10 rows through an index. Would batches of 1,024 make it noticeably faster? Pause and think. (three seconds) Hardly.
Ten rows of overhead is too little to notice. Batches pay off when a query reads millions of rows.

SCREEN: The moral as captions over the whole picture. The query becomes "10 rows through an index"; countdown; a
red cross by the batch bar's label; "batches pay off over millions of rows".

---

### Beat check

- Opens with QUESTION (scene 1, the missing 136 ms). FAMILIAR + ANALOGY + MAP (scene 2) before the name iterator model.
- PAIN, BREAK (the comparison isn't the cost), LOOP-PAYOFF and WISH (scene 3).
- SHOW then NAME vectorized execution (scene 4); PREDICT + PAUSE (scene 5) and the check (scene 8).
- BREAK of "bigger is better" and of the analogy's counter (scene 6); GUARDRAIL (scene 7); MORAL last.
- Light moments: the afternoon of walking (2:20), same books fewer trips (3:20), books on the floor (3:50).

### Accuracy notes for the producer

- Demo numbers are the lesson's Try-it run; the lesson says the user's own numbers vary with CPU and JDK but the order
  holds. "About 7 times" is 139.3 / 18.8 = 7.4. 10,000,000 / 1,024 = 9,766 batches, shown as "under 10,000 calls".
- The bars are drawn to scale in nanoseconds per row (13.93, 1.88, 0.33).
- "Every call goes through the same door, so the chip can't guess which code comes next" is the lesson's point about
  many kinds of operator behind one next() call (branch prediction, not named).
- The X100 facts are the lesson's (Boncz, Zukowski and Nes, CIDR 2005: TPC-H query 1, MySQL 4.1 26.6 s, arithmetic
  under 10%, X100 0.50 s, hand-written C 0.22 s; best near 1,000 values, slower above about 8,000). The video doesn't
  name TPC-H, CWI or MonetDB.
- "Compare several amounts in one instruction" is SIMD, not named. The plain loop's remaining 6x is the next section.
- The five strip amounts and their sums are picked for the picture; the demo's data isn't shown.
- PostgreSQL is spoken through a scene SAY rule ("post-gress"), because sfz's "postgres" comes out as "POST-gurz".
