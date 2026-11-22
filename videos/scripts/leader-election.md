# The counter that says no: a leader that froze, and the number that stops it

- Slug / scene: `leader-election`, `videos/scenes/leader_election.py:LeaderElection`
- Lesson: `cons-05`, section 3, "Electing a leader, and fencing the one that froze"
- Audience / level: a complete newcomer. Has queued at a post office; doesn't know what etcd, a lease, a key's
  revision or a fencing token is.
- Length: 4:46 (~770 words of narration, two pauses)
- Poster: `POSTER=205` (the fenced write: ledger "highest token: 9", "token 7: refused, 7 < 9")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: one copy of the payout job froze, another took over, and the frozen one woke up and
  paid again. How do we stop the second payout?
- Misconception to steelman and break: "the election is a lock, so checking that you're the leader before you write
  is enough". Broken by the stepper's 15-second freeze, then by "just check again right before writing" (the freeze
  can land between the check and the write).
- Concept chain: lowest ticket leads, on a lease → a frozen program looks dead, so the turn passes → the frozen one
  still acts → the resource remembers the highest token and refuses lower ones → the check and the write in one step
  (hardest last)
- Analogy family: the lesson's post office ticket machine (etcd hands out numbers that only go up; wandering off ends
  your turn; the clerk who has called 48 won't serve ticket 47).
- Open loops: "how do we stop that second payout?" planted in scene 1 → paid off in scene 5; the clerk at the counter
  planted in scene 2 → scene 5.
- Assumptions: the run is the lesson's stepper (revisions 7, 9 and 11 on 10-second leases; batch 17 by A with token
  7; a 15-second freeze; A's key deleted at revision 12; B leads with 9 and pays batch 18; A's late write with 7
  refused; A rejoins at 13). Jepsen 2020 and the 56-of-60-second wait are the section's and its Try-it's.

## The one picture

Left: etcd (teal) as a panel of keys, one row per ticket ("rev 7  job A") with a lease bar that drains, and grey
watch arrows (B watches A, C watches B). Centre: three job boxes, each with a state line (waiting, leader, frozen,
watches A). Right: the payout ledger (gold) with "highest token" and one row per write. Dots run from jobs to etcd
(check-ins) and to the ledger (writes); chips carry token numbers. Captions top and bottom.

## Scene 1 · The question · [QUESTION] [LOOP-PLANT]

VO: Each night, one program pays every shop what it took that day. Three copies of it run on three machines, so one can die: job A, job B and job C. Only one may pay the shops each night. One night, job A freezes for 15 seconds. Job B takes over and pays the shops. Then job A wakes up, and pays them again. How do we stop that second payout? Hold that question.

SCREEN: "each night, one payout"; three job boxes; A turns blue "frozen", B green "pays", A red "pays again"; the question in yellow.

## Scene 2 · The ticket machine · [FAMILIAR] [ANALOGY] [MAP] [SHRINK]

VO: Picture the ticket machine at a busy post office. You pull ticket 47. When it lights up, it's your turn, and nobody else's. Wander off, and the screen moves on to 48. Our ticket machine is etcd, a small service that a few servers run together, agreeing on every change. Each copy creates a key under one shared name, settlement, and etcd stamps it with a number from a counter that only goes up. Job A got 7, job B 9, job C 11. The lowest ticket leads, so job A leads. Each key is tied to a lease, ten seconds here. A copy keeps its lease alive by checking in. Stop checking in, the lease runs out, and the key is deleted. That's wandering off. Job B watches job A's key, and job C watches B's. When a leader goes, only the next in line wakes up.

SCREEN: The ticket machine caption; etcd's panel; chips run from each job to its key row (rev 7, 9, 11); A's row turns green, "leader"; lease bars; teal check-in dots; watch arrows B to A and C to B.

## Scene 3 · Trust the turn, and break it · [PAIN] [BREAK] [SHOW] [JOKE:release]

VO: Inside one program, a lock means one holder at a time, and etcd's election sounds like the same promise. So job A checks: am I the leader? Yes. And it pays batch 17 into the payout ledger, the table where each payout is recorded. Now job A's program stops for 15 seconds. Java pauses everything to clean up memory, or a disk stalls. Its check-ins stop with it. To etcd, a frozen program and a dead one look exactly the same. The lease runs out, and etcd deletes job A's key, as change number 12. Job B's watch fires. Its key is now the lowest, so job B leads, and pays batch 18. Then job A wakes, and finishes the payout it was writing when it froze. It checked it was leader before the freeze, and nothing has told it otherwise. Well, the shops in batch 17 may just have been paid twice. And this isn't rare. In 2020, Jepsen, a project that tests databases by breaking them, saw two holders of an etcd lock overlap within minutes, even in a healthy cluster.

SCREEN: Purple "the obvious plan"; the ledger appears, "batch 17 by job A"; A freezes, its lease bar drains and its key vanishes (revision 12); B's row pulses and turns green; "batch 18 by job B"; A, awake, writes a red "job A pays again"; Jepsen caption.

## Scene 4 · The wish, and why checking again isn't enough · [BREAK] [WISH]

VO: Couldn't job A just check again, right before it writes? It should, but the freeze can land between the check and the write, and from inside, a freeze is invisible. What we want is someone who sees the write at the moment it arrives, and can say no.

SCREEN: Purple "check again right before writing?"; "check ... freeze ... write"; the ledger pulses: "wanted: someone who sees the write arrive, and can say no".

## Scene 5 · The counter, predict · [ANALOGY] [SHOW] [PREDICT] [PAUSE] [LOOP-PAYOFF]

VO: Back to the post office. The clerk who has called 48 won't serve ticket 47. So let every write carry the writer's ticket number, and let the ledger remember the highest it has accepted. Replay it. Job A pays batch 17 with token 7. Nothing higher has been seen, so it's accepted. Job B pays batch 18 with token 9. 9 is higher than 7, so it's accepted, and the ledger remembers 9. Now job A wakes and writes with token 7. What does the ledger do? Pause and guess.

(three seconds)

It refuses. 7 is lower than 9. One copy paid, one copy was turned away at the counter.

SCREEN: "the clerk who has called 48 won't serve 47"; token chips 7 and 9 run to the ledger, accepted, "highest token: 9"; countdown; A's red 7 arrives: "token 7: refused, 7 < 9".

## Scene 6 · The name · [NAME]

VO: That's called fencing, and the number is a fencing token. Here it comes free. The key's revision was handed out by etcd's agreement, so no two leaders share one, and every new leader's is higher. Job A's next check-in fails. Now it knows it lost, so it rejoins at the back, with a new key at revision 13. A token never comes back down.

SCREEN: Teal "fencing: every write carries a token; the resource refuses old ones"; the key rows pulse; A's new row "rev 13", "watches C".

## Scene 7 · The guardrail · [GUARDRAIL]

VO: One rule keeps it honest. The check must happen at the ledger, in the same all or nothing step as the write. Check in one step and write in the next, and you've reopened the gap. In a SQL database, that's one conditional statement. And the lease length is a trade. After a crash in the lesson's run, the next job waited 56 seconds, the rest of a 60-second lease. Shorter leases take over faster, with more false alarms.

SCREEN: "the check and the write: one all-or-nothing step"; "in SQL: one conditional statement"; "a crash: 56 seconds of waiting"; "shorter lease: faster takeover, more false alarms".

## Scene 8 · The moral, and a check · [MORAL] [PREDICT] [PAUSE] [RECAP]

VO: So the moral of the story: a lease says who should act. Only the resource can refuse the one who shouldn't. One quick check. Job B freezes next, and job C takes over with token 11. Then job B wakes and writes with token 9. Accepted or refused? Pause and think.

(three seconds)

Refused. Once the ledger has seen 11, every 9 is old news.

SCREEN: The moral in yellow; B frozen, C leader with 11; countdown; "highest token: 11", B's red 9: "9 < 11: refused"; last caption "the counter says no".


---

### Beat check

QUESTION (1) → FAMILIAR/ANALOGY/MAP (2) → the obvious plan and its BREAK (3) → a second wrong fix broken, WISH (4) →
the counter, PREDICT + PAUSE, SHOW (5) → NAME (6) → GUARDRAIL (7) → MORAL and a check with PAUSE (8). Light moments:
"the shops in batch 17 may just have been paid twice" (understatement, 3), "every 9 is old news" (8).

### Accuracy notes for the producer

- Revisions, lease length, batch numbers and tokens are the stepper's. The stepper calls the delete "one change,
  revision 12"; the video says "as change number 12".
- "Java pauses everything to clean up memory, or a disk stalls" paraphrases the stepper's causes (a long garbage
  collection, a stalled disk).
- Jepsen 2020 (etcd 3.4.3): lock holders overlapped within minutes with 1 to 3 second leases, in a healthy cluster.
  The 18% lost-update figure is left to the lesson.
- The 56-second wait is the Try-it's (`etcdctl elect` with the Go client's 60-second default lease, after `docker
  kill`).
- "In SQL, one conditional statement" points at the lesson's worked example; the video shows no code.
- ZooKeeper's sequence numbers, Curator's LeaderLatch, service discovery and work assignment are left to the lesson.
