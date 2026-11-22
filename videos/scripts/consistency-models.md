# What may a read return? A ladder of promises

- Slug / scene: `consistency-models`, `videos/scenes/consistency_models.py:ConsistencyModels`
- Lesson: `cons-01`, section 1, "Down the ladder: six models, each one looser"
- Audience / level: a complete newcomer. Has used a banking app; knows nothing about replicas or histories.
- Length: about 5:00 (~860 words of narration, two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=162`: history 3 (opposite orders) with linearizable and sequential red, the rest green
- The learner's real question: with three copies, what is a read allowed to return? Was the sister's 100.00 a bug?
- Misconception to steelman and break: "copies should always agree, so a stale read is a bug". Broken by walking
  down the ladder: each history breaks exactly one more rung, eventual holds throughout, and the closing check shows
  the sister's 100.00 broke only the top rung.
- Concept chain: one computer returns the last write → three copies make "last" depend on which and when → a
  history of bars → the ladder, each rung dropping one demand → six histories, each breaking one more rung → the name
  → the cost (availability during a split) → pick the loosest rung
- Analogy family: three noticeboards in three rooms; somebody walks each new balance to the other boards; a read is
  a glance at the board in your room. The rungs are house rules for what a glance may show.
- Open loops: "was that 100.00 a bug?" planted in scene 1 → answered by the check in scene 10.
- Assumptions: 30.00, 70.00 and 100.00 are the lesson's opening. The six histories and their pass/fail rungs are the
  lesson's stepper frames (read from its SVGs); bar times are drawn to match the frames' shapes. The sister's history
  in the check (w b=70; r b:100; r b:70) restates the opening, and the lesson's closing gives its verdict.

## The one picture

Left: the ladder, rails and five rungs (linearizable, sequential, causal, read your writes | monotonic reads,
eventual), "stronger" above. Each rung turns green (passes) or red (breaks) for the history on the right. Right: a
history: one line per program, gold bars for writes, blue for reads, a title above. Captions at the bottom.

## Scene 1 · The shared card · 0:00–0:35 · [QUESTION] [LOOP-PLANT]

VO: You share a card with your sister. You pay 30.00 for coffee, and your app shows 70.00 left. A moment later, her
app shows 100.00, as if you'd never paid. She refreshes: 70.00. Nothing is broken. The company keeps each balance on
three computers, so losing one loses nothing. Your payment reached one copy first, and her phone asked a copy that
hadn't heard yet. So here's the real question. With three copies, what is a read allowed to return? Was that 100.00
a bug?

## Scene 2 · One computer, then three noticeboards · 0:35–1:20 · [FAMILIAR] [ANALOGY] [MAP]

VO: On one computer the answer is easy. A read returns the last value written, like a variable in a program. With
three copies, the last value depends on which copy you ask, and when. Picture three noticeboards in three rooms of a
house. You write the new balance on the nearest board, and somebody carries it to the other two, sooner or later. A
read is a glance at the board in the room you're in. The boards are the copies, the walk between rooms is the delay,
and the glance is a read. What we need is a set of house rules. What may a glance show?

## Scene 3 · A history, and the ladder · 1:20–1:55 · [SHRINK] [SHOW]

VO: To check a rule, we draw a history... Checkout writes the balance, 70. The ledger, starting later, reads 70. The
house rules form a ladder. Each rung down drops one demand, so a history that passes a rung passes every rung below
it. This history passes every rung. One copy could have done exactly this.

## Scene 4 · Linearizable, broken by a stale read · 1:55–2:30 · [PREDICT] [PAUSE] [SHOW]

VO: The top rung is linearizable... a read that starts after a write has finished must see it. Now the ledger starts
after the write has finished, and still reads the old value. The dash means the value before the write. Which rungs
survive? Pause and guess. (three seconds) Only the top one breaks...

## Scene 5 · Sequential, broken by opposite orders · 2:30–3:05 · [NAME] [BREAK]

VO: That's sequential consistency, which Leslie Lamport defined in 1979... Two copies, one in Europe and one in the
United States, accept two writes to a payment's status at the same moment: 2 for captured, and 3 for refunded. The
ledger sees 2, then 3. The fraud checker sees 3, then 2. No single order explains both.

## Scene 6 · Causal, broken by an answer before its question · 3:05–3:40 · [BREAK] [JOKE:release]

VO: Causal consistency drops the single order... never an effect before its cause. A support agent asks a shop a
question. The shop reads it and answers. An auditor reads the answer, then finds no question... It's a reply that
says yes, see you there, with no invitation anywhere.

## Scene 7 · The session promises · 3:40–4:15 · [BREAK]

VO: Read your writes... Checkout writes 70, and its very next read gets the old value. Monotonic reads... The ledger
reads 70, then the old value from a copy further behind. Its balance went back in time.

## Scene 8 · Eventual · 4:15–4:35 · [SHOW] [JOKE:is-the-explanation]

VO: If the writes stop, all copies end up the same... No history that stops can break a promise with no deadline.
It's the friend who'll pay you back eventually: never technically wrong.

## Scene 9 · The name, the cost, the moral · 4:35–5:15 · [NAME] [GUARDRAIL] [MORAL]

VO: Each rung has a name: a consistency model... Each rung up costs availability... When the network splits the
copies, no model at sequential or above lets every copy keep answering. Some must refuse. Causal and the session
promises can keep working, if a client keeps talking to the same copy. A stronger model is a promise someone pays
for. Pick the loosest rung your data can live with.

## Scene 10 · Check · 5:15–5:40 · [PREDICT] [PAUSE] [LOOP-PAYOFF]

VO: Your sister read 100.00 after you had already paid, then 70.00. Which rungs did that break? (three seconds) Only
the top one. She didn't write anything, her balance never went back, and one order explains it all. Nothing was
broken: the store just promised less than one copy.

---

### Beat check

QUESTION (1) → FAMILIAR + ANALOGY + MAP (2) → SHRINK (3) → PREDICT + PAUSE (4) → NAME and BREAK for each rung (4–8)
→ NAME of the family (9) → GUARDRAIL (9) → MORAL (9) → check (10). Light moments: the reply with no invitation (6),
the friend who'll pay you back eventually (8).

### Accuracy notes for the producer

- The session rung is drawn as two halves because read your writes and monotonic reads are siblings, not one under
  the other (frame 6 breaks monotonic reads but keeps read your writes). Monotonic writes and writes follow reads
  are left to the lesson.
- "Sticky available" is said as "keep working, if a client keeps talking to the same copy".
- Jepsen's map is the lesson's source for the availability line; the video doesn't name Jepsen.
