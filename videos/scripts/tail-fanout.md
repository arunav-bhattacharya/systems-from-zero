# Waiting for a hundred answers: fan-out, the tail and a second copy

- Slug / scene: `tail-fanout`, `videos/scenes/tail_fanout.py:TailFanout`
- Lesson: `found-02`, section 3, "When one screen waits for a hundred answers: fan-out and the tail"
- Audience / level: a complete newcomer. Can read a little code; knows nothing about servers, databases or
  replicas. Has met "slow one time in a hundred" only as plain words.
- Length: 5:08 (~750 words of narration at Kokoro's ~180 words a minute, plus three pauses, a silent run of ten
  trays and the builds)
- Poster: `POSTER=217` (the hedged screen at 23 ms: phone, tray, replica, arc and the hedged-request chip)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: if each part is fast 99 times in 100, why is the whole screen slow most of the
  time? And what can you do about a slowness you can't remove?
- Misconception to steelman and break: "the whole is as reliable as its parts: each piece is slow 1 time in 100,
  so the screen is slow about 1 time in 100". Broken by sending out ten trays (six are late) and by the
  arithmetic, 0.99 multiplied by itself 100 times is 0.37.
- Concept chain: waiting for all of many answers → the rare slow one turns up most of the time (fan-out, the tail,
  tail latency amplification) → each part would need to be far better → instead, stop waiting for the unlucky
  one (a hedged request to a replica) → when a hedge can't help (shared slowness, not safe to run twice)
- Analogy family: the café's kitchen. A tray of 100 sandwiches that leaves only when every slot is full; 100 cooks,
  one sandwich each; a dropped sandwich (the pause); a second cook who makes the same sandwich (the replica); the
  staff eat the spare (the cost); one shared toaster that jams (shared slowness).
- Open loops: "why is the screen slow most of the time?" planted in scene 1 → answered in scene 8; "nobody can
  leave" (the tray waits for the last cook) in scene 2 → the fix "stop waiting for the unlucky one" in scene 6.
- Assumptions: numbers are the lesson's (100 leaves, 5 to 15 ms, one time in 100 a full second, 63 in 100 slow,
  hedge after 15 ms → p99 30 ms for 1% more requests). The kitchen times
  aren't to scale. The ten trays are one seeded random run, picked to land near the true rate.

## The one picture

Left: the owner's phone (white), showing the time the home screen takes. Centre: a tray (grey outline) of 100
slots, a 10 by 10 grid; each slot is a cook, later a leaf. Grey means waiting to start, yellow means working,
green means done, red means stuck in a pause, teal means filled by the second copy. Ten grey lines fan out from
the phone to the tray's rows. Right: the second cook, later the replica (teal), joined to the unlucky slot by a
dashed "same data" line; the hedge is a teal arc from the phone over the tray. Below: one shared toaster for the
guardrail. Captions sit along the bottom. At most six things on screen.

## Scene 1 · The symptom · 0:00–0:28 · [QUESTION] [LOOP-PLANT]

VO: The café owner opens her app's home screen. Some mornings it appears at once. Most mornings, it hangs for a whole
second. Here's the odd part. The screen is built from 100 small answers, and each one is slow only one time in a
hundred. So why is the screen slow most of the time?

SCREEN: A large phone, "home screen", a timer that stops at 12 ms, then runs to 1,000 ms. Left: "100 small
answers, each slow 1 time in 100". Right, in red: "the screen: slow most mornings". A "?" above.

NOTE: The phone then shrinks into its place on the left and dims while we leave the app.

## Scene 2 · The tray · 0:28–1:00 · [FAMILIAR] [ANALOGY] [JOKE:pivot]

VO: Let's leave the app and go to the café's kitchen. A big order comes in: a tray of 100 sandwiches. A hundred cooks
make one each, all at once. The tray goes out only when every slot is full. Each sandwich is quick. But one time in
a hundred, a cook drops it on the floor and starts again. Now the whole tray waits for that one cook. Ninety-nine
slots are full, and nobody can leave.

SCREEN: The tray and its 100 slots draw in; "the tray: 100 slots, 100 cooks". All slots turn yellow, then fill
green one by one; one slot (row 4, column 10) turns red on "drops it". The tray's outline pulses; caption "99
full, 1 empty: the tray waits".

NOTE: The dropped sandwich is the light moment and the mechanism: one rare delay holds up everything.

## Scene 3 · Predict, then send ten trays · 1:00–1:46 · [SHRINK] [PREDICT] [PAUSE] [SHOW] [BREAK] [JOKE:release]

VO: So each cook is late one time in a hundred. How often is the tray late? Pause and guess.

(three seconds)

Most people say about one in a hundred, since that's what each cook does. Let's send out ten trays and watch. Six of
the ten were late. Well... that's not one in a hundred. The tray is on time only if all 100 cooks are. Each one is
on time 99 times in 100, so 0.99. All 100: 0.99 multiplied by itself 100 times, about 0.37. So the tray is late 63
times in 100. Every extra cook is one more chance to draw the dropped sandwich.

SCREEN: Countdown bar. Caption "about 1 in 100?" Ten small tray icons below the tray. Each run: the slots go
yellow, fill green, and any dropped ones go red; the icon turns red if any slot is red, green otherwise. "late: 6
of 10". Captions: "one cook on time: 0.99", "all 100 on time: 0.99 × 0.99 × ... (100 times) = 0.37", "on time:
37 in 100. late: 63 in 100".

NOTE: The wrong guess is steelmanned (it's what each cook does) and broken by the run before the formula.

## Scene 4 · The app works the same way · 1:46–2:40 · [MAP] [NAME]

VO: The app works the same way, in thousandths of a second, called milliseconds. To draw the home screen, the program
asks 100 places for a piece each, all at once, and waits for every answer. Each place, a small program or a piece of
a big database, is called a leaf. The screen is the tray, and the leaves are the cooks. A leaf answers in 5 to 15
milliseconds. But one time in a hundred, it hits a pause and takes a full second. And the screen waits the whole
second. When one request sets off many requests behind it, that's called fan-out. The rare slow answers are called
the tail, because they sit at the slow end when you sort the times. Fan-out turns the tail into the normal case: 63
screens in 100 take a second. That's called tail latency amplification, where latency is the time you wait.

SCREEN: The phone lights up with a timer. Ten lines grow from the phone to the tray's rows, and dots run along
them. The label becomes "the screen: 100 leaves (the cooks)". The timer runs to 15 ms while slots go green; the
unlucky slot goes red; the timer runs on to 1,000 ms. "fan-out" appears under the fan. Captions: "the tail: the
rare slow end of the answer times", then "fan-out turns the tail into the normal case: 63 screens in 100 take a
second".

NOTE: Each mapping is said out loud: the screen is the tray, a leaf is a cook, the pause is the dropped sandwich.

## Scene 5 · Fix the leaves? · 2:40–3:00 · [PAIN] [WISH]

VO: So, fix the leaves? To keep only 1 screen in 100 slow, each leaf could be slow only once in 10,000 answers. And
some pauses can't be removed at all. Wouldn't it be nice to stop waiting for the unlucky one?

SCREEN: Captions "1 slow screen in 100 needs each leaf slow only 1 in 10,000", then "stop waiting for the unlucky
one?". The red slot pulses.

## Scene 6 · A second cook · 3:00–4:02 · [ANALOGY] [MAP] [PREDICT] [PAUSE] [SHOW] [NAME] [JOKE:reward]

VO: Back in the kitchen, the answer is plain. If a slot is still empty after longer than a sandwich usually takes, ask
a second cook to make the same one, and use whichever is ready first. And the spare sandwich? The staff eat it. So
the cost is a little extra work, only for the late ones. In the app, the second cook is a replica: another computer
that holds a copy of the same data. The program waits 15 milliseconds, longer than any quick leaf takes. Then it
sends the same request to the replica, and keeps the first answer back. How long does the screen take now? Pause
and guess.

(three seconds)

23 milliseconds. The replica answered while the first leaf was still stuck. That second copy is called a hedged
request. Over many screens, 99 in 100 now finish within 30 milliseconds, and only 1 request in 100 needed a copy. A
common rule is to wait as long as 95 answers in 100 take, so at most about 5 in 100 get a copy.

SCREEN: The tray reruns to the red slot. A teal box "second cook" appears on the right, with a dashed line "same
sandwich" to the red slot; a teal dot runs along it and the slot fills teal. Captions "the spare: the staff eat
it", "the cost: a little extra work, only for late ones". The labels become "replica" and "same data". Rerun with
the timer: at 15 ms a teal arc grows from the phone over the tray to the replica and a dot runs along it;
countdown; then a green dot runs back, the slot fills teal and the timer stops at 23 ms. A chip "hedged request"
under the replica. Captions with the numbers (the lab's p99 and extra requests, then the 95-in-100 rule).

NOTE: The joke (the staff eat the spare) is cashed straight back into the cost. Nothing funny inside the run.

## Scene 7 · When a hedge can't help · 4:02–4:42 · [GUARDRAIL] [BREAK]

VO: A hedge needs two things. First, each copy must be slow for its own reasons. If both cooks share one toaster and it
jams, the second cook is stuck too. In a program, that's one faulty new version on every replica, or one overloaded
disk under both. Then the extra request buys nothing. Second, the request must be safe to run twice. A spare
sandwich is fine. A second charge on someone's card is not. Reading a balance twice is harmless. A card payment is
safe only with an idempotency key, a unique label the bank checks so it charges once. Safe to run twice is called
idempotent.

SCREEN: A grey box "one toaster" under the replica, with lines to the replica and to the unlucky slot. It turns
red, then the replica and the arc turn red. The box becomes "one faulty version". Captions for each condition.

## Scene 8 · The moral, and a check · 4:42–5:15 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So why was the screen slow most of the time? It waits for the slowest of 100 answers, and with 100 tries, the rare
slow one turns up most of the time. You can't make every leaf perfect. So stop waiting for the unlucky one: ask a
second copy, and keep the first answer. One quick check. Say the screen asked only 10 leaves. Slow more often, or
less, and roughly how often? Pause and think.

(three seconds)

Less often: about 1 screen in 10. Fewer leaves, fewer chances to draw the slow one.

SCREEN: The red slot pulses and the tray glows: "the slowest of 100 answers sets the time". The arc and replica
glow: "ask a second copy, keep the first answer". For the check, 90 slots dim, leaving one row of 10; countdown;
"less often: about 1 screen in 10".

---

### Beat check

- Opens with QUESTION (scene 1) from a felt symptom (a screen that hangs).
- FAMILIAR + ANALOGY (scene 2) before any technical word; MAP said out loud (scenes 4 and 6).
- PREDICT with PAUSE three times (the tray, the hedged screen, the check); SHOW right after each.
- BREAK: the "1 in 100" model broken by ten trays and the arithmetic (scene 3); the hedge broken by a shared
  toaster (scene 7).
- NAME after the SHOW: leaf, fan-out, tail, tail latency amplification (scene 4), replica and hedged request
  (scene 6), idempotent (scene 7).
- GUARDRAIL (scene 7, plus the cost and the 95-in-100 rule in scene 6) and MORAL (scene 8) come last. Light
  moments: the dropped sandwich, "that's not one in a hundred", the staff eating the spare, the toaster.

### Accuracy notes for the producer

- The leaf model is the lesson's lab (`FanOutDemo.kt`): 5 to 15 ms, or 1,000 ms one time in 100. The lab prints
  63.2% slow screens at 100 leaves (formula 63.4%) and 9.5% at 10 leaves (formula 9.6%); the video says "63 in
  100" and "about 1 in 10".
- The ten trays are one seeded random run (each slot dropped with probability 1 in 100), chosen to show 6 late
  of 10, close to the true 63%. They illustrate; the formula is the claim.
- "23 milliseconds" is the lab's median screen with a hedge after 15 ms; the lab's p99 is 30 ms and the hedge adds
  1.0% more requests. The lab's p99.9 stays at a second (both copies slow, 1 in 10,000 per leaf, about 1 screen in
  100); the video leaves that to the lesson.
- The 95-in-100 rule (hedge after the leaf's p95, about 5% more requests) is from Dean and Barroso, "The Tail at
  Scale" (2013), as quoted in the lesson. Their BigTable result (p99.9 from 1,800 ms to 74 ms for 2% more requests)
  was cut for length and is left to the lesson.
- Tied requests (queue on two servers, the first to start cancels its twin) are left to the lesson.
- The kitchen times aren't to scale; only the program's numbers are real.
