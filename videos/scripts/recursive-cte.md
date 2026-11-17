# Round after round of phone calls: the recursive CTE is a loop

- Slug / scene: `recursive-cte`, `videos/scenes/recursive_cte.py:RecursiveCte`
- Lesson: `model-07`, section 1, "WITH RECURSIVE: the loop, written as one query"
- Audience / level: a complete newcomer. Can read a little code (a loop); knows nothing about SQL joins or CTEs.
- Length: about 4:45 (~730 words of narration, two guesses, silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: how do you ask a database for everyone below Asha in a chain of invitations, when you
  don't know how deep the chain goes?
- Misconceptions to steelman and break: (1) "one join per level is fine, the data has fixed levels" (right today; the
  day Farid invites a friend, the level query never looks there, with no error); (2) "recursive means something calls
  itself" (it's a while loop over a working table; the PostgreSQL docs call it iteration)
- Concept chain: a self-pointing column makes a forest → one level is one step, levels must be known in advance → the
  phone-call rounds (only call the people from the last round, stop when a round names nobody) → WITH RECURSIVE: anchor,
  recursive term, UNION ALL → the working table → the whole forest stops by itself (hardest: predict the rounds) → it
  can't count inside the loop, and it has no built-in limit
- Analogy family: phone calls. Call Asha and ask whom she invited; call each person she named; each round you call only
  the people you heard about in the round before; a round that names nobody new means you're done. The list of people
  from the last round is the working table. Where it breaks: if the data loops back, the calls never end (a later
  section adds the guard).
- Open loops: "the answer quietly leaves them out" planted in scene 1 → paid off by the loop with no depth in scene 7
- Assumptions: all data is the lesson's seed (13 customers, 5 roots 1, 2, 7, 9, 11; first names from the seed), the
  anchor and rounds are the stepper's, Asha's five rows are the Try-it's output (path column left out), and 50,000
  customers in 8 rounds and about 40 ms is the lesson's large data set. "A new friend" under Farid is hypothetical, as in
  the lesson's opening.

## The one picture

Left: the forest of 13 customers drawn as circles by depth (0 at the top), lines from each inviter down to the people
they invited; Asha's tree in front, the others dimmed at first. In scene 4 the left side shows the query instead, then
the forest returns. Right: the "to call this round" box, renamed "working table" (yellow), and the result box below it.
Bottom: the round strip (what this round asks on the left, what it found on the right). Yellow is the current round's
callers, green the people found, red a miss or an error.

## Scene 1 · Asha's thank-you · 0:00–0:35 · [QUESTION] [LOOP-PLANT] [JOKE:soften]

VO: Picture a café app that gives you a free coffee for inviting a friend. Asha invited Chloe and Elena, and each of them
invited a friend. Now the company wants to thank Asha for her whole chain: everyone who joined through her, at any
distance. The first query people write counts by levels: her friends, then her friends' friends, one more step for each
level. It's right today. Then someone at the bottom invites a friend, and the answer quietly leaves them out. No error.
Just one person short.

SCREEN: Title card. Asha's tree draws in (Asha; Chloe and Elena; Farid and Jonas). Strip: "thank Asha: everyone below
her, at any distance".

## Scene 2 · One step per level · 0:35–1:20 · [FAMILIAR] [PAIN] [BREAK]

VO: Here's the data. The app's database is PostgreSQL, a free database program. Its customers table has 13 rows, and a
column, referred_by, that holds the id of whoever invited each customer, or NULL when nobody did. Draw those pointers and
you get trees: a forest of five, with Asha at the top of one. Asha's chain is two levels deep today, so the level query
asks two levels. The day Farid invites a friend, there's a third level, and the query never looks there.

SCREEN: A small table sketch (customer_id, full_name, referred_by) for Chloe (1), Farid (3) and Asha (NULL); the rest of
the forest fades in. A translucent band covers depths 0 to 2 under Asha ("the level query looks here"); a dashed "?"
node, "a new friend", appears under Farid at depth 3, outside the band, with a red cross.

## Scene 3 · Phone calls · 1:20–2:00 · [ANALOGY] [MAP] [SHRINK]

VO: How would you do it by hand? With a phone. Call Asha: whom did you invite? Chloe and Elena. Then call each person she
named. Chloe says Farid, Elena says Jonas. Call those two: nobody. A round that names nobody new means you're done.
Notice the rule. In each round, you only call the people you heard about in the round before. You never needed to know
how deep the chain was.

SCREEN: The "to call this round" box shows Asha, then Chloe and Elena, then Farid and Jonas, then "nobody: stop". Callers
glow yellow, the people they name turn green. The result box fills with names.

## Scene 4 · The loop, written as one query · 2:00–3:00 · [NAME] [MAP] [SHOW] [JOKE:is-the-explanation]

VO: SQL can run that loop inside one query. WITH gives a query a name, here downline, and RECURSIVE lets that query read
itself. The whole thing is called a recursive common table expression, or CTE. The first part, the anchor, is where the
loop starts: Asha, at depth 0. The second part, the recursive term, takes one step down: customers whose inviter is
already in downline. UNION ALL stacks the two parts into one result. PostgreSQL runs it with a working table: the people
you heard about in the last round of calls. Run the anchor once. Then run the recursive term, reading only the working
table. Its new rows join the result and become the next working table. Repeat until a round comes back empty. So despite
the name, nothing calls itself. The PostgreSQL docs call it iteration. Recursive is the name on the box; inside, it's a
while loop.

SCREEN: The forest gives way to the query (the lesson's, comments left out). The anchor lines get a gold frame, the
recursive term a teal frame, UNION ALL glows. The right box is renamed "working table". The walk replays: {1}; {3, 5};
{6, 10}; empty. The result shows the Try-it's five rows (1 Asha Rao 0, 3 Chloe Martin 1, 5 Elena Petrova 1, 6 Farid Haddad
2, 10 Jonas Weber 2). Caption "recursive on the box; a while loop inside".

## Scene 5 · The whole forest · 3:00–3:45 · [PREDICT] [PAUSE] [SHOW]

VO: Now start from all five roots at once: everyone nobody invited. How many times does the recursive term run before the
loop stops? Pause and guess. (three seconds) Round one finds 3, 4, 5 and 12. Round two finds 6, 8 and 10. Round three
finds only Mateo. Round four finds nobody, and the loop ends with all 13 customers. Four runs, and the last one finds
nothing. Nobody wrote a stop condition. The data running out is the stop. On a copy with 50,000 customers, the whole
forest takes 8 rounds and about 40 milliseconds.

SCREEN: The forest returns, all trees lit. Working table {1, 2, 7, 9, 11}; countdown. Then {3, 4, 5, 12}, {6, 8, 10},
{13}, "empty: stop", each round's nodes turning green in the forest. The result box holds "depth 0: 1 2 7 9 11" to "depth
3: 13", "13 rows". Caption "50,000 customers: 8 rounds, about 40 ms".

## Scene 6 · Two things the loop can't do · 3:45–4:25 · [GUARDRAIL] [BREAK of the analogy] [JOKE:release]

VO: Two things follow from the working table. First, each round sees only the last round's rows, never the whole result.
So it can't count. Put count in the recursive term and PostgreSQL refuses. Count in the main query, after the loop.
Second, there's no built-in limit. The loop stops when a round comes back empty, and only then. SQL Server, Microsoft's
database program, stops after 100 levels by default. PostgreSQL doesn't. If the data ever loops back on itself, you'll
be making calls until the battery dies. A later section adds the guard.

SCREEN: The working table glows; the PostgreSQL error in red mono, "aggregate functions are not allowed in a recursive
query's recursive term"; "count in the main query, after the loop". Then a dashed red arrow from Mateo back up to Ben,
marked "if the data loops back"; captions for SQL Server's 100 and PostgreSQL's no limit.

## Scene 7 · The moral, and a check · 4:25–5:00 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, Asha's thank-you. The loop has no depth written in it: start somewhere, take one step from the rows you found
last, and stop when a step finds nothing. One quick check. Start the walk from Ben instead. How many rows come back, and
how many rounds find someone? Pause and think. (three seconds) Four rows: Ben, Daniel, Hugo and Mateo. Three rounds find
someone, and a fourth finds nobody.

SCREEN: Caption with the moral. Ben's chain lit; countdown; Ben, Daniel, Hugo, Mateo turn green one round at a time and
the working table ends "empty: stop".

---

### Beat check

- Opens with QUESTION (scene 1); FAMILIAR + PAIN + BREAK of the level query (scene 2).
- ANALOGY + MAP (scene 3) before the names CTE, anchor, recursive term, working table (scene 4).
- PREDICT with PAUSE: the forest's rounds (scene 5) and the check (scene 7), each followed by SHOW.
- GUARDRAIL (scene 6) and MORAL (scene 7) last. Light moments: "no error, just one person short" (0:30), "the name on the
  box" (2:55), "until the battery dies" (4:20).

### Accuracy notes for the producer

- Asha's five rows are the Try-it output (the `path` column is left out); the forest's rounds are the stepper's.
- "A new friend" under Farid is hypothetical, as the lesson's opening is ("someone at the bottom invites a friend").
- The level query is described as "asking two levels", not as a count of joins (the first level is a filter, each level
  after it one more self join).
- The error text is the lesson's quote. SQL Server's default of 100 levels and PostgreSQL's lack of one are the
  lesson's.
- 50,000 customers, 8 rounds (`loops=8`, the eighth finding nobody) and about 40 ms are the lesson's large data set.
- Left to the lesson: EXPLAIN ANALYZE and the WorkTable Scan, the calendar of days made from nothing, paths and cycle
  guards (later sections).
