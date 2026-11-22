# "Saved." On how many machines? When the leader says OK

- Slug / scene: `async-failover`, `videos/scenes/async_failover.py:AsyncFailover`
- Lesson: `repl-01`, section 1, "When the leader says OK: before or after a follower has the payment"
- Audience / level: a complete newcomer who has seen the lesson's first section (a leader, two followers, a numbered
  log). Doesn't know what acknowledging, a commit, or synchronous replication is.
- Length: 4:58 (~740 words of narration)
- Poster: `POSTER=117` (OK at once, leader dead: 247 to 250 lost in flight, score 0 ms / 250 / 4)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: the card reader says OK. Saved where? If the machine that said it dies a moment
  later, is my payment gone?
- Misconception to steelman and break: (1) "say OK at once, the copies catch up in a few milliseconds" (broken: 4
  acknowledged payments lost, and nothing limits the lag); (2) "then wait for every follower" (broken: 100 ms per
  payment, and a frozen follower stops all payments); (3) "a setting called semi-synchronous always waits" (broken:
  after a timeout it switches itself off, and a crash loses 149).
- Concept chain: the leader says OK at some moment → OK at once is fast and loses what's in flight → OK after every
  follower is safe and stalls → OK after one follower is the middle → on a bad day the middle may quietly become the
  fast one (hardest last)
- Analogy family: the lesson's club notebook. One clerk writes numbered lines and posts photocopies to two towns; she
  says "noted" either when the ink is dry or after a town phones back.
- Open loops: "saved where?" planted in scene 1 → answered in scene 7.
- Assumptions: every number is the lesson's simulator (`CommitDemo.kt` output): f1 20 ms and f2 50 ms one way, a
  payment every 4 ms, the leader dies at 1,001 ms; 250/241/226 OKs; 0/40/100 ms waits; 4 lost, f1 at 246; the stalled
  semi-sync run (500 ms, 149 lost, f1 at 101); the check (2 and 70 ms: 4 ms and 140 ms). Log cells 243 to 250 are the
  window the picture shows; f2's exact position isn't shown.

## The one picture

Three rows, one per machine: the leader (blue), f1 and f2 (teal), each a box on the left with its log to the right
as numbered cells 243 to 250 (filled = it has that entry). A card reader chip above the leader gets the OK. On the
right, a score panel: "each payment waits", "said OK", "lost". The rule in force is written over the logs. Red means
lost, green means safe on two machines.

## Scene 1 · Saved where? · 0:00–0:45 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: You tap your card, and the reader beeps: OK. Your payment is saved. Saved where, exactly? On how many machines?

Here's the setup from the start of this lesson. The payments live in a database, a program that stores records. One
machine, the leader, takes every new payment, and writes it at the next numbered position in its log. Two followers,
f1 and f2, copy that log in order. f1 is 20 milliseconds away, and f2 is 50.

A card reader sends a payment. The leader writes it, and sends it on. At some moment, it tells the card reader OK.
Which moment? That choice decides what a dying leader can take with it.

SCREEN: Title card. Card reader chip, "OK" and "saved where?". The three rows draw in; cells fill on the leader, then
dots carry each entry down to f1 (quick) and f2 (slower). A yellow "OK" flies back to the card reader with a "?".

## Scene 2 · The clerk says "noted" · 0:45–1:30 · [ANALOGY] [MAP]

VO: Think back to the lesson's club notebook. One clerk writes each payment on the next numbered line, and posts
photocopies to two other towns. A member hands over money, and waits for the clerk to say: noted.

She can say it the moment the ink is dry. Or she can wait until a town phones back: we have your line. Say it early,
and the member leaves sooner. But if the office burns down that night, a line she said "noted" for may exist nowhere
else.

Map it. The clerk is the leader, the notebook is the log, and the towns are followers. Saying "noted" is called
acknowledging the write. And the moment a change becomes final is its commit.

SCREEN: Role labels: "the clerk", "town 1", "town 2"; "noted" chip by the card reader. Then the labels become the
names; caption "acknowledge: say OK", "commit: the moment a change becomes final".

## Scene 3 · OK at once · 1:30–2:40 · [SHRINK] [PREDICT] [PAUSE] [SHOW] [NAME]

VO: Now the lesson's simulator, with exact numbers. A payment arrives every 4 milliseconds. First rule: the leader
says OK as soon as the payment is on its own disk. Nobody waits at all. In the first second, 250 card readers hear
OK.

At 1,001 milliseconds, the leader dies. How many payments that already heard OK are now gone? Pause and guess.

Four. f1 had everything up to 246. Entries 247 to 250 were still on the wire, and they died with the leader. f1
takes over as the new leader. Four card readers heard OK for payments that exist on no running machine.

This is asynchronous replication: the copies happen in the background. And four is a good day. A follower is
usually a few milliseconds behind, but nothing limits it. Stuck behind a slow link, it can be minutes behind, and
a crash then takes minutes of payments.

SCREEN: Rule "OK when: the leader's own disk has it". Score: waits 0 ms, said OK 250. A red cross on the leader at
"1,001 ms". Cells 247 to 250 on the leader turn red and fade; f1's cells up to 246 stay; dots stuck halfway turn into
red crosses. Score: lost 4. f1 gets a "new leader" label. Caption "asynchronous: copies in the background".

## Scene 4 · Wait for everyone · 2:40–3:20 · [BREAK] [JOKE:amplify]

VO: So the obvious fix: say OK only when every follower has the payment. Run it again. Nothing is lost. But each
payment now waits 100 milliseconds, the round trip to f2, the farthest. And it gets worse. Say f2 freezes for 40
seconds while its machine is moved. Every payment waits for it. Card payments stop, everywhere, for 40 seconds.

The whole system now moves at the speed of its sleepiest machine. That's fully synchronous replication.

SCREEN: Reset. Rule "OK when: both followers have it". Score: waits 100 ms, said OK 226, lost 0. Then f2 turns grey,
"frozen: 40 s"; the card reader shows "waiting..." and a queue of payments stacks up.

## Scene 5 · The middle · 3:20–4:00 · [NAME] [SHOW]

VO: Most systems choose the middle: wait for any one follower. Each payment waits 40 milliseconds, the round trip to
f1. And the crash loses nothing, because every acknowledged payment is on at least two machines. That's usually
called semi-synchronous replication.

Side by side: no waiting, 250 OKs, four lost. Wait for one, 40 milliseconds, 241, none lost. Wait for both, 100, 226,
none lost. The waiting rules sent fewer OKs only because their last payments were still waiting when the leader died.

SCREEN: Rule "OK when: one follower has it". Score: 40 ms, 241, 0. Then the table from the lesson, row by row.

## Scene 6 · The bad day · 4:00–4:50 · [GUARDRAIL] [BREAK]

VO: Now the small print. What if no follower answers? MySQL, a popular free database, waits up to 10 seconds by
default. Then it quietly goes back to asynchronous. No card reader sees an error.

The lab shows it with a 500 millisecond timeout and both followers stalled. The first payment waits the full 500.
Then semi-sync switches itself off, and every later payment gets its OK at once. When the leader dies, 149
acknowledged payments are lost, under a setting with "synchronous" in its name.

PostgreSQL, another free database, does the opposite: it keeps payments waiting until a follower is back. Neither is
wrong. One keeps payments flowing and drops its promise. The other keeps its promise and stops the payments.

SCREEN: Both followers grey, "stalled". Rule "semi-sync, timeout 500 ms". The first payment's wait bar grows to 500,
then the rule's text is struck through to "asynchronous (quietly)". Score: max wait 500 ms, said OK 250, lost 149,
new leader f1 at 101. Then two captions side by side: MySQL "keeps payments flowing", PostgreSQL "keeps its promise".

## Scene 7 · Moral and check · 4:50–5:30 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, saved where? On as many machines as the leader waited for before it said OK. And here's the rule to keep: a
setting's name describes a good day. Find out what it does on a bad one.

One quick check. Move f1 to 2 milliseconds away, and f2 to 70. Waiting for one follower, how long does each payment
wait? Pause and think.

4 milliseconds: the round trip to f1. Waiting for both now costs 140.

SCREEN: Caption "saved on as many machines as the leader waited for". The rule in yellow. The followers' distance
labels change to 2 ms and 70 ms; score "?"; countdown; "4 ms" (green), "both: 140 ms".

---

### Beat check

- QUESTION (scene 1) from the beep everyone knows; FAMILIAR: the lesson's leader, followers and log.
- ANALOGY and MAP (scene 2) before the first rule; NAME (acknowledge, commit) right after the mapping.
- PREDICT with PAUSE (scenes 3 and 7), SHOW right after each.
- BREAK three times: the fast rule loses 4, the safe rule stalls, the middle rule switches itself off.
- NAME after each SHOW: asynchronous (3), fully synchronous (4), semi-synchronous (5).
- GUARDRAIL (scene 6) and MORAL (scene 7) last. Light moments: the office burning down, the sleepiest machine, the
  setting with "synchronous" in its name.

### Accuracy notes for the producer

- The simulator's rows are the lesson's output; the waits are round trips (f1: 2 × 20 ms; f2: 2 × 50 ms).
- "Follower has it" has three possible points (received, flushed, applied); the video doesn't split them (the lesson's
  figure does).
- MySQL's timeout is `rpl_semi_sync_source_timeout`, 10 seconds by default; the lab uses 500 ms. PostgreSQL waits
  under `synchronous_commit` until a follower returns.
- The frozen-follower stop (40 seconds) is the lesson's warm-up.
- Failover itself (noticing, choosing, redirecting) is section 3; here f1 is simply promoted, as in the simulator.
