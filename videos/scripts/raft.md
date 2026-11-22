# One chair per term: how five servers choose a leader

- Slug / scene: `raft`, `videos/scenes/raft.py:Raft`
- Lesson: `cons-04`, section 1, "Choosing a leader: terms, votes and random timers"
- Audience / level: a complete newcomer. Has tapped a card and seen Approved; doesn't know what a leader, a term, a
  vote between servers or an election timeout is.
- Length: 4:58 (~750 words of narration, two pauses, silent builds)
- Poster: `POSTER=102.5` (n4 green "leader, term 1", every follower on term 1, "votes for n4: 3, 3 of 5: a majority")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: when the leader's cable comes loose, how do the others even notice, and how do they
  make sure exactly one of them takes over?
- Misconception to steelman and break: "same rules for everyone, same timer for everyone, is fair and fine", broken by
  the lab's `split` run: every timeout 150 ms, every message 5 ms, 330 elections and term 66 after 10 s, no leader.
- Concept chain: a follower's timer notices silence → a candidate needs a majority, one vote per server per term →
  terms make an old leader step down → equal timers tie forever, random ones don't → the timeout's limits (hardest
  last)
- Analogy family: the lesson's club with a minutes book (chair = leader, period of office = term, minutes book = log,
  members = followers). It breaks where members can see who's in the room and servers can't.
- Open loops: "how do they notice, and make sure only one takes over?" planted in scene 1 → scene 3 (timers, a
  majority) and scene 9 (the check: two winners would need six votes).
- Assumptions: the first election is the lab's `election` run exactly (n4 at 186 ms; n1 at 187; n2 and n3 at 190;
  wins at 192; n5's vote at 194). The cut-off leader (n2 winning term 2) is an illustration of the section's rules,
  with no timings. Timer bar lengths are drawn, not measured. The split numbers are the lab's `split` run; the
  randomness numbers are the Raft paper's, as the lesson quotes them.

## The one picture

Five server boxes on a ring (n1 top, then clockwise n2, n3, n4, n5), each with "term k" top right, its role under its
name (white follower, yellow candidate, green leader) and a teal timer bar underneath that drains and refills.
Messages are dots: yellow vote requests, green votes and heartbeats, red refusals. Left panel: the club's mapping,
later the names. Right panel: the clock and vote count, later the numbers. A caption row top and bottom.

## Scene 1 · The question · [QUESTION] [LOOP-PLANT]

VO: Picture a café at lunchtime. You tap your card, and the screen says Approved. Behind that word, five computers saved your payment. One of them, the leader, takes each payment and copies it to the others. Now the leader's network cable comes loose. How do the other four even notice? And how do they make sure exactly one of them takes over, not two? Hold that question.

SCREEN: Five boxes; n4 green, dots to the other four; a red cross on n4; the two questions.

## Scene 2 · The club · [FAMILIAR] [ANALOGY] [MAP]

VO: Think of a club with a minutes book. Each period of office has one chair, chosen by vote. If the chair stops turning up, a member calls an election. Our five computers work the same way: the chair is the leader, the period of office is a term, numbered 1, 2, 3, and the minutes book is the log of payments. Everyone else is a follower.

SCREEN: Left panel builds "chair = leader", "period = term 1, 2, 3", "minutes book = log", "members = followers".

## Scene 3 · The first election · [SHRINK] [SHOW] [JOKE:release]

VO: Watch it from the start, in the lab's run. Nobody is leader yet. Every server is a follower with a timer. If the timer runs out before it hears from a leader, it calls an election. n4's timer runs out first, at 186 milliseconds. It moves to term 1, becomes a candidate, votes for itself, and asks the others for their votes. Each server gives at most one vote per term, to the first candidate that asks, and writes it to disk before answering. n1 votes at 187, n2 and n3 at 190. Three of five is a majority, so at 192, n4 wins term 1. It sends a heartbeat at once, a small I'm still here message, and keeps sending one every 50 milliseconds. Each one restarts every timer. n5's vote arrives at 194 and changes nothing. The chair is already seated.

SCREEN: Timer bars drain; n4's empties; "t = 186 ms"; n4 yellow candidate, term 1; yellow dots out, green votes back;
"votes for n4: 3", "3 of 5: a majority"; n4 green leader at 192; heartbeats refill every bar; n5's grey vote at 194.

## Scene 4 · A cut-off leader · [SHOW]

VO: Now n4's cable comes loose. The heartbeats stop, and the timers run down. Say n2's runs out first. It moves to term 2, and n1, n3 and n5 vote for it. n2 leads term 2. Then the cable goes back in. n4 still thinks it leads term 1, and sends a heartbeat. But every message carries the sender's term, and the reply says term 2. A server that sees a higher term takes that number and becomes a follower, and a message with a lower term is refused. So n4 steps down at the first reply, and nobody acts on its old messages.

SCREEN: Red cross on n4; bars drain; n2 candidate, term 2, votes from n1, n3, n5; n2 green. n4's heartbeat to n3,
the reply "term 2"; n4 becomes follower, term 2.

## Scene 5 · The name · [NAME]

VO: This method is Raft. The roles are follower, candidate and leader, the vote request is called RequestVote, and the timer is the election timeout. Two leaders in one term would need two majorities with no server in common, and five servers can't form those.

SCREEN: Teal "Raft: follower, candidate, leader"; left panel "RequestVote", "election timeout".

## Scene 6 · Break it: no randomness · [PREDICT] [PAUSE] [BREAK] [JOKE:amplify]

VO: So does the timer matter much? Restart all five, but make every timeout exactly 150 milliseconds, and every message take exactly 5. Who wins? Pause and guess.

(three seconds)

Nobody. All five time out in the same millisecond. Each votes for itself and refuses the other four, because it already voted in that term. Twenty refusals. 150 milliseconds later, the same thing again, one term higher. After 10 seconds: 330 elections, term 66, and still no leader. A club where everyone nominates themselves at the same second, forever. The rules are fine. The tie is the problem.

SCREEN: All five reset to follower, term 0; bars drain together; five yellow candidates, twenty red dots; "20
refusals, no winner"; again in term 2; "after 10,000 ms: 330 elections, highest term 66, leader: none".

## Scene 7 · Random timers · [SHOW]

VO: The fix is almost silly: draw each timeout at random, from 150 to 300 milliseconds in Raft's paper. One server usually wakes well before the others, and collects its votes first. The paper measured it on five servers. With no randomness, split votes left them leaderless for more than 10 seconds. With just 5 milliseconds of randomness, the median wait fell to 287 milliseconds. With 50, the worst of 1,000 trials took 513.

SCREEN: Bars at different lengths; n4's empties first; it wins. Right panel: the paper's three numbers.

## Scene 8 · The guardrail · [GUARDRAIL]

VO: So why not make the timeout tiny? One round of messages, disk writes included, takes 0.5 to 20 milliseconds. The timeout must be many of those, or followers unseat a healthy leader that was merely slow. So it sits between 10 and 500 milliseconds. etcd, a small database built on Raft, waits 1,000 milliseconds before calling an election. And here the club picture breaks. Members in a room can see who's there. A server can't tell a dead leader from a slow network, so every rule runs on timers and term numbers.

SCREEN: "0.5 to 20 ms", "10 to 500 ms"; "etcd: 100 ms heartbeat, 1,000 ms election timeout"; "dead or just slow?".

## Scene 9 · Moral and check · [MORAL] [PREDICT] [PAUSE] [LOOP-PAYOFF]

VO: So the moral: one leader per numbered term, won by a majority, one vote per server per term. Random timers break ties, and the higher term always wins. One quick check. Could two servers both win term 1? Pause and think.

(three seconds)

No. Each winner needs three votes, so two winners need six. Five servers have only five votes in term 1.

SCREEN: Moral in yellow; countdown; "3 + 3 = 6 votes", "5 votes per term"; every box pulses; "one chair per term".

---

### Beat check

QUESTION (1) → FAMILIAR/ANALOGY/MAP (2) → SHOW (3, 4) → NAME (5) → PREDICT + PAUSE + BREAK (6) → the fix (7) →
GUARDRAIL and where the analogy breaks (8) → MORAL, check with PAUSE (9). Light moments: "the chair is already
seated" (3), "everyone nominates themselves at the same second, forever" (6), cashed back as "the tie is the problem".

### Accuracy notes for the producer

- Scene 3's timings are the lab's `election` output; the heartbeat interval (50 ms) is the lab simulator's.
- Scene 4 has no numbers; n2 winning term 2 is an example of the rules in the section, not a lab run.
- Scene 6's numbers are the lab's `split` output (20 refusals each round, every 150 ms; 330 elections, highest term
  66 after 10,000 ms). The picture shows the first two rounds as terms 1 and 2.
- Scene 7: "150 to 300 ms" and the three measurements are the Raft paper's, as the lesson quotes them.
- Scene 8: 0.5 to 20 ms per round, 10 to 500 ms for the timeout, and etcd's 100 ms heartbeat and 1,000 ms election
  timeout are the lesson's. The vote condition about logs ("a later section adds one condition") is left out.
