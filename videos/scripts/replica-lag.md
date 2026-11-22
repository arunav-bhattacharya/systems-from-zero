# Where did my refund go? Carry the position of your last write

- Slug / scene: `replica-lag`, `videos/scenes/replica_lag.py:ReplicaLag`
- Lesson: `repl-03`, section 1, "Seeing your own changes: carry the position of your last write"
- Audience / level: a complete newcomer. Has met the leader, its numbered log and followers in the earlier lessons,
  but the video sets them up again in one breath.
- Length: about 4:30 (~760 words of narration, two pauses and a check)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: the moment after the router sends the read to the leader (token 2, r1 at 0, refund listed)
- The learner's real question: the app said "refund sent", the reload shows no refund. Did it vanish? Why couldn't
  she see it?
- Misconception to steelman and break: "read from the leader for a minute after each change". It passes every test
  (lag in tests is milliseconds), then a follower restarts and replays for six minutes, and changes vanish.
- Concept chain: a follower is some position behind, and a read there shows that position → her own change is past
  it → the page needs to know where her change is → carry its position as a token and compare → name:
  read-your-writes → costs: where the token lives, a follower that never catches up (hardest last)
- Analogy family: the track's club notebook. One clerk numbers each line; towns keep copies posted to them. The
  clerk tells you your change's line number, you write it on your hand, and you check a town's last line before
  you read there.
- Open loops: "did the first refund vanish?" planted in scene 1 → paid off in scene 9. "A timer is a promise the
  follower never signed" (scene 4) → "compare positions, not clocks" (scene 9).
- Assumptions: all numbers are the lesson's (1,000 ms refund of pay-41 committed at position 2; reload at 1,010 ms;
  r1 300 ms behind at position 0; caught up at 1,300 ms; one minute and six minutes; support agent's token 0).
  The check question's token 5 and r2 at position 7 are made up for the check.

## The one picture

Top left: the leader (blue) with its log, cells 1 and 2. Top right: follower r1 (teal) with the same cells, empty
until applied, joined by an arrow "300 ms behind". Bottom left: the café owner's phone (white) with her refund list.
Bottom centre: the load balancer, later the router (gold), with arrows up to each machine. The token chip (yellow)
sits under the phone's arrow. A clock chip at the top centre. Red means a wrong screen; green a right one.

## Scene 1 · The refund that vanished · 0:00–0:25 · [QUESTION] [LOOP-PLANT]

VO: Picture a café owner at closing time. A customer's coffee was charged twice, so she opens the payments app on
her phone and taps Refund. The app says, refund sent. She reloads the page to check, and the refund isn't in the
list. So she taps Refund again. Did the first refund vanish? And if it didn't, why couldn't she see it? Hold that
question.

SCREEN: Title card. A large phone: "café app", "refunds". A "Refund sent" toast. The list reloads: "(none)". A gold
ring on the phone (second tap). A yellow "?".

## Scene 2 · The notebook and its copies · 0:25–1:00 · [FAMILIAR] [ANALOGY]

VO: Picture a club's notebook. One clerk writes each change on the next numbered line. Copies are posted to other
towns, and each town's copy is right as of the last letter it got. The payments app works the same way. One
computer, the leader, writes every change at the next position in its log, a numbered list of changes. Other
computers, the followers, copy that log in order, a little later. Most pages read from a follower, so the leader
keeps its time for card payments. And a read on a follower shows the data as of that follower's position.

SCREEN: The phone shrinks to the bottom left. Two boxes with grey subtitles "the clerk's notebook" and "a town's
copy", then their titles "leader" and "follower r1". Cells 1 and 2 on each, dots run along the arrow and fill r1's
cells. Caption: "a read on a follower shows that follower's position".

## Scene 3 · Her evening on the clock · 1:00–1:45 · [SHOW] [PAIN] [JOKE:release] [WISH]

VO: Now let's put a clock on her evening. At 1,000 ms, she asks for a refund of pay-41. The leader commits it,
writes it for good, at position 2. At 1,010 ms, her page reloads. A load balancer, a program that spreads reads
across the followers, sends the question to follower r1. r1 is 300 ms behind. It's still at position 0. So the
refund list is empty, and she taps Refund again. The database turns the second refund away as a repeat, so no money
is lost. But the screen was wrong, and her call to the
support line is real. Her refund was safe the whole time. It was only in the post. So the real question is: how can
a page tell whether this copy has her change yet?

SCREEN: Clock "1,000 ms". r1's cells empty, "position 0". A refund chip runs to the leader's cell 2 (gold). Clock
"1,010 ms"; "load balancer" box; a dot from the phone to it, then up to r1; the list shows "(none)" in red. A dot
crawls along the leader-to-r1 arrow, still on its way. Caption: "does this copy have her change yet?"

## Scene 4 · Two obvious fixes · 1:45–2:35 · [BREAK] [PREDICT] [PAUSE] [JOKE:is-the-explanation]

VO: You might be thinking: send her reads to the leader. That's correct. But most pages show a shop owner's own
data, so soon the leader takes most reads again. Here's a cleverer one. For one
minute after each change she makes, read from the leader. After that, a follower is surely caught up. Will this
hold? Pause and guess.

(three seconds)

It passes every test, because on a quiet test computer, lag is a few milliseconds. Then one night a follower
restarts and spends six minutes catching up. For every owner who changed something in that window, the change
vanishes. One minute was a guess about the clock. A timer is a promise the follower never signed.

SCREEN: Caption "1. every read of her own data: the leader"; the leader-bound arrow thickens with many dots, the
leader glows red. Caption "2. the leader for 1 minute after each change"; a countdown. Then r1's label "restarting:
6 minutes to catch up" in red; the clock jumps past one minute; the read goes to r1; the list shows "(none)" again.

## Scene 5 · The number on your hand · 2:35–3:10 · [ANALOGY] [MAP]

VO: Back to the club. When you send the clerk a change, she writes it on line 2 and tells you: line 2. You write that
on the back of your hand. Later you walk into a town's reading room. First, you look at its last line. Line 0? Your
change hasn't arrived. Wait a little, or go to the clerk's own notebook. Line 2 or later? Read right there. Now map
it. The line number is the log position. The number on your hand is a token, kept in her session, the app's memory
of one signed-in user. And whoever checks the last line before you read is the router, the part of the app that picks
a machine for each read.

SCREEN: The subtitles glow. Chip "on your hand: line 2". The gold box becomes "checks the last line". Then each label
swaps to its technical name as it is mapped: "token: 2 (her session)", "router".

## Scene 6 · Replay it with the token · 3:10–3:50 · [SHRINK] [PREDICT] [PAUSE] [SHOW]

VO: Let's replay her evening with the token. At 1,000 ms, the leader commits the refund at position 2 and sends that
position back. Her session keeps it: token 2. At 1,010 ms, the page reloads. The router asks r1 for its position. r1
says 0. Where does this read go? Pause and guess.

(three seconds)

0 is below 2, so the read goes to the leader. The refund is listed. She doesn't tap again. At 1,300 ms, r1 has
applied position 2. Now 2 is at or past 2, so her reads go back to r1. The leader only took the reads that would have
been wrong.

SCREEN: Reset: r1 at 0, clock 1,000 ms. A dot carries "2" from the leader back to the token chip. Clock 1,010 ms; the
router asks r1 (a dot up and back), "r1: 0 < 2"; countdown. Arrow to the leader lights; the list shows "pay-41
refund" in green. Clock 1,300 ms; r1's cell 2 fills, "position 2", "r1: 2 ≥ 2", the arrow to r1 lights.

## Scene 7 · The name, and what it doesn't promise · 3:50–4:15 · [NAME]

VO: This promise has a name: read-your-writes. After you change something, your own reads always show the change.
Notice what it doesn't promise. A support agent who changed nothing has token 0. Every follower qualifies, so the
agent may not see the refund yet. That's allowed.

SCREEN: Caption "read-your-writes: your own reads show your own changes". The token chip becomes "support agent:
token 0", "r1: 0 ≥ 0", then the caption "it covers only your own changes".

## Scene 8 · Two costs, one more option · 4:15–4:55 · [GUARDRAIL]

VO: Two costs come with the token. First, it must live where every one of her requests can find it. A cookie, the
small note a website keeps in one browser, works for one browser. But she refunds on her phone and checks on her
laptop. So the server keeps the token, under her account. Second, a follower that's paused or broken may never catch
up. Don't let a read wait forever. Wait a short time, then go to the leader. There's one more option: make every
commit wait until a follower has applied it. Every read is fresh, and every payment pays for it. On PostgreSQL, a
free database program, the token is the log position, read right after the commit. The check on the follower is one
comparison.

SCREEN: Captions for each cost; the token chip reads "kept by the server, under her account". r1 "paused" in red,
a short countdown, then the arrow to the leader. A code card over the dimmed picture:
`SELECT pg_current_wal_lsn();` (on the leader, right after the commit: the token) and
`SELECT pg_last_wal_replay_lsn() >= token;` (on the follower, before the read).

## Scene 9 · The moral, and a check · 4:55–5:25 · [MORAL] [LOOP-PAYOFF] [RECAP] [PREDICT] [PAUSE]

VO: So, did her first refund vanish? No. It was on the leader all along. She read a copy that hadn't reached it. The
fix is to carry her last write's position, and refuse to read below it. Compare positions, not clocks. One quick
check. Her token is 5. Follower r2 is at position 7. Where can her read go? Pause and think.

(three seconds)

To r2. 7 is past 5, so her change is already there.

SCREEN: Caption "carry the position; refuse to read below it", then "compare positions, not clocks". For the check:
the token chip "token: 5", the follower becomes "follower r2", "position 7"; countdown; "r2: 7 ≥ 5" and the arrow to
r2 lights green.

---

### Beat check

- QUESTION opens (scene 1). FAMILIAR + ANALOGY (scene 2) before the pain on the clock (scene 3).
- BREAK: the two obvious fixes, the second with a PREDICT and PAUSE (scene 4). ANALOGY + MAP for the fix (scene 5).
- PREDICT + PAUSE + SHOW with the token (scene 6). NAME after the show (scene 7). GUARDRAIL (scene 8), MORAL and a
  check (scene 9). Light moments: "only in the post" (1:40), "a promise the follower never signed" (2:30).

### Accuracy notes for the producer

- Position 1 in the log is an earlier change the lesson doesn't name; the video shows it as a plain cell.
- The lesson's stepper has the router "wait on r1 if a short wait is allowed" or go to the leader; the video sends
  the read to the leader and mentions the short wait in the analogy and the guardrail.
- The lesson's option 4 is PostgreSQL's `synchronous_commit = remote_apply`; the video says it in plain words only.
  MySQL's GTID sets and MongoDB's causally consistent sessions are left to the lesson.
- The video says the database turns the second refund away "as a repeat"; the lesson names the idempotency key.
- The lesson notes a moment after replay resumes where the check can still say false; that's why the guardrail says
  "wait a short time, then go to the leader".
