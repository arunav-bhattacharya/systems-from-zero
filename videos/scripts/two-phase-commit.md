# Where did the 30.00 go? Everyone promises, then one line decides

- Slug / scene: `two-phase-commit`, `videos/scenes/two_phase_commit.py:TwoPhaseCommit`
- Lesson: `txn-07`, section 1, "Two-phase commit: everyone promises first, then one line in a log decides"
- Audience / level: a complete newcomer. Can read a little code; knows nothing about databases, logs, locks or
  networks.
- Length: 5:25 (~880 words of narration, one pause for a guess, one for the check)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=174.5`, just after the commit point (both servers prepared with locks, both votes yes, `txf-1 COMMIT` in green
  in the coordinator, the reader line still showing 100.00 and 0.00)
- The learner's real question: one payment touches two machines. How can they agree to do both or neither, when
  either can crash?
- Misconception to steelman and break: "commit one side, then the other, and undo the first if the second fails"
  (broken by payouts crashing before its commit, and the undo being a refund that can fail too)
- Concept chain: one server commits with one log line → two servers have no single line → promise first (prepare,
  log, yes, keep the lock) → one line in the coordinator's log is the commit point → forward only → no line means
  abort (presumed abort) → two points of no return → the price in round trips and held locks (hardest last)
- Analogy family: the lesson's dinner by text. You ask each friend "Friday at eight? keep the evening free"; only
  when all say yes do you write "dinner is on" in your diary and text everyone; anyone says no, you text "off".
  Tags above the boxes keep the mapping on screen: you = coordinator, a friend = each server.
- Open loops: "both, or neither?" planted in scene 1 → paid off in scenes 4–5; "where did the 30.00 go?" scene 1 →
  scene 8; "what if the coordinator dies after the yeses?" planted in scene 7 → the lesson's next section
- Assumptions: numbers and ids are the lesson's (w-17 100.00 to 70.00, m-cafe 0.00 to 30.00, `wallets` and
  `payouts`, `txf-1`, the duplicate payout entry for the no vote, 70 ms round trip, 140 instead of 70).

## The one picture

Three boxes in a row: `wallets` (blue, left: row w-17 and its amount, a lock, its log on disk), the coordinator
(purple, centre: its answers, then its one log line), `payouts` (gold, right: row m-cafe, a lock, its log). Grey
links; yellow dots are requests, green dots yes and commit, red dots no and roll back. Under the boxes, "someone
reading both sees: wallet … café …". Captions at the bottom. Italic tags above the boxes once the dinner arrives.

## Scene 1 · The missing 30 · 0:00–0:25 · [QUESTION] [LOOP-PLANT]

VO: Picture paying for a coffee from the money you keep in a café chain's app, your wallet. The app says it went
through, and your wallet drops from 100.00 to 70.00. That evening, the café's owner checks what she's owed. Your
30.00 isn't there. It left your wallet, and never arrived. How can money leave one place and never land in the
other? And how do two machines agree to do both, or neither?

SCREEN: `wallets` box (w-17, 100.00 → 70.00), `payouts` box (m-cafe, 0.00 in red); the reader line 70.00 / 0.00.
Caption "both, or neither?".

## Scene 2 · One server is easy, two are not · 0:25–1:35 · [FAMILIAR] [PAIN] [BREAK] [WISH] [JOKE:understatement]

VO: The app keeps its records in a database, a program that stores rows of data, a bit like a spreadsheet. The
wallets live on one database server, a computer called wallets. The shops' balances live on another, called payouts.
On one server, this is easy. A transaction groups changes so that all of them happen, or none do. It commits,
becomes permanent, at one moment: when one line reaches the server's log on disk. But our payment has two halves, on
two disks. No single line can commit both.

So the obvious plan: commit the debit on wallets, then the credit on payouts. Now payouts crashes a moment before its
commit. You've paid 30.00, and the café got nothing. That's our missing money. Then undo the debit? By then, another
payment may already have been approved against your 70.00. Putting it back is a new transaction, a refund, and that
can fail too. Well... we've just moved the problem.

What we want is this: nobody commits until everybody has promised that they can.

SCREEN: "log on disk" areas appear; a green "commit" line in wallets' log. The obvious plan: wallets "debit, commit"
and 70.00; payouts "credit ..." then a red cross. Reset, caption "nobody commits until everybody has promised".

## Scene 3 · The dinner · 1:35–2:15 · [ANALOGY] [MAP]

VO: Picture organising a dinner by text. You ask each friend: Friday at eight? If you say yes, keep the evening
free. Only when everyone has said yes do you write dinner is on in your diary, and then text everyone. If anyone
says no, you text off. Let's map it. You're the coordinator: the program running the payment, which decides how it
ends. The friends are the participants: the servers that hold the data. And the whole thing gets one id that
everyone shares, txf-1.

SCREEN: The coordinator box and links draw in, tagged "you, organising"; the servers get "a friend" tags. Two yeses
come back; "diary: dinner is on" appears in the coordinator. Then it gets its title, "coordinator".

## Scene 4 · Phase one, and the commit point · 2:15–3:15 · [SHOW] [PREDICT] [PAUSE] [NAME]

VO: Phase one is prepare. The coordinator sends each server its changes, and asks: can you commit? wallets checks its
rules, writes the changes and a line saying prepared to its log, makes sure the disk has them, and answers yes. That
yes is a promise. Whatever happens next, even a crash and a restart, it will commit if told to. So it can't give up
on its own any more, and it keeps a lock on your wallet's row, a mark that stops anyone else changing it. That's the
friend keeping Friday free. payouts does the same, and says yes.

Both servers said yes, and neither has committed. So at what moment is the payment really committed? Pause and guess.

(three seconds)

The moment the coordinator writes one line to its own log, txf-1 COMMIT, and the disk has it. That one line is the
commit point. It's the note in your diary. Neither server has changed yet, but the outcome is fixed.

SCREEN: Locks appear on both rows as the changes arrive. Logs: "txf-1 -30.00", "txf-1 prepared"; "+30.00",
"prepared". Votes "yes" in the coordinator. Reader 100.00 / 0.00. Countdown. "txf-1 COMMIT" in green.

## Scene 5 · Phase two · 3:15–3:55 · [SHOW] [NAME] [LOOP-PAYOFF]

VO: Phase two is commit. The coordinator tells wallets to commit. It commits, and lets go of the lock. For a moment,
someone reading both servers sees the debit without the credit. The outcome is all or nothing. It just doesn't show
on both servers at the same instant. Then payouts commits too. If payouts were out of reach, the coordinator would
keep resending, for minutes or days, because once the line is written, the only way is forward. That's two-phase
commit. Everyone promises first, then one line decides.

SCREEN: wallets "committed", 70.00, lock gone; reader 70.00 / 0.00 (yellow). payouts commits, 30.00, reader
70.00 / 30.00. Three resend dots.

## Scene 6 · A no, and presumed abort · 3:55–4:35 · [BREAK] [NAME]

VO: Now a different run. This time payouts finds a payout entry for txf-1 already there, so one of its rules fails,
and it answers no. The coordinator writes nothing at all, and tells wallets to roll back, to undo its prepared
changes. Your wallet stays at 100.00. A payment with no line in the log counts as aborted. That's called presumed
abort, and it's safe, because nobody can commit without the line. A server that doesn't answer in time counts as a
no, too. So notice the two points of no return. A server's yes takes away its own right to abort. The coordinator's
line takes away everyone's.

## Scene 7 · The price · 4:35–5:10 · [GUARDRAIL] [JOKE:amplify] [LOOP-PLANT]

VO: Now the price. A normal commit is one round trip, a message there and its answer back, plus one wait for the
disk. Two-phase commit needs two round trips to every server, and three disk waits in a row. Between data centres at
the two ends of a continent, a round trip takes about 70 milliseconds. So each payment spends about 140 on the
network, instead of 70. And every prepared server holds its locks the whole time. It's like a friend who can't
accept any other plan until you text back. Hope you don't lose your phone. What happens when the coordinator dies
right after the yeses? That's next.

## Scene 8 · Moral and a check · 5:10–5:45 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So where did the 30.00 go? Into the gap between two separate commits. Two-phase commit closes it: every server
promises first, and one line on disk decides. One quick check. payouts said yes, then crashed and restarted before
phase two. The coordinator's log says txf-1 COMMIT. What must payouts do? Pause and think.

(three seconds)

Commit. Its yes was a promise that survives a crash, and the line has already decided.

---

### Beat check

- QUESTION (scene 1); FAMILIAR, PAIN, the obvious fix and its BREAK, WISH (scene 2) before the analogy.
- ANALOGY + MAP (scene 3); SHOW, PREDICT + PAUSE (scene 4); NAME commit point (scene 4), two-phase commit (scene 5),
  presumed abort (scene 6), each after it is shown.
- GUARDRAIL (scene 7): two round trips, three disk waits, held locks. MORAL + check (scene 8).
- Light moments: "we've just moved the problem" (1:20), "hope you don't lose your phone" (5:00).

### Accuracy notes for the producer

- The steps follow the lesson's stepper: changes sent and rows locked, prepare with a log line on disk and a yes, the
  COMMIT line as the commit point, COMMIT PREPARED to wallets first (a reader briefly sees the debit only), resending
  until payouts confirms; the alternative run where a duplicate payout entry makes payouts vote no and the
  coordinator writes nothing and sends ROLLBACK PREPARED.
- The video doesn't name PostgreSQL's commands (PREPARE TRANSACTION, COMMIT PREPARED, pg_prepared_xacts,
  max_prepared_transactions = 0 by default); the lesson does.
- The lock is drawn on each server's row; the lesson's stepper names the lock on w-17, and payouts locks the rows it
  changes too ("each server locks the rows it changes, as usual").
- The coordinator dying (in doubt, blocking) is the lesson's next section; the video only plants it.
- 70 ms per round trip between data centres at two ends of a continent, and 140 ms instead of 70, are the lesson's
  figures.
