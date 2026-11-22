# Two majorities always share someone: one decision that survives a crash

- Slug / scene: `paxos`, `videos/scenes/paxos.py:Paxos`
- Lesson: `cons-03`, section 3, "Paxos in plain words, and the family it started"
- Audience / level: a complete newcomer. Knows a payment can be captured or voided once told; doesn't know what a
  proposer, an acceptor, a ballot or a majority vote between computers is.
- Length: 5:46 (~800 words of narration at Kokoro's ~175 words a minute, plus two pauses and silent builds)
- Poster: `POSTER=216` (both majorities drawn around A2, every notebook green, "once chosen, it stays chosen")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: if the program that started a decision crashes halfway, how does the next one finish
  it without changing the answer?
- Misconception to steelman and break: "nobody told P2 anything, so it should start fresh and push its own value",
  broken by the walk itself (capture was already chosen) and by the lesson's Try-it: 114 of 500 runs split when
  proposers push their own value, 36 when acceptors forget their disk.
- Concept chain: a value is chosen when a majority wrote it under one number → round 1 makes the next proposer ask a
  majority what they wrote → the highest-numbered rule carries a chosen value forward → two majorities always share
  an acceptor, so once chosen it stays chosen (hardest last)
- Analogy family: three clerks with notebooks (acceptors and their disks) and two managers giving instructions
  (proposers); the request number on each instruction (the ballot); a shift handover, where the colleague who takes
  over finishes the job already signed (the value rule). Breaks where a clerk loses the notebook (the disk rule).
- Open loops: "how does the next one finish without changing the answer?" planted in scene 1 → paid off in scenes
  5 and 6; "chosen, and nobody knows yet" in scene 3 → scene 5 ("the same value that was chosen when P1 crashed").
- Assumptions: the run is the lesson's stepper exactly (pay-77; P1 capture, P2 void; ballots 1.1 and 2.2; A3's
  accept lost; P1 crashes; A1 slow in round 2; A2 reports 1.1 capture). Break numbers are the Try-it's output
  (500 seeded runs; 0, 114, 36). The clerks, managers and shift handover are the video's own analogy.

## The one picture

Centre: three acceptor boxes stacked (A1, A2, A3), each with two lines, "promised" and "accepted". Left: P1 (blue,
wants capture); right: P2 (gold, wants void); a status line under each. Arrows from a proposer to the acceptors carry
travelling dots. A caption row at the top and one at the bottom. Green marks capture written down; yellow a fresh
promise; red a crash or a cost; purple the wrong idea. Scenes 8 and 9 swap the picture for a three-row scoreboard and
three cost chips, then the picture comes back for the moral and the check.

## Scene 1 · The question · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: A payment, pay-77, needs one decision. One program wants it captured: the money moves to the shop. Another wants it voided: cancelled. Never both. Three computers keep the decision, messages get lost, and any program can stop at any moment. So if the program that started the decision crashes halfway, how does the next one finish it without changing the answer? Hold that question.

SCREEN: Title card. "pay-77: capture or void?"; P1 and P2 slide in; "one or the other, never both"; a "?"; P1 pulses
red; the question in yellow.

## Scene 2 · Clerks and notebooks · 0:30–1:15 · [FAMILIAR] [ANALOGY] [MAP] [SHRINK]

VO: Picture three clerks with notebooks, and two managers giving them instructions. The managers, called proposers, are the programs: P1 wants capture, P2 wants void. The clerks are the three computers, called acceptors. Each notebook has two lines: the request number the clerk has promised to listen to, and the last instruction it wrote down. The notebook is the computer's disk, so it survives a restart. Each request carries a number, round dot proposer, so 2.2 is round 2 from P2, and beats 1.1. A value is chosen once two clerks out of three, a majority, have written it under the same number.

SCREEN: Three acceptor boxes; "managers = proposers", "clerks = acceptors"; the promised and accepted lines pulse;
"notebook = the computer's disk"; "2.2 beats 1.1"; "chosen: a majority (2 of 3) wrote the same value under the same
number".

## Scene 3 · P1's two rounds · 1:15–2:05 · [SHOW] [JOKE:release]

VO: Let's play it slowly. P1 picks number 1.1 and sends a prepare to every clerk. It means: promise to ignore anything lower than 1.1, and tell me what you've already written. A1 and A2 write promised 1.1, and answer with a promise. Neither has written any value. Two out of three is a majority, so P1 doesn't wait for A3. No one reported a value, so P1 may use its own. It sends accept 1.1, capture. A1 and A2 write it down. The copy to A3 is lost. Two notebooks out of three now say 1.1 capture, so capture is chosen. And then P1 crashes, before a single reply reaches it. So P1 had the best moment of its career and never found out. Nobody knows yet, and that's the point: chosen is a fact about the notebooks, not about who heard.

SCREEN: Blue arrows and dots; "promised 1.1" in A1 and A2; replies; A3 dimmed; "accept 1.1 capture"; A3's copy dies
halfway with a red cross; "1.1 capture" in green in A1 and A2; "capture is chosen"; P1 dims with a red cross,
"crashed".

NOTE: The joke comes after the walk, and is cashed back at once ("chosen is a fact about the notebooks").

## Scene 4 · The obvious move, and P2's first round · 2:05–2:45 · [PAIN] [WISH] [BREAK]

VO: Now P2 hears nothing, and its timer runs out. The obvious move is to start fresh and push void. But capture is already chosen, so some services would move the money while others cancel it. What we want is for the next manager to find out what may already be decided, before saying anything. That's the first round's job. P2 picks a higher number, 2.2, and sends prepare. A1 is slow, so only A2 and A3 answer. A3 promises 2.2, with nothing written. A2 raises its promise to 2.2, and reports what it wrote: 1.1, capture.

SCREEN: Purple "the obvious move: start fresh and push void"; red "two answers". Yellow wish. Gold arrows; A1 dimmed,
"slow"; A3 and A2 show "promised 2.2"; A2's reply runs back green; "A2 reports 1.1 capture".

## Scene 5 · Predict, then the rule · 2:45–3:20 · [PREDICT] [PAUSE] [SHOW] [LOOP-PAYOFF]

VO: So P2 wants void, and one of its two promises carries capture. What must it propose? Pause and guess.

(three seconds)

Capture. The rule is: propose the value with the highest number among the promises, or your own if there's none. It's a shift handover. The colleague who takes over finishes the job that's already signed, and keeps their own opinion for later. P2 sends accept 2.2, capture. A2 and A3 write it down, and P2 learns the decision: capture, the same value that was chosen when P1 crashed.

SCREEN: Countdown under P2. "proposes capture"; the rule in yellow; "wants void" pulses red; "a shift handover";
"2.2 capture" in A2 and A3; "learned: capture".

## Scene 6 · Why it had to be capture · 3:20–3:45 · [SHOW] [LOOP-PAYOFF]

VO: Was that luck? No. P1's majority was A1 and A2. P2's majority was A2 and A3. Any two majorities of three share at least one clerk, here A2. A value that's chosen sits in a majority of notebooks, so the next manager's majority always includes someone who wrote it down. Once chosen, it stays chosen.

SCREEN: A blue outline around A1 and A2, "majority for 1.1"; a gold one around A2 and A3, "majority for 2.2"; A2
pulses; "once chosen, it stays chosen".

## Scene 7 · The name · 3:45–4:10 · [NAME] [JOKE:release]

VO: What we just played is Paxos, Leslie Lamport's method for deciding one value. The request number is called a ballot, and the two rounds are prepare and promise, then accept. Lamport first told it as a story about a Greek island's parliament. Readers struggled, so his next paper was called Paxos Made Simple. A title like that is mostly an apology. The whole method is the two rounds you just watched.

SCREEN: Teal "Paxos: deciding one value (Leslie Lamport)"; "request number = ballot ..."; the two paper titles.

## Scene 8 · Break it on purpose · 4:10–4:45 · [BREAK]

VO: Now let's break it on purpose. The lesson's demo plays 500 runs with five acceptors, lost and repeated messages, and crashes everywhere. Paxos as written: zero runs out of 500 chose two values. Now let proposers ignore the promises and push their own value: 114 runs split. Now let acceptors forget their notebook when they restart, as if they answered before writing to disk: 36 runs split. Well, that's a lot of payments both captured and cancelled. So every rule matters: read what's written, carry the highest forward, and write to disk before you answer.

SCREEN: The picture fades; "500 hostile runs: how many chose two different values?"; rows 0 (green), 114 (red), 36
(red); the three rules in yellow.

## Scene 9 · What it costs · 4:45–5:15 · [GUARDRAIL]

VO: So what does it cost? One decision takes two round trips. A majority must be up: three acceptors survive one failure, five survive two. And plain Paxos decides one value, but a real system needs a log of them. So real systems run Multi-Paxos: a steady leader runs the first round once, then each command costs one round trip. Google's lock service, Chubby, works this way.

SCREEN: Chips "one decision: 2 round trips", "a majority must be up: 3 survive 1 failure, 5 survive 2", "Multi-Paxos:
a steady leader, then 1 round trip per command".

## Scene 10 · The moral, and a check · 5:15–5:50 · [MORAL] [PREDICT] [PAUSE] [RECAP]

VO: So the moral: before you propose, ask a majority what they've written, and carry the highest forward. Two majorities always share a notebook, so a crash can delay a chosen value, never change it. One quick check. Suppose P2's promises had come from A1 and A3 instead. Would it still have proposed capture? Pause and think.

(three seconds)

Yes. A1 wrote 1.1 capture, and A1 is in that majority too. Any two clerks out of three include A1 or A2, so every majority hears about capture.

SCREEN: The picture returns. The moral in yellow; A1 and A3 pulse; countdown; A1's "1.1 capture" pulses; last caption
"two majorities always share someone".

---

### Beat check

- Opens with QUESTION (scene 1). FAMILIAR + ANALOGY + MAP (scene 2) before any formal term other than the plain
  "proposers" and "acceptors" labels.
- SHOW (scene 3), PAIN + WISH + the wrong move (scene 4), PREDICT with PAUSE (scene 5), why (scene 6).
- NAME after the walk (scene 7: Paxos, ballot, prepare, promise, accept).
- BREAK (scene 8, the Try-it numbers), GUARDRAIL (scene 9), MORAL and a check with PAUSE (scene 10).
- Light moments: P1's best moment (scene 3), the sequel's title as an apology (scene 7), "a lot of payments both
  captured and cancelled" (scene 8, understatement).

### Accuracy notes for the producer

- The run is the stepper's seven frames. "Chosen" is the lesson's definition: a majority accepted the same ballot.
- "Paxos as written / push their own value / forget their notebook" are the Try-it's three setups and its printed
  counts (0, 114 and 36 of 500); the setup line paraphrases its header (20% lost, 10% duplicated, 5 acceptors,
  3 proposers, up to 2 down at a time, all but one proposer crash early).
- "Some services would move the money while others cancel it" is what two chosen values would mean; the lesson's
  safety property is that every service learns the same outcome.
- "Readers found it so hard": the lesson's deeper section says reviewers found the parliament story hard to read, and
  "Paxos Made Simple" (2001) restated it. The apology line is the video's joke.
- 2f + 1 (3 survive 1, 5 survive 2) and the round trips are from the lesson's recap and section; Multi-Paxos runs
  phase 1 once and fills gaps with no-ops, which the video leaves to the lesson. Spanner and Viewstamped Replication
  and Zab are left to the lesson too.
