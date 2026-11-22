# Two honest against one liar isn't enough: why one liar takes four

- Slug / scene: `byzantine`, `videos/scenes/byzantine.py:Byzantine`
- Lesson: `dist-07`, section 3, "Byzantine faults: why one liar takes four nodes"
- Audience / level: a complete newcomer. Knows what a vote and a majority are; nothing about consensus or PBFT.
- Length: about 5:10 (~830 words of narration, two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=89` (poster regenerated at 89 s): the two worlds side by side, both "follower 1 heard: APPROVE DECLINE" panels lit
- The learner's real question: if one of three computers lies, don't the two honest ones simply out-vote it?
- Misconception to steelman and break: "two honest against one liar, the majority wins". Broken by the lesson's two
  worlds: follower 1 hears the same tie in both, and each tie rule fails one of them (the lab: every rule fails with
  three nodes).
- Concept chain: a node that lies → three nodes, leader and two followers, majority of two verdicts → two worlds,
  one view → a fourth node gives three verdicts, one liar spoils one → 3f + 1, derived → who pays for it, who doesn't
- Analogy family: the office. The boss says approve; a colleague says the boss told them decline. Who is lying?
  Leader = boss, followers = you and your colleague, the relay = the chat by the coffee machine.
- Open loops: "the majority wins? hold that guess" planted in scene 1 → broken in scene 6, answered in scene 10.
- Assumptions: approve/decline verdicts, the two worlds, the tie-rule results and the 40 rounds are the lesson's
  figure and lab. In the four-node lying-leader beat, the split (APPROVE, DECLINE, APPROVE) is one example of a lie.

## The one picture

Node boxes with arrows; verdict chips (green APPROVE, red DECLINE) ride on the arrows. A liar's box turns red with a
"liar" tag. Under follower 1, a "follower 1 heard:" row of chips. Three nodes in world A (left) and world B (right),
then four nodes centred. Captions at the bottom.

## Scene 1 · A computer that lies · 0:00–0:25 · [QUESTION] [LOOP-PLANT]

VO: So far, a broken computer has simply stopped, or come back with gaps in its memory. Now picture a worse one. It
keeps talking, and it lies. Three computers decide one card payment, approve or decline, and one of them lies. Two
honest against one liar. Surely the majority wins? Hold that guess.

## Scene 2 · The office · 0:25–0:50 · [FAMILIAR] [ANALOGY]

VO: You've felt this at work. Your boss tells you: approve it. Then a colleague says: funny, the boss told me to
decline. Somebody is lying. Is it the boss, or your colleague? From where you sit, you can't tell.

## Scene 3 · Leader and followers · 0:50–1:25 · [SHRINK] [MAP]

VO: Computers do exactly this. One node, the leader, holds a verdict and sends it to the other two, the followers.
Each follower tells the other what the leader said. Then each one decides by majority over the two verdicts it
heard. So the leader is the boss, the followers are you and your colleague, and passing on what the leader said is
the chat by the coffee machine.

## Scenes 4–5 · Two worlds · 1:25–2:20 · [SHOW]

VO: In world A, the leader is honest, and says approve. Follower 2 lies. It tells follower 1 that the leader said
decline. So follower 1 hears approve from the leader, and decline from follower 2. In world B, the leader lies. It
tells follower 1 approve, and follower 2 decline. Follower 2 is honest, and passes its decline on. So follower 1
hears approve from the leader, and decline from follower 2. Exactly the same as in world A.

## Scene 6 · Predict, then break · 2:20–3:15 · [PREDICT] [PAUSE] [BREAK] [JOKE:release]

VO: So what should follower 1 decide? Pause and guess. (three seconds) In world A, it must approve, because an honest
leader's verdict has to win. In world B, it must decide the same as follower 2... One verdict each way is a tie, and
nothing in the tie tells the two worlds apart. Trust the leader on a tie, and world B splits. Pick a fixed answer
instead, say decline, and in world A a lying follower overrules an honest leader. The lesson's lab tries every rule
and every lie. With three nodes, every rule breaks. Well... two honest against one liar wasn't enough.

## Scene 7 · A fourth node · 3:15–4:05 · [SHOW]

VO: Add a fourth node. Each follower hears three verdicts... Let follower 2 lie... The liar spoils one verdict out of
three. Follower 1 still hears approve twice, and the honest majority wins. If the leader lies instead, the followers
pass on honestly what they got, so every honest follower hears the same three verdicts and reaches the same
decision. The lab runs every way one node can lie with four nodes, 40 rounds, and not one of them breaks.

## Scene 8 · The name and the count · 4:05–4:50 · [NAME]

VO: A Byzantine fault... a 1982 paper by Lamport, Shostak and Pease, told as a story about generals and traitors.
Surviving f liars takes at least 3f + 1 nodes: wait for at most N minus f replies, up to f may be lies, so N minus 2f
honest must outnumber f, so N > 3f. For one liar, four. Crashes only: 2f + 1.

## Scene 9 · Who pays, who doesn't · 4:50–5:35 · [GUARDRAIL] [JOKE:is-the-explanation]

VO: PBFT runs 3f + 1 copies, three rounds of messages per request; its authors' file server ran only 3% slower.
Blockchains use the same family. A payments database almost certainly doesn't: four copies instead of three, more
rounds, and it wouldn't help. Four copies of one bug just agree with each other, very confidently. An attacker's trick
for one copy usually works on all. Checking who is asking, limiting what each program may touch, encryption and
firewalls do that job.

## Scene 10 · Moral and check · 5:35–6:00 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: Two honest against one liar? Not enough... One liar takes four nodes. Check: how many nodes to survive two liars?
(three seconds) Seven. Three times two, plus one.

---

### Beat check

QUESTION (1) → FAMILIAR + ANALOGY (2) → SHRINK + MAP (3) → SHOW (4–5) → PREDICT + PAUSE + BREAK (6) → SHOW (7) →
NAME (8, after the show) → GUARDRAIL (9) → MORAL + check (10). Light moments: "well... wasn't enough" (6), the
confident unanimous bug (9).

### Accuracy notes for the producer

- Tie-rule results: the lab output (3 nodes: approve and decline fail validity, leader fails agreement; 4 nodes:
  40 rounds, none). The video narrates "trust the leader" and "always decline" as the two examples.
- The 5-node subtlety (trust-the-leader fails again) is left to the lab.
- PBFT's 3% and the blockchain mention are the lesson's; CometBFT and Cosmos are left out.
- The fourth section's checksums (small lies) are left to the next video.
