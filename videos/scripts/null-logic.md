# Where did 5 customers go? NULL is a sealed envelope

- Slug / scene: `null-logic`, `videos/scenes/null_logic.py:NullLogic`
- Lesson: `sql-01`, section 3, "NULL means unknown, and WHERE keeps only true"
- Audience / level: a complete newcomer. Knows the lesson's opening (13 customers, a free coffee for everyone Asha
  didn't invite) and that a query asks the database for rows; knows nothing about NULL or logic with three answers.
- Length: 4:18 (~665 words of narration, plus two guesses and silent builds)
- Poster: `POSTER=139.8` (all 13 rows tested: five envelopes unknown and dropped, "got: 6 of 13")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: the question reads like plain English and the database answered without an error,
  so why are 5 customers missing?
- Misconceptions to steelman and break: (1) "an empty cell can hold 0 or -1" (broken: there is no customer 0, and a
  count would count Kofi); (2) "a NULL row is simply not equal to 1, so it stays" (broken by predict-then-show:
  `NULL <> 1` is unknown, and WHERE drops unknown)
- Concept chain: the column and the empty cell → NULL, a marker for "no value here" → the sealed envelope: unknown,
  three-valued logic → WHERE keeps only true (hardest) → the rules for NULL = NULL, IS NULL, OR, AND, NOT → say
  what you mean (IS DISTINCT FROM, OR IS NULL, NOT NULL) → Kotlin's null, grouping, counting
- Analogy family: a sealed envelope. There may be a number inside, nobody can see it, so "is it 1?" can only be
  answered "can't tell". IS NULL asks "is this a sealed envelope?", which always has an answer. Where it breaks:
  grouping and sorting put all the NULLs together, as if they were equal.
- Open loops: "where did the other 5 go?" planted in scene 1 → answered in scene 4 (five envelopes, five rows gone)
  and fixed in scene 6 (11 rows); the check in scene 8 finds the 5 again from two counts.
- Assumptions: the 13 rows are the course database's seed (`labs/env/postgres/course/seed.sql`): NULL for customers
  1, 2, 7, 9 and 11; 1 for Chloe (3) and Elena (5); someone else for the other 6. Counts are the lesson's: 6 and 11;
  `count(*)` 13, `count(referred_by)` 8.

## The one picture

Left: the customers table, all 13 rows (id, name, referred_by), with the five empty cells drawn as sealed envelopes
once the analogy arrives. Top: the query in a bar, and the result on the right ("expected: 11", "got: 6"). Right,
next to each row: the test's answer (true green, false red, unknown yellow) and what WHERE does with it (kept,
dropped). The same right-hand space holds the big envelope, the rules and the counts when the row columns are put
away. Kept rows have a green outline; dropped rows dim.

## Scene 1 · A free coffee · 0:00–0:30 · [FAMILIAR] [QUESTION] [LOOP-PLANT]

VO: A small company's app records card payments, and it lists its 13 customers, noting who invited each one. Asha's
two friends got a free coffee when they joined with her invitation. Now the company wants to send one to everybody
else: every customer Asha didn't invite. That should be 11 people. You ask the database, and it answers at once,
with no error: 6. Where did the other 5 go?

SCREEN: Title card. The 13 rows draw in; referred_by shows numbers, and a short dash where nobody invited the
customer. Chloe and Elena (referred_by 1) light up. "expected: 11"; the query bar `SELECT * FROM customers WHERE
referred_by <> 1`; "got: 6" in red; caption "expected 11, got 6: where did 5 go?".

## Scene 2 · What goes in an empty cell? · 0:30–1:05 · [PAIN] [WISH] [NAME]

VO: Look at the column. referred_by holds the id of the customer who invited this one. Asha is customer 1, so Chloe
and Elena hold 1. But Kofi, customer 11, signed up without an invitation. What should his referred_by hold? Try 0.
There's no customer 0, and the table's rule that referred_by must name a real customer rejects it. And a count of
invited customers would count Kofi. Try -1: the same problems, and every query must remember what -1 means. SQL's
answer is a marker that means no value here: NULL.

SCREEN: On the right, a card "Kofi Mensah, customer 11 / referred_by = ?", while Kofi's cell becomes "?", then a
red "0", then a red "-1". Under the card, each try gets a line and a cross: "0: no customer 0; a count would count
Kofi", "-1: the same, and every query must remember it", then "NULL: a marker for: no value here" in gold. On
"NULL", all five empty cells read NULL.

## Scene 3 · A sealed envelope · 1:05–1:50 · [ANALOGY] [MAP] [NAME] [JOKE:is-the-explanation]

VO: Picture NULL as a sealed envelope. There may be a number inside, but nobody can see it. Is the envelope equal to
1? The honest answer is: can't tell. And that's what SQL says. Ask whether NULL equals 1, and SQL doesn't say false.
It says NULL again, which here means unknown. Honestly, NULL should have been called don't know. Every rule makes
sense once you read it that way. So SQL has three answers: true, false and unknown. That's called three-valued
logic.

SCREEN: The five NULLs turn into small sealed envelopes. A big envelope on the right wiggles; "= 1 ?"; "can't tell",
then "NULL, which here means unknown". Caption "read NULL as: don't know". The three answers appear in green, red
and yellow.

## Scene 4 · WHERE keeps only true · 1:50–2:40 · [PREDICT] [PAUSE] [SHOW] [BREAK] [NAME] [JOKE:release] [LOOP-PAYOFF]

VO: Now the query. WHERE runs its test once for each row. Does a row with a sealed envelope stay or go? Pause and
guess. (three seconds) Asha, customer 1: NULL not equal to 1 is unknown. And here's the rule that bites: WHERE keeps
a row only when its test is true. False drops it, and unknown drops it too. So Asha goes, though she certainly
didn't invite herself. Chloe: 1 not equal to 1 is false, so she goes, correctly. Daniel: 2 not equal to 1 is true,
so he stays. And so on, down the table. Five envelopes, five rows gone, with no error and no warning. 6 of 13.

SCREEN: Two new columns, "referred_by <> 1" and "WHERE". The envelopes pulse; countdown bar. Row by row: unknown →
dropped (dimmed, red outline), false → dropped, true → kept (green outline). The rule as a caption. The other nine
rows run quickly. The five envelope rows pulse red; "got: 6 of 13".

## Scene 5 · The rules · 2:40–3:15 · [SHOW]

VO: A few rules follow from the envelope. Any comparison with NULL is unknown, even NULL equals NULL: two sealed
envelopes may or may not hold the same number. IS NULL asks a different question: is this a sealed envelope? That
always has an answer. When tests are joined with OR, or with AND, a side we already know can decide on its own. true OR unknown is true, whatever the
envelope holds. false AND unknown is false. And NOT unknown is still unknown.

SCREEN: The row columns fade; a panel lists `NULL = NULL → unknown`, `NULL IS NULL → true`, `true OR unknown →
true`, `false AND unknown → false`, `NOT unknown → unknown`, one per sentence.

## Scene 6 · Say what you mean · 3:15–3:45 · [SHOW] [GUARDRAIL]

VO: So say what you mean. referred_by IS DISTINCT FROM 1 treats NULL as an ordinary value. An envelope is distinct
from 1, so the test is true, and the five come back: 11 rows, everyone Asha didn't invite. Writing not equal to 1, OR
referred_by IS NULL, does the same. And if a column should never be empty, declare it NOT NULL, and the question
never comes up.

SCREEN: The query bar becomes `... WHERE referred_by IS DISTINCT FROM 1`; the test column header changes; the five
envelope rows turn true and kept; "got: 11" in green. Captions for the two other fixes.

## Scene 7 · Two warnings, and counting · 3:45–4:20 · [GUARDRAIL] [BREAK of the analogy]

VO: Two warnings. If you write Kotlin or Java, this feels wrong, because there, null equals null is true. SQL spells
that kind of equal: IS NOT DISTINCT FROM. And the envelope picture breaks in one place: when SQL groups or sorts
rows, it puts all the NULLs together, as if they were equal. Counting has its own rules. count(*) counts rows: 13.
count(referred_by) counts the filled-in values: 8. And sum over no rows at all is NULL, not 0.

SCREEN: Captions for Kotlin and IS NOT DISTINCT FROM; the five envelopes nudge sideways together for grouping. A
panel: `count(*) → 13`, `count(referred_by) → 8`, `sum over no rows → NULL`.

## Scene 8 · The moral, and a check · 4:20–4:50 · [MORAL] [PRINCIPLE] [PREDICT] [PAUSE]

VO: So: NULL is a sealed envelope, any comparison with it is unknown, and WHERE keeps only true. Next time a filter
says not, ask which side can be empty. One quick check. count(*) says 13, and count(referred_by) says 8. How many
customers would a careless not equal lose? Pause and think. (three seconds) 5. The gap between the counts is the
number of sealed envelopes, and every one of them falls out.

SCREEN: The moral as captions. The two counts pulse; countdown bar. "13 - 8 = 5" appears and the five envelope rows
glow.

---

### Beat check

- Opens with FAMILIAR and QUESTION (scene 1); PAIN and WISH (0 and -1, scene 2) before the name NULL.
- ANALOGY and MAP (scene 3) before "unknown" and "three-valued logic"; its break said in scene 7.
- PREDICT with PAUSE: scene 4 and the check in scene 8, each followed by SHOW.
- BREAK: the made-up values (scene 2), "a NULL row is not equal to 1" (scene 4).
- GUARDRAIL: the fixes and NOT NULL (scene 6), the Kotlin habit, grouping and counting (scene 7). MORAL last.
- Light moments: "NULL should have been called don't know" (1:35), "she certainly didn't invite herself" (2:15).

### Accuracy notes for the producer

- Rows, names and referred_by values are the course seed. On the whole table `<> 1` returns 6 and `IS DISTINCT FROM 1`
  returns 11; `count(*)` is 13 and `count(referred_by)` is 8, as the lesson prints.
- "The table's rule that referred_by must name a real customer" is the lesson's foreign key, named in plain words.
- The test column shows `referred_by <> 1`; the narration says "not equal to". In psql, NULL prints as whatever
  `\pset null` sets; the video draws envelopes.
- `true OR unknown`, `false AND unknown` and `NOT unknown` are the lesson's query (`true OR NULL`, `false AND NULL`,
  `NOT NULL::boolean`). `count(DISTINCT referred_by)` (7) and `avg`, `min`, `max` skipping NULLs are left to the
  lesson, as are the details of grouping and sorting (its Go deeper).
- "sum over no rows is NULL" is the lesson's Try it on shop 6, Paper Lantern Books, which has no payments.
