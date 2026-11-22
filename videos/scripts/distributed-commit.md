# The reader who isn't sure: clocks that disagree, and a read that starts over

- Slug / scene: `distributed-commit`, `videos/scenes/distributed_commit.py:DistributedCommit`
- Lesson: `cons-06`, section 3, "CockroachDB: no special clocks, so the reader handles the doubt"
- Audience / level: a complete newcomer. Has sent money in a banking app; doesn't know what a timestamp, a snapshot
  read, a clock offset or an uncertainty interval is.
- Length: 4:23 (~700 words of narration, two pauses)
- Poster: `POSTER=164` (the restart: window -1 to 19 on the axis, batch 1 at 10 inside it, "read @ 10",
  "payouts = 1, ledger = 1")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: I sent the money and the app said Sent, so how can my friend's app, a second later,
  show a world where I hadn't paid?
- Misconception to steelman and break: "stamp each write with its server's clock and read everything stamped before
  the read began". Broken by the lab's TRUST_CLOCK run: the audit reads at -1 and misses batch 1, stamped 10 and
  already paid.
- Concept chain: timestamps from clocks that disagree → a stale read → a promised bound on the disagreement → values
  inside the reader's window are uncertain → move the read up past them and read again → the bound must hold, and it
  sets the price (hardest last)
- Analogy family: the lesson's bank branches: clerks stamping deposit slips by their own clocks, an auditor counting
  slips stamped before the audit began, and starting over for a slip stamped just after.
- Open loops: the friend's empty app, planted in scene 1 → named in scene 3 ("that's your friend's empty app, with
  timestamps") → answered in scene 5.
- Assumptions: all lab numbers are the section's Try-it and the previous section's TRUST_CLOCK run (settle 10 ms
  fast, audit-0 10 ms slow; commit at 10; client told at 8 ms; audit at -1; window up to 19; restart at 10; 4 ms
  instead of 2). The video calls the lab's 2ε "the bound" (the most two clocks can disagree), which plays the max
  offset's role. The check's "stamped 23" is a made-up value for the question.

## The one picture

Top: the writer (green, first "branch clerk", then "settle") and the reader (blue, first "auditor", then "audit-0"),
with "true time" between them. Middle: a timestamp axis from -5 to 25 ms; chips on dashed stems mark batch 1 (green)
and the read timestamp (blue); a teal band under the axis is the read's uncertainty window. Under it, what the audit
read. Captions top and bottom.

## Scene 1 · The question · [QUESTION] [LOOP-PLANT]

VO: Picture paying a friend back. You send 20.00, your app says Sent, and you text them: done. They open their app a second later, and the money isn't there. Then it appears. For a moment, their app showed a world where you hadn't paid. How does a database spread over many machines end up showing that? Hold that question.

SCREEN: "you: Sent", then "your friend, a second later: nothing yet", then "20.00"; the question in yellow.

## Scene 2 · The branches · [FAMILIAR] [ANALOGY] [MAP]

VO: Think of bank branches in different towns. Each clerk stamps deposit slips with the branch's own wall clock. An auditor notes the time the audit starts, and counts every slip stamped before it. If the clocks agree, that works. But clocks never quite agree. A slip stamped by a fast clock can look newer than an audit that really started after it.

SCREEN: The clerk box ("clock: a little fast") and the auditor box ("clock: a little slow"); "a fast clock's slip can look newer than a later audit".

## Scene 3 · Trust the clocks, in the lab · [SHRINK] [SHOW] [BREAK] [LOOP-PAYOFF]

VO: Now the lab's version. Two servers: settle pays batch 1 of the nightly payout, and its clock runs ten milliseconds fast. audit-0 runs an audit, a report that checks the books, and its clock runs ten milliseconds slow. Settle commits batch 1 at timestamp 10, its own clock reading. At 8 milliseconds of true time, the client hears: paid. One millisecond later, the audit starts. Its clock reads minus 1, so it reads everything stamped up to minus 1. Batch 1, stamped 10, looks like the future. The audit reads payouts: zero. Well. The batch was paid before the audit began, and the audit missed it. That's your friend's empty app, with timestamps.

SCREEN: The boxes become settle (10 ms fast) and audit-0 (10 ms slow); the axis draws; "batch 1 @ 10"; "true time: 8 ms", "client told: paid"; "read @ -1"; "audit reads payouts = 0" in red.

## Scene 4 · The wish · [WISH]

VO: There are fixes that make every writer pay. A head office can hand out every stamp by phone, or every clerk can wait out the clock's error before saying done. But what if writers don't wait at all, and the reader handles the doubt?

SCREEN: "fixes that make every writer pay"; "wanted: writers never wait; the reader handles the doubt".

## Scene 5 · The bound, the window, predict · [PREDICT] [PAUSE] [SHOW] [ANALOGY]

VO: That's what CockroachDB does, a SQL database that runs on ordinary servers with ordinary clocks. It promises a bound on how far any two clocks may disagree. So a reader at timestamp T knows that anything stamped above T plus that bound was written after it began. Anything in between is uncertain: it may have committed first, on a server whose clock runs ahead. In the lab the bound is 20 milliseconds, so the audit's window runs from minus 1 up to 19. Batch 1 is stamped 10. Inside the window, or outside? And what should the audit do? Pause and guess.

(three seconds)

Inside. The audit can't tell whether that payment came before it or after, so it can't skip it. It moves its own read timestamp up to 10, and reads again: payouts 1, ledger 1. One restart. The audit took 4 milliseconds instead of 2, and the writer still answered at 8. It's the auditor who finds a slip stamped just after the audit began, and starts over to count it in.

SCREEN: Teal CockroachDB caption; "above T + bound: surely written after"; the band "uncertain: -1 to 19"; countdown; batch 1 pulses; "read @ 10", "restarts at 10"; "audit reads payouts = 1, ledger = 1"; "the writer: 8 ms, no wait; the audit: 4 ms instead of 2".

## Scene 6 · The names · [NAME]

VO: That window is called the uncertainty interval, and the bound is the max offset. The top of the window stays put when the read moves up, so the restarts must end. The writes themselves go in as intents, provisional values, plus one transaction record that says commit or abort. With parallel commits, the transaction counts as done once every intent has reached agreement: one round instead of two.

SCREEN: Teal "the window: the uncertainty interval; the bound: the max offset"; "writes: intents + one transaction record"; "parallel commits: one round instead of two".

## Scene 7 · The guardrail · [GUARDRAIL]

VO: Now, the fine print. The max offset is 500 milliseconds by default, and 250 is suggested for clusters spread over several regions. The bound has to hold, so a server whose clock is off from at least half the others by 80% of it shuts itself down, rather than give wrong answers. If clocks drift past it anyway, real-time order can break. And here the branch picture breaks too. Clerks would recount for seconds. Servers do it for milliseconds, thousands of times a second, so clock error becomes a cost you can measure, paid by reads of recently written keys.

SCREEN: "max offset: 500 ms by default, 250 suggested across regions"; red "a clock off by 80% of the bound: that server shuts itself down"; "clocks past the bound: real-time order can break"; "restarts cost reads of keys written within the last max offset".

## Scene 8 · The moral, and a check · [MORAL] [PREDICT] [PAUSE] [RECAP]

VO: So the moral of the story: the bound on the clock's error, not the clock's reading, sets the price. Know your bound. One quick check. The audit reads at minus 1 again, with its window up to 19. Suppose batch 1 were stamped 23 instead. Restart, or not? Pause and think.

(three seconds)

No restart. 23 is above the window's top, so it was surely written after the audit began. The audit can skip it with a clear conscience.

SCREEN: The moral in yellow; the read back at -1, batch 1 moved to 23; countdown; "above the window: surely later, safe to skip"; last caption "only the uncertain values cost a restart".


---

### Beat check

QUESTION (1) → FAMILIAR/ANALOGY/MAP (2) → SHOW and the wrong model broken (3) → WISH (4) → the bound, PREDICT +
PAUSE, SHOW, the analogy's auditor starting over (5) → NAME (6) → GUARDRAIL and where the analogy breaks (7) →
MORAL and a check with PAUSE (8). Light moments: "That's your friend's empty app, with timestamps" (3), "skip it with
a clear conscience" (8).

### Accuracy notes for the producer

- TRUST_CLOCK numbers (commit timestamp 10, client told at 8 ms, audit at 9 ms reading at -1, payouts = 0) are the
  previous section's Try-it; RESTART numbers (window up to 19, restart at 10, payouts = 1, ledger = 1, 4 ms instead
  of 2) are this section's.
- The lab's window is 2ε above the reader's clock; CockroachDB's is the max offset. The video calls both "the bound".
- "A head office" and "waiting out the clock's error" are the previous two sections (a timestamp oracle; Spanner's
  commit wait), named only in passing.
- Hybrid logical clocks are left to the lesson. The real error is `ReadWithinUncertaintyIntervalError`; a restart
  keeps going only if the earlier reads still hold at the new timestamp, otherwise the transaction restarts.
- Max offset 500 ms default, 250 ms suggested for multi-region; the 80%-of-max-offset self-shutdown rule; real-time
  order can break past the bound; parallel commits (STAGING record, one round of consensus): all from the section.
- The check's "stamped 23" is outside the window's top (19), so the read can skip it: anything above T + max offset
  was written after the read began.
