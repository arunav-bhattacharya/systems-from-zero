# The update that arrived first: three leaders, one payment, two answers

- Slug / scene: `multi-leader`, `videos/scenes/multi_leader.py:MultiLeader`
- Lesson: `repl-05`, section 1, "Circles, stars and all-to-all: how the logs travel, and the update that overtakes
  its insert"
- Audience / level: a complete newcomer. Has met a leader and its log; doesn't know topologies, clock skew or
  version vectors.
- Length: about 5 minutes (~800 words of narration, two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: the end of the discard run: eu and us CAPTURED, ap AUTHORIZED, the dropped update crossed out
- The learner's real question: every message arrived, nothing was lost, yet one region disagrees forever. How?
- Misconception to steelman and break: "use timestamps: keep the version with the later time". Broken by the
  lesson's clock 60 ms behind: the capture is stamped -15, and every region keeps the insert.
- Concept chain: a leader in each region → who sends to whom (circle, star, all-to-all; the origin stops echoes) →
  links run at different speeds → an update can overtake its insert → discard leaves the regions apart; timestamps
  agree on the wrong answer → carry what each change had seen and hold early arrivals (version vector)
- Analogy family: the lesson's cafés that each keep a copy of the same notebook and phone each other their new
  lines. The early update is a call that says "mark that payment captured" about a payment the café hasn't heard of.
  The fix is a call that starts "I've already heard Frankfurt's line 1".
- Open loops: "how do three regions end up disagreeing forever?" planted in scene 1 → explained in scene 4, fixed in
  scene 6.
- Assumptions: all numbers are the lesson's stepper and lab (links eu→us 40 ms, eu→ap 150 ms, us→ap 30 ms, us→eu
  40 ms; insert at 0, capture at 45, update at ap at 75, at eu at 85, insert at ap at 150; us clock 60 ms behind,
  stamps -15 and 0). The drawn link lengths aren't to scale.

## The one picture

Three leader boxes in a triangle: eu (Frankfurt) top left, us (Virginia) top right, ap (Asia and the Pacific)
at the bottom, each showing payment pay-81723's status. Grey links between every pair, labelled with their delays.
A clock chip at the top. Messages are chips that travel along the links: gold INSERT, green UPDATE. Red marks a
dropped or wrong result; yellow a held message.

## Scene 1 · Two answers forever · 0:00–0:25 · [QUESTION] [LOOP-PLANT]

VO: Three databases, one in Frankfurt, one in Virginia, one in Asia. They all copy each other. Every message
arrived. Nothing was lost. And yet, for one card payment, two of them say captured and the third says authorized,
and nothing will ever fix it. How do three careful copies end up disagreeing forever?

SCREEN: Title card. The three boxes fade in with final states: CAPTURED, CAPTURED, AUTHORIZED (red). A "?".

## Scene 2 · A leader in every region · 0:25–1:20 · [FAMILIAR] [ANALOGY] [MAP]

VO: Here's how we got here. A leader is the one database that takes writes and puts them in order in its log. With
customers on three continents, one leader means every card tap crosses an ocean. So each region gets its own leader.
It saves its own customers' writes at once, and sends its log to the others a moment later. Picture cafés that each
keep a copy of the same notebook. Each café writes new lines in its own copy, and phones the others its new lines a
little later. The notebooks are the databases, each café is a leader, and the phone calls carry the logs.

SCREEN: Statuses clear. Region names light up. Grey links grow between every pair. Caption "each region: a leader
for its own customers, a follower of the others". The mapping as three captions.

## Scene 3 · Who calls whom · 1:20–2:05 · [SHOW] [NAME]

VO: With three cafés, who calls whom? In a circle, each one passes changes to the next. In a star, one hub hears
everything and passes it on. Both forward, so a change could come home and go round forever. So every change
carries its origin, where it was first written, and a café drops a change it has already applied. Circles and stars
depend on single cafés: lose the hub, and nobody hears anything. So all-to-all is the usual choice: everyone calls
everyone. Its weakness is quieter. The lines run at different speeds.

SCREEN: Yellow arrows round the circle; a dot loops and comes back to eu; a tag "origin: eu" and the dot stops.
The star: us glows "hub"; the eu-ap link dims; then us turns red, "hub down". All three links back: "all-to-all".
Delay labels appear: 40 ms, 150 ms (slow today), 30 ms.

## Scene 4 · The update that overtakes · 2:05–3:20 · [SHRINK] [PREDICT] [PAUSE] [SHOW] [BREAK] [JOKE:release]

VO: Two words for a card payment. When you tap, your bank sets the money aside, and the payment is authorized.
Later the money really moves, and it's captured. At 0 ms, Frankfurt inserts payment pay-81723 as authorized, and
sends the insert to both others. Virginia gets it at 40 ms, and captures the payment at 45. It sends that update on.
Asia's line from Virginia takes 30 ms. Its line from Frankfurt takes 150. So what reaches Asia first? Pause and guess.

(three seconds)

The update, at 75 ms, for a row Asia doesn't have yet. pgactive, a free add-on from Amazon that lets several
PostgreSQL servers all take writes, documents its default for this case: throw the update away. The insert lands at
150 ms. Asia says authorized, the others say captured, and no message is left on its way to repair it. It's a
call saying "change that order to blue" about an order nobody has heard of yet. So the café shrugs, and bins it.

SCREEN: Clock steps 0, 40, 45, 75, 85, 150. A gold INSERT chip runs to us and crawls towards ap. us turns
AUTHORIZED, then CAPTURED; green UPDATE chips leave us. Countdown. The update reaches ap first: "no such row",
crossed out. eu turns CAPTURED at 85. The insert lands at ap: AUTHORIZED, red outline.

## Scene 5 · Timestamps, tested · 3:20–4:00 · [BREAK] [JOKE:soften]

VO: You may be thinking: timestamps. Every leader keeps whichever version carries the later time. But say
Virginia's clock runs 60 ms behind Frankfurt's. Then the capture is stamped minus 15, and the insert 0. Every region
keeps the insert, Virginia included, so it ignores its own capture. They agree, on the wrong answer. A clock is a
very confident witness, and that's all it is.

SCREEN: Reset. The INSERT chip reads "ts 0", the UPDATE "ts -15". "us clock: 60 ms behind". us goes back to
AUTHORIZED; all three AUTHORIZED; caption "they agree, on a capture that never happened".

## Scene 6 · Say what you'd seen · 4:00–4:45 · [ANALOGY] [SHOW] [NAME]

VO: What works is to carry what each change had already seen, instead of the time. Back at the cafés, Virginia's
call starts: I've already heard Frankfurt's line 1. Asia hasn't heard it yet, so it holds the update, and waits. At
150 ms, the insert arrives. Asia applies it, sees the held update is now ready, and applies that too. All three say
captured, whatever the clocks read. That record, one counter per leader, is called a version vector.

SCREEN: Reset. The UPDATE chip reads "needs eu: 1". It reaches ap at 75 and parks in a yellow "held" slot. At 150
the INSERT lands, then the held update applies: all three CAPTURED with ticks. Caption "version vector: one counter
per leader".

## Scene 7 · Moral, guardrail, check · 4:45–5:20 · [MORAL] [GUARDRAIL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So how did three careful copies disagree forever? A later change took a faster line, and got thrown away. Carry
what each change had seen, not what time it was. One limit: holding works because the update had seen the insert.
Two writes that never saw each other are a harder problem, and that's next. One quick check. An update says: needs
Frankfurt's change 2. Asia has applied only change 1. What does Asia do? Pause and think.

(three seconds)

It holds the update, until Frankfurt's change 2 arrives.

SCREEN: Captions "carry what you'd seen, not what time it was"; "two writes that never saw each other: next".
For the check, a chip "needs eu: 2" at ap, ap "applied eu: 1"; countdown; the chip moves to "held".

---

### Beat check

- QUESTION (scene 1). FAMILIAR + ANALOGY + MAP (scene 2). SHOW + NAME for topologies (scene 3).
- SHRINK, PREDICT + PAUSE, SHOW, BREAK (scene 4). The steelmanned fix broken (scene 5). The fix in the analogy, then
  NAME (scene 6). MORAL, GUARDRAIL, check (scene 7). Light moments: "change that order to blue" (3:15), "a very
  confident witness" (3:55).

### Accuracy notes for the producer

- Delays and times are the lesson's stepper and `OvertakeDemo.kt` output; the update also goes us→eu (40 ms),
  reaching eu at 85.
- pgactive's documented default (discard an UPDATE for a missing row) is the lesson's claim; the video doesn't quote
  the documentation's wording.
- The video's version vector is the single entry the lesson shows ({eu=1}); lesson 8 builds the full record.
- PostgreSQL's `origin = none` subscription option is left to the lesson.
- The lab's other case, the clock 60 ms ahead, where timestamps happen to give the right answer, is left to the lab.
