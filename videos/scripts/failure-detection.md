# Slow or dead? How long to wait before you call it

- Slug / scene: `failure-detection`, `videos/scenes/failure_detection.py:FailureDetection`
- Lesson: `dist-02`, section 0, "How long to wait: a timeout trades slow detection for false alarms"
- Audience / level: a complete newcomer. Has waited for a text that didn't come; knows nothing about heartbeats,
  failure detectors, failover or network delay.
- Length: 5:27 (~880 words of narration at Kokoro's ~175 words a minute, plus two pauses and silent builds)
- Poster: `POSTER=229` (the jittery link's histogram, the three bars past T = 1.5 s in red, "15 false alarms")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: a machine has gone quiet. Is it dead or just slow, and how long should we wait before
  acting as if it's dead?
- Misconception to steelman and break: (1) "the watcher can tell slow from dead", broken by the stuck heartbeat that
  looks exactly like a crash; (2) "pick one good timeout for everything" (the hiker's one deadline for every walk),
  broken by the table: 1.5 s is perfect on the calm link and raises 15 false alarms on the jittery one; 3 s is quiet on
  both and makes the calm link twice as slow.
- Concept chain: silence is all a watcher can see → heartbeats make silence measurable → a timeout T turns silence into
  a verdict → long T strands work, short T raises false alarms → pick T from measured gaps → one T can't suit two
  links (hardest last) → bridge to a timeout that learns
- Analogy family: the lesson's hiking friend who texts "all good" every half hour; the helicopter that finds her eating
  a sandwich (false alarm); the city walk and the mountain walk (calm and jittery links).
- Open loops: "when do you call rescue?" planted in scene 1 → answered in scene 8; the hiker's one deadline for every
  walk (lesson opening) → broken in scene 6.
- Assumptions: numbers are the lesson's (heartbeat every second; 2,000 payments a second x 10 s = 20,000; calm link
  1 to 5 ms, jittery link 30 to 830 ms; 1.5 s: 0 and 15 false alarms in 5 minutes, 1,509 ms to notice on the calm link;
  3 s: 0 and 0, 3,009 and 3,719 ms; Elasticsearch: 3 s timeout, about 1 start in 10, 15 s fixed it). The jittery
  histogram is drawn from 300 simulated gaps seeded so that exactly 15 pass 1.5 s, as in the lab; its shape is
  illustrative. The stuck heartbeat in scene 4 is an illustration.

## The one picture

Top row: the payments machine (blue), the watcher (teal) and the standby (grey, gold when it takes over), joined by
the heartbeat arrow (yellow dots) and the failover arrow (gold). Mapping labels under each box. Under them, the silence
bar (yellow, red once past T) on a 0 to 3 s scale, and a red dashed T line. Below, sharing the same scale, the histogram
of gaps (teal for the calm link, gold for the jittery link, red past T). Captions at the bottom.

## Scene 1 · The hike · 0:00–0:28 · [QUESTION] [FAMILIAR] [LOOP-PLANT] [JOKE:pivot]

VO: Your friend is hiking alone, and she promised to text you "all good" every half hour. An hour passes. Nothing.
Maybe she fell. Maybe she's in a valley with no signal. Maybe her phone is flat. From your sofa, all three look exactly
the same: silence. So when do you call rescue? Call too soon, and a helicopter finds her eating a sandwich. Call too
late, and help arrives late.

SCREEN: A phone with two green "all good" bubbles (10:00, 10:30), "no message for an hour", 11:30. Three gold causes on
the left, each arrow into the phone, one arrow out to a red "silence" chip. Captions: "when do you call rescue?", the
too-soon and too-late costs.

## Scene 2 · Heartbeats, a watcher, a timeout · 0:28–1:30 · [ANALOGY] [MAP] [NAME]

VO: Put the hike into a payments app. One machine records every café's payments. A second machine watches it, ready
to hand its work to a spare, the standby, if it dies. The watcher can't see inside the first machine. All it sees is
messages. So the first machine sends a small "I'm alive" message every second. That's called a heartbeat, like your
friend's text. Map it out loud. Your friend is the machine. Her text is the heartbeat. You, on the sofa, are the
watcher. And the rescue team is the standby. Now watch the silence: the time since the last heartbeat. It grows, and
each heartbeat drops it back to zero. A healthy machine is never quiet for long. So the watcher keeps one rule: if
nothing has arrived for T seconds, suspect the machine. A program with a rule like that is called a failure detector,
and T is its timeout. The only question is how big T should be. And neither answer is free.

SCREEN: The three boxes appear, the heartbeat arrow grows and dots run along it. Mapping labels appear one by one as
they are said. The silence bar grows to 1 s and drops to zero with each heartbeat.

## Scene 3 · A long timeout · 1:30–2:00 · [PAIN]

VO: Try a long timeout first: ten seconds. Now the machine dies. The watcher waits, ten whole seconds. Meanwhile
payments keep arriving, two thousand a second, and nobody takes them. By the time it acts, twenty thousand payments
are stranded. Only then does the standby take over. That step has a name too: failover.

SCREEN: "T = 10 s" off the right of the scale. A red cross on the machine. The silence bar fills the scale; counters
climb to "silence: 10 s" and "payments with nowhere to go: 20,000"; caption "10 s x 2,000 payments a second = 20,000
stranded". The failover arrow grows and the standby turns gold.

## Scene 4 · A short timeout · 2:00–3:10 · [PAIN] [BREAK] [JOKE:release] [WISH] [NAME]

VO: So make it short. Say one and a half seconds. The machine is fine this time. But one heartbeat gets stuck on the
way. The silence passes T. The watcher declares a live machine dead, and the standby takes over its work. But the first
machine is still doing that work. Two machines, one job: a whole machine's worth of payments, charged twice. Well...
the helicopter just found her eating a sandwich. That wrong verdict is called a false alarm. And it spreads. The moved
work slows other machines' heartbeats, and the next false alarm follows. A group can talk itself into declaring
everyone dead. This happens for real. Elasticsearch, a search program that runs on a group of machines, split itself
in two on about one start in ten, because its machines were sometimes slower than its three second timeout. Fifteen
seconds fixed it. Wouldn't it be nice if the watcher could just tell slow from dead? It can't. From where it sits, a
slow heartbeat and a dead machine send exactly the same thing: nothing. A timeout detects silence, not death.

SCREEN: The T line at 1.5 s. Two normal cycles, then a slow dot; the bar passes T and turns red; "verdict: dead"; the
standby turns gold while the machine keeps working (both pulse gold). Captions carry the false alarm, the cascade, the
Elasticsearch case, and the key line in yellow.

NOTE: The joke comes right after the failure, and is cashed back at once into the name "false alarm".

## Scene 5 · Pick T from data · 3:10–4:25 · [SHRINK] [SHOW] [PREDICT] [PAUSE] [SHOW]

VO: So we pick T from data. Every time a heartbeat lands, write down the gap since the one before. Then stack the gaps
up. Start with a calm link inside one building, where each heartbeat takes one to five milliseconds. Five minutes of
gaps, and every one lands within a few milliseconds of one second. With T at one and a half seconds, no gap reaches it:
no false alarms. And when the machine dies, the watcher notices in about one and a half seconds. Now a jittery link
between two regions far apart, where each heartbeat takes anywhere from 30 to 830 milliseconds. Same timeout, one and
a half seconds. In five minutes, how many false alarms? Pause and guess.

(three seconds)

Fifteen. On a machine that never failed. Here's why. A gap is one second, plus the difference between two delays. One
heartbeat comes fast, the next one slow, and a gap can stretch to 1.8 seconds. Every gap past T is a false alarm. And
every bit of T is time a dead machine goes unnoticed. So move T out to three seconds. Now both links are quiet. But the
calm link waits three seconds to notice a crash, twice as long as it needs.

SCREEN: The histogram axis appears under the silence bar, same scale. Each gap's bar drops down into its bin as a
brick. Calm: one tall teal bar at 1 s, "all 300 gaps". Jittery: five bricks, then the full gold histogram; bars past
1.5 s turn red, "15 false alarms". The T line moves to 3 s; the red bars go gold, "0 false alarms".

## Scene 6 · One number for both links · 4:25–4:50 · [BREAK] [LOOP-PAYOFF]

VO: Side by side. At one and a half seconds, the calm link is perfect and the jittery link raises fifteen false alarms.
At three seconds, both are quiet, and the calm link is twice as slow. Remember the tempting plan for the hike: one
deadline, say an hour, for every walk. But she's never late in the city, and often late in the mountains. One number
can't suit both links either.

SCREEN: A table: calm link / jittery link against T = 1.5 s and T = 3 s (0 false alarms, 1.5 s to notice; 0, 3 s; 15
false alarms; 0, 3.7 s). Caption "one number can't suit both links".

## Scene 7 · Rules · 4:50–5:05 · [GUARDRAIL]

VO: So, a few rules. Measure the gaps over days and over many machines, and put T beyond the gaps you see when things
are normal. And if one link needs a quick verdict and the other needs patience, you need a timeout that learns what
normal looks like. That comes next.

SCREEN: Numbered captions: measure over days and machines; put T beyond normal gaps; long T strands payments, short T
does the work twice.

## Scene 8 · The moral, and a check · 5:05–5:27 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, when do you call rescue? When the silence is longer than anything you've measured as normal. A timeout detects
silence, not death. One quick check. Heartbeats come every second on the calm link, T is three seconds, and the
machine dies. At the very least, how long until the watcher suspects it? Pause and think.

(three seconds)

Three seconds. The timeout itself is the least time any crash takes to notice. That's the price of every second of T.

SCREEN: The silence bar grows past normal; the key line in yellow. For the check, the machine gets a red cross; after
the countdown the bar fills to 3 s and turns red, "verdict: dead, after 3 s".

---

### Beat check

- Opens with QUESTION from a felt situation (the hiker's silence); FAMILIAR is the everyday wait.
- ANALOGY + MAP said out loud (scene 2) before the names heartbeat, failure detector, timeout; failover and false
  alarm are named after they are shown.
- PREDICT with PAUSE: the false-alarm count (scene 5) and the check (scene 8).
- BREAK: the stuck heartbeat (scene 4) and one number for two links (scene 6).
- GUARDRAIL (scene 7) and MORAL (scene 8) last. Light moments: the sandwich (0:20, called back at 2:25).

### Accuracy notes for the producer

- The lab's numbers come from its `DetectorDemo` output (fixed 1,500 ms: 0 / 1,509 ms on the calm link, 15 false
  alarms on the jittery link; fixed 3,000 ms: 3,009 and 3,719 ms). The table rounds them to 1.5 s, 3 s and 3.7 s.
- The jittery histogram's shape is simulated (uniform delays of 30 to 830 ms, 300 gaps); only the 15 is the lab's.
- "No false alarms" means none in the lab's 5 minutes, not never.
- The detection time on the jittery link is longer than T because the last heartbeat's own delay is added; the video
  says only "at the very least" for the calm link.
- Left to the lesson: TCP's adaptive timeout, phi accrual, SWIM and gray failure (sections 1 to 3).
