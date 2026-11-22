# Frozen between the check and the write

- Slug / scene: `process-pause`, `videos/scenes/process_pause.py:ProcessPause`
- Lesson: `dist-04`, section 0, "A worker checks its lease, freezes, and writes too late"
- Audience / level: a complete newcomer. Has been on a video call that froze; knows nothing about leases, threads,
  the JVM or check-then-act.
- Length: 5:30 (~850 words of narration, plus two pauses and silent builds)
- Poster: `POSTER=164`, the moment A's late update lands: the frozen band, lease 1 ended, lease 2 and B's 13
  updates, A's red tick and the red gap arrow
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: my code checks that it still holds the lease right before it writes. How can it still
  write without the lease?
- Misconception to steelman and break: (1) "the check and the write are one step" (they run a millionth of a second
  apart on a laptop and every test agrees), broken by the lab's 3-second pause; (2) "just check again right before
  writing", fair first (the 1,520 ms pause is caught), then broken by the same pause 42 ms later.
- Concept chain: one writer at a time → a lease that runs out on its own → the loop: check, then act → a pause between
  them → a late write the ledger accepts → check-then-act; a second check only moves the gap (hardest last) → the fix
  must live outside the program
- Analogy family: the lesson's friend frozen on a video call, answering a question everyone has moved past; a
  sleepwalker double-checking that they're awake (the checker is what freezes).
- Open loops: "what if a program freezes in the middle of a job?" planted in scene 1 → answered in scene 3; "the real
  fix lives outside A" planted in scene 6 → the next lesson (fencing tokens).
- Assumptions: every time is the lab's `TimelineDemo` (check at 1,500 ms with 1.6 s left; pause 1,520 to 4,520; lease 1
  ends 3,105; lease 2 to B at 3,155; B's updates from 3,320 every 100 ms; A's update at 4,530 on top of 13 of B's; the
  careful worker drops its update; with the pause at 1,562 the update lands at 4,567). A's earlier updates on the ledger
  lane (every 100 ms up to 1,470) and B's "asks every 100 ms" are drawn from the lesson's loop; the frozen-call
  dialogue ("Tuesday", "Thursday") is invented for the opening.

## The one picture

One timeline, 0 to 5,200 ms, with four lanes: worker A (blue running, grey frozen), the lease service (lease 1 blue,
lease 2 green), worker B (green once it holds lease 2) and ledger M-0042 (blue ticks for A's updates, green for B's,
red for a late one). A yellow playhead with a clock readout plays the run. Top left: A's loop as three steps (check,
build, write), with the current step boxed. In scene 5 the top becomes a zoomed strip of 1,490 to 1,590 ms (check,
build 60 ms, check again, send, and a red "freeze" marker).

## Scene 1 · The frozen call · 0:00–0:30 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: Picture a video call with a friend. Her picture freezes, halfway through a sentence. Ten seconds later, it moves
again, and she finishes the sentence: answering a question everyone else has already moved past. From her side,
nothing happened. Programs freeze the same way, and they can't feel it either. So what if a program freezes in the
middle of a job?

SCREEN: A call tile with a face; "frozen" and a counter to 10 s; the half sentence finishes ("...Tuesday!") under the
caption "everyone else: already on Thursday".

## Scene 2 · The lease · 0:30–1:25 · [FAMILIAR] [NAME] [PAIN]

VO: A small company records card payments for shops. Each shop has a ledger, the list of every change to its balance.
Two updates at the same moment could both start from the old balance and lose a change. So only one worker may update
it at a time. There are two workers, A and B, running the same code, so one can take over if the other dies. They agree
on who may write with a lease: a permission to act that runs out on its own. A lease service grants A the lease for two
seconds, and A renews it whenever less than one second is left. If A crashes, the renewals stop, the lease runs out,
and B gets it. Nobody has to decide whether A is dead. Worker A's loop runs every 100 milliseconds. First the check: is
my lease still valid? Then the act: build the update, and write it. On a laptop, the check and the write run a
millionth of a second apart. So it's easy to treat them as one step, and every test you run agrees with you.

SCREEN: Lane labels and guides appear as named; lease 1 grows on the service lane with a renewal tick at 1,100; the
loop's three steps appear top left and are boxed in turn.

## Scene 3 · The run · 1:25–2:50 · [SHOW] [PREDICT] [PAUSE] [SHOW]

VO: Here is one run from the lab's simulator, which plays out the workers, the service and the ledger on a pretend
clock, so the same run happens every time. At 1,500 milliseconds, A checks. Its lease has 1.6 seconds left. So it
starts building the update. At 1,520, the JVM, the program that runs Java and Kotlin code, stops A for three seconds.
Why it would do that is a story for the next part. Here's the question. When A wakes up, does its update reach the
ledger? Pause and guess.

(three seconds)

Watch the clock. Worker A is frozen, so it sends no renewals. At 3,105, lease 1 runs out. That's the service doing its
job. At 3,155, B asks, and gets lease 2. From 3,320, B's updates land, one every 100 milliseconds. The ledger has no
reason to doubt them. B really is the holder now. At 4,520, A runs again. From the inside, nothing happened. It was in
the middle of building its update, so it finishes, and writes. 4,530. The ledger applies A's update, 1.4 seconds after
A's lease ran out, on top of 13 updates from B. So, yes, it gets through. Worker A finds out its lease is gone at its
next check, 100 milliseconds too late to matter.

SCREEN: The playhead runs; A's blue band and ledger ticks; the check dot "check: 1.6 s left"; the grey frozen band grows
with the clock; "runs out 3,105"; lease 2 and B's band; 13 green ticks; A's red tick at 4,530 and a red double arrow
from 3,105 to 4,530.

## Scene 4 · The map, and the name · 2:50–3:35 · [MAP] [BREAK of the analogy] [NAME] [PRINCIPLE]

VO: It's the video call. Worker A is the friend. The three seconds frozen is the frozen picture. And the lease that ran
out is the question everyone already moved past. But here the picture breaks. On a call, everyone waits for her. Here,
nobody waits. The service hands the lease to B, and the ledger takes A's late write as if it were on time. The check was
right when it ran. Then worker A stopped between the check and the act. This pattern, checking and then acting as a
separate step, is called check-then-act. Every lease and every lock has one. Seen from inside, a program is one
continuous run. Seen from outside, it can stop between any two steps, for any length of time.

SCREEN: Each part of the picture pulses as it is mapped. Captions: "on a call, everyone waits. here, nobody waits.", the
name, and the principle in yellow.

## Scene 5 · Check again · 3:35–4:30 · [BREAK] [SHOW] [JOKE:is-the-explanation]

VO: The obvious fix: check again, right before you write. The lab's careful worker does exactly that, with 200
milliseconds to spare. Same pause, at 1,520, in the middle of the build. When A wakes up, its second check fails, and it
drops the update. Fixed? Let's be fair to it: that run has no stale write at all. Now start the same pause 42
milliseconds later, at 1,562. That's just after the second check, while the update is on its way. At 4,567, the ledger
applies A's stale update again. The second check didn't close the gap. It only moved it. Asking a frozen program to
check once more is like asking a sleepwalker to double-check that they're awake. The one doing the checking is the one
that freezes.

SCREEN: The zoomed strip (1,490 to 1,590 ms) with dashed lines down to the timeline: check, build 60 ms, check again,
send. A red "freeze" marker at 1,520; the second check turns red and the 4,530 tick goes. The marker slides to 1,562; a
red tick lands at 4,567.

## Scene 6 · Guardrail · 4:30–4:55 · [GUARDRAIL] [LOOP-PLANT]

VO: So keep the checks. They're cheap, and in the lab they made stale writes about fourteen times rarer. But never
impossible. What freezes programs? Memory clean-up, the cloud, the operating system, a slow disk. The rest of the lesson
measures each one. And the real fix lives outside A: someone who sees every write has to refuse the late one. That's the
next lesson.

## Scene 7 · The moral, and a check · 4:55–5:25 · [MORAL] [PREDICT] [PAUSE]

VO: So, the moral. A check tells you about the moment it ran, and nothing after. Between any two steps, the world can
move on without you. One quick check. Say A's freeze at 1,520 had lasted one second instead of three. Would its update
be late? Pause and think.

(three seconds)

No. Worker A wakes at 2,520, and lease 1 doesn't run out until 3,105. A pause only hurts when it outlasts what's left
of the lease.

SCREEN: The frozen band shrinks to 1 s (1,520 to 2,520); lease 2 and B's lane clear; a green tick lands at 2,530 inside
lease 1.

---

### Beat check

- Opens with QUESTION from a felt situation (the frozen call); FAMILIAR is the lease and a loop that looks airtight.
- PREDICT with PAUSE: "does A's update reach the ledger?" (scene 3) and the check (scene 7).
- ANALOGY mapped and its breaking point said (scene 4: nobody waits).
- BREAK: the one-step model (scene 3) and the second check (scene 5), fair first.
- NAME after the SHOW: check-then-act (scene 4). GUARDRAIL and MORAL last. Light moments: the frozen friend's
  "Tuesday!", the sleepwalker (scene 5, the joke is the explanation).

### Accuracy notes for the producer

- Times are the lab's simulator with every message taking 5 ms; real pauses and delays vary.
- "13 updates from B" counts B's 12 from 3,320 to 4,420 plus the one at 4,520, as in the lesson.
- "About fourteen times rarer" is the lesson's closing figure for the careful worker in the lab's randomized runs.
- The check question is reasoned from the picture (lease 1 lasts to 3,105); the lab didn't print a 1-second run.
- Left to the lesson: why the JVM stops threads (garbage collection), the cloud and disk pauses, and why a program
  can't catch its own pause in time.
