# Three failures in a row? Number twice and subtract

- Slug / scene: `gaps-islands`, `videos/scenes/gaps_islands.py:GapsIslands`
- Lesson: `sql-07`, section 3, "Three failed logins in a row: number the rows twice and subtract"
- Audience / level: a complete newcomer. Has met a table, GROUP BY and window functions (row_number) once in earlier
  lessons, and nothing else.
- Length: 4:54 (~790 words of narration at the Kokoro voice's ~180 wpm, plus a guess, a check and the
  silent moves)
- Poster: `POSTER=291` (the last frame: both strips counted, every island braced, Jonas's last id answered)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: a database compares values. How can it see "in a row"?
- Misconceptions to steelman and break: (1) "GROUP BY customer and outcome counts the failures": breaks on Jonas,
  four failures but never three in a row. (2) "keep only the failures first, then number them": less work, and it
  glues Jonas's two pairs into one island of four.
- Concept chain: GROUP BY sees equal values, not neighbours → a label that stays the same along a run is needed → two
  counters move together inside a run and drift apart across one → their difference is the island id → group by it →
  number first, filter after → the id means something only within one customer and one outcome (hardest last)
- Analogy family: the lesson's receipt picture (islands are runs of receipts of one colour), extended with two hand
  clickers walking down the pile: one clicks on every receipt, one clicks only for the receipt's own colour.
  Breaks on time: "in a row" here means the next receipt, not "soon after".
- Open loops: "how does it see in a row?" planted in scene 1 → answered in scene 9; Jonas locked out by GROUP BY in
  scene 2 → set free in scene 6, locked out again by the filter-first idea in scene 7.
- Assumptions: Elena's nine logins and Jonas's six are the seed's (customers 5 and 10); every counter, difference and
  island is the lesson's figure and Try it output (re-run in SQLite on the seed). Times are the seed's.

## The one picture

Two strips of login slips, oldest on the left: Elena (customer 5, nine slips) on top, Jonas (customer 10, six slips)
below. Green slips with a tick are successes; red slips with a cross are failures. Above each strip, the first
counter (blue, every login); below it, the colour counter (gold, same outcome); below that, the difference
(white, the island id). Row labels on the left say what each row is. Braces under a run give its folded result.
Same places and colours from start to end.

## Scene 1 · In a row · 0:00–0:35 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: A payments app records every attempt to log in: who tried, when, and whether the password was right. The security team
wants a rule: three failed logins in a row, and the account gets locked. First, they want to see every run of
failures, with its length. Here's Elena's history, oldest first. Two successes. Then six failures in two minutes, from
an address she had never used. Then her own success. It looks like someone guessing her password. A database compares
values. So how does it see in a row?

SCREEN: Elena's nine slips appear left to right; the six reds pulse with "6 failures in 2 minutes, from an address
she had never used". Caption "three failures in a row: lock the account". A yellow "in a row?".

## Scene 2 · GROUP BY counts, but can't see neighbours · 0:35–1:16 · [FAMILIAR] [PAIN] [BREAK] [WISH] [JOKE:amplify] [LOOP-PLANT]

VO: The first thing to try is GROUP BY: one pile per customer and outcome, then count each pile. For Elena, that's three
successes and six failures. But her three successes came from two separate runs, and the count can't tell. Jonas is
worse off. He failed twice in April and twice in June, with a success after each pair. GROUP BY counts four failures,
and locks him out. He never failed three times in a row. He forgets his password now and then, like the rest of us.
GROUP BY sees which rows share a value. It can't see whether they sit next to each other. We need a label that stays
the same along a run, and changes when a new run starts.

SCREEN: Copies of Elena's slips fly into two chips under her strip: "successes: 3", "failures: 6"; her first two
and last success glow as two runs. Jonas's strip appears; a red chip "failures: 4: locked out?". Caption "GROUP BY
sees equal values, not neighbours".

## Scene 3 · Two clickers · 1:16–2:04 · [ANALOGY] [MAP] [JOKE:pivot]

VO: Picture each login as a paper receipt, in a pile sorted by time: green for a success, red for a failure. A run is a
stretch of receipts of one colour. Now walk down the pile with two hand clickers, the kind people use to count
visitors at a door. The first clicks on every receipt. The second clicks only for the receipt's own colour: it keeps
one count for reds, and one for greens. Along a red run, both clickers move together, so the gap between them stays
the same. Pass a green receipt, and only the first one moves. So the next red run gets a bigger gap. Let's map it. A
receipt is a row. The pile's order is the time order. The first clicker numbers every row. The second numbers rows
with the same outcome. And the gap is the label we wanted.

SCREEN: Row labels appear on the left: "clicker 1: every receipt" (blue), "clicker 2: its own colour" (gold), "the
gap" (white), with "time →" under Elena's strip. Mapping captions one by one.

## Scene 4 · Try it on Elena · 2:04–2:43 · [SHRINK] [PREDICT] [PAUSE] [SHOW] [JOKE:release]

VO: Let's try it on Elena. The first clicker numbers her logins 1 to 9. The colour clicker gives her successes 1 and 2,
her failures 1 to 6, and her last success 3. Now subtract. On her six failures, what's the first number minus the
second? Pause and guess.

(three seconds)

2, on all six. 3 minus 1, 4 minus 2, all the way to 8 minus 6. Her first two successes get 0, and her last success, 9
minus 3, gets 6. Same difference, same run. Subtraction: the hardest maths you'll do today. And it's enough.

SCREEN: Blue 1 to 9 above the slips, one by one; gold 1, 2 / 1 to 6 / 3 below; a yellow "?" in each failure's
difference slot; countdown. Then 2 on all six, 0 0, 6; a brace under the red run: "one run, one number: 2".

## Scene 5 · Now the names · 2:43–3:07 · [NAME]

VO: Now the names. A run of equal values with nothing else between them is called an island. The places where the value
changes are the gaps. The difference is the island id. In SQL, each clicker is row_number, a window function that
numbers rows 1, 2, 3 in order. Number every login by time, number them again within the same outcome, and subtract.

SCREEN: Labels become "island", "gap" (thin marks between runs), row labels become "row_number(): all", "row_number():
same outcome", "island id". Two lines of SQL at the bottom: `row_number() OVER (PARTITION BY customer_id ORDER BY
occurred_at)` and `- row_number() OVER (PARTITION BY customer_id, success ORDER BY occurred_at)`.

## Scene 6 · Fold the islands · 3:07–3:36 · [SHOW] [LOOP-PAYOFF]

VO: Jonas, the same way. Every login: 1 to 6. Failures: 1 and 2, then 3 and 4. His April pair gets 0, and his June pair
gets 1. Now group by customer, outcome and island id, and each island folds into one row with a count. Elena: one
island of six failures, all inside two minutes. Jonas: two islands of two. A rule of three in a row locks Elena's
account, and leaves Jonas alone.

SCREEN: Jonas's counters fill (his last slip's difference stays blank for the check). Braces: Elena "island 2: 6
failures, 19:52:00 to 19:53:40"; Jonas "island 0: 2 failures" and "island 1: 2 failures". Elena's brace turns red with
"locked", Jonas's green.

## Scene 7 · Filter first? · 3:36–4:00 · [BREAK] [JOKE:soften]

VO: You might think: why number the successes at all? Keep only the failures, then number those. To be fair, it's less
work. But look at Jonas. With the successes gone, his four failures sit next to each other. Both clickers count 1 to
4, every difference is 0, and he's one island of four again. Locked out. So number every login first. Only then keep
the failures.

SCREEN: Jonas's greens fade; his four reds slide together; counters 1 2 3 4 / 1 2 3 4 / 0 0 0 0; red brace "one
island of four: locked out". Caption "number every login first; keep the failures after". Then everything slides back.

## Scene 8 · Two limits · 4:00–4:26 · [GUARDRAIL]

VO: One more trap. An island id only means something inside one customer and one outcome. Elena's first success run is
island 0, and so is Jonas's April failure run. So group by customer and outcome too. And in a row here means the next
row. Sometimes it means soon after, like failures a minute apart. That needs gaps measured in time, which the next
section draws.

SCREEN: Elena's two 0s and Jonas's two 0s glow; caption "island 0 + island 0: group by customer and outcome too".
Then "in a row = the next row; soon after = a gap in time (next section)".

## Scene 9 · The moral, and a check · 4:26–4:54 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So how does a database see in a row? Count every row, count again within the colour, and subtract. Same difference,
same island. One quick check. Jonas's last login is number 6 overall, and his second success. What's its island id?
Pause and think.

(three seconds)

4. 6 minus 2. A new success island, not his first one, island 2.

SCREEN: Caption "count all, count within the colour, subtract". Jonas's last slip glows, its "?" sits in the
difference row; countdown; then 4 (yellow), and the final caption "same difference, same island".

---

### Beat check

- QUESTION from a felt rule (scene 1); FAMILIAR GROUP BY broken on Jonas (scene 2) with the WISH.
- ANALOGY + MAP (scene 3) before any name; PREDICT with PAUSE and SHOW (scene 4); NAME after (scene 5).
- SHOW and loop payoff (scene 6); the second wrong model steelmanned and BROKEN (scene 7).
- GUARDRAIL (scene 8) with the analogy's limit; MORAL and a check answerable from the picture (scene 9).
- Light moments: Jonas forgets his password like the rest of us (1:05), subtraction as the hardest maths you'll do
  today (2:40), "to be fair, it's less work" (3:40).

### Accuracy notes for the producer

- Elena (customer 5): events 4, 10, 11 to 16, 17: t t f f f f f f t. Counters 1 to 9; same-outcome 1 2 / 1 to 6 / 3;
  island ids 0 0 2 2 2 2 2 2 6, as in the lesson's figure. Her failure island: 6 failures, 19:52:00 to 19:53:40 on
  6 March (the Try it output).
- Jonas (customer 10): events 20, 21, 22, 25, 26, 27: f f t f f t. Island ids 0 0 2 1 1 4. Failure islands 0 and 1,
  two each (the Try it output). GROUP BY gives him 4 failures (the lesson's third query). Filtering first gives 0 on
  all four failures (re-run in SQLite).
- The lesson's CTE orders by `occurred_at, event_id` so ties can't make the numbering uncertain; the video's code
  shows `ORDER BY occurred_at` to fit on screen. None of these logins tie on time.
- The clickers are an extension of the lesson's receipt picture; in SQL, the "second clicker" is one row_number
  partitioned by success.
- Left to the lesson: sessions and streaks with gaps measured in time (section 4), and the address column.
- Spoken forms via `SAY`: row_number as "row number", GROUP BY in lower case. "From 19:52 to 19:53 and 40 seconds" was
  heard by Whisper as "42nds" even in isolation, so the line says "all inside two minutes"; the brace keeps the times.
