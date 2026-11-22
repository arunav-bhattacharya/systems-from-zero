# One copy, one timeline: what linearizable demands

- Slug / scene: `linearizability`, `videos/scenes/linearizability.py:Linearizability`
- Lesson: `cons-02`, section 0, "One copy, one instant: what linearizable demands"
- Audience / level: a complete newcomer. Has had a notification that opened an out-of-date screen; knows nothing
  about registers, histories or Herlihy and Wing.
- Length: about 5:00 (~800 words of narration, two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=160`: the four bars with instants at 10, 18 and 25, the email bar red, and the replay row above
- The learner's real question: "behave like one copy" sounds obvious. What exactly does it demand of a read?
- Misconception to steelman and break: "the fraud checker and the email program are on different computers; if they
  never talk, nobody can notice a stale read". Broken by the second channel: "captured!" sent from one to the other,
  which is the café owner's notification and her empty list.
- Concept chain: a notification beats a list → one board flips at one instant and never back → four bars on one
  register → pick one instant per bar, replay on one copy → the email read can't be placed → real time matters
  because of second channels → linearization, linearization point, Herlihy and Wing → what "seems" allows, locality
- Analogy family: a station departure board. One board (one copy); the line flips from on time to boarding at one
  instant (the write's point); a glance is a read; a friend texting "we're boarding!" is the second channel.
- Open loops: "what does one copy demand?" planted in scene 1 → answered by the rule in scene 4 and the moral.
- Assumptions: all times and answers are the lesson's stepper (capture 0–60 ms, ledger 5–15 reads -, fraud 20–30
  reads 2, email 40–50 reads -; points 10, 18, 25, 45). The station, train and time on the board are made up. The
  check (email 22–32 reading -, points 23, 24, 26) is a made-up history, worked out by hand against the rule.

## The one picture

Four lanes (capture, ledger, fraud checker, email) over a 0–60 ms axis. Capture's write is a gold bar across the
whole range; reads are blue bars. Chosen instants are yellow ticks with their time. Above: "one copy, in order:" a
row of replay chips. Captions at the bottom.

## Scene 1 · The café owner · 0:00–0:40 · [QUESTION] [LOOP-PLANT]

VO: A café owner's phone buzzes: payment received, 30.00. She opens the payments app to look at it, and the payment
isn't in the list. She pulls down to refresh, and there it is. The message was sent after the payment was saved. The
list read a copy that hadn't caught up yet. It's easy to shrug. A second later, everything agreed. But if the app had
used that list to decide whether the payment could be refunded, a second is plenty of time to decide wrong. The usual
cure is to make the copies behave like one. So what exactly does one copy demand?

## Scene 2 · The departure board · 0:40–1:20 · [FAMILIAR] [ANALOGY] [MAP]

VO: Picture the departure board at a station. One board. At some instant, your train's line flips from on time to
boarding. Anyone who looks before the flip sees on time. Anyone after, boarding. If you glance up right while it
changes, you get one or the other, never half. And once anybody has seen boarding, nobody who looks later can see on
time. A board doesn't flip back. Map it. The board is one copy. The flip is the instant a write takes effect. And
each glance is a read.

## Scene 3 · Four programs, one value · 1:20–2:05 · [SHRINK] [NAME: register]

VO: Now four programs and one value... 1 means authorized... 2 means captured... The capture program writes status 2,
and the write takes 60 milliseconds from request to answer. A value you can read and write like this is called a
register. Meanwhile, three programs read the status... Each bar runs from when the request is sent to when the answer
comes back.

## Scene 4 · Pick the instants · 2:05–3:10 · [SHOW] [PREDICT] [PAUSE] [BREAK]

VO: Here's the board's rule, written for bars. Pick one instant inside each bar... replay those instants, in order,
on one plain copy. Every answer has to match. The ledger, from 5 to 15, got the old status... put its instant at 10.
The fraud checker, from 20 to 30, got 2... Put the write at 18, and the fraud check at 25. The capture program hasn't
heard back yet. That doesn't matter. Now the email program, from 40 to 50, got the old status. Can we place its
instant? Pause and guess. (three seconds) No... This history isn't linearizable. Once any read has returned the new
value, every read that starts later must return it too.

## Scene 5 · The second channel · 3:10–3:50 · [BREAK] [JOKE:pivot] [LOOP-PAYOFF]

VO: You might be thinking: ... if they never talk, who would ever notice? Any second channel notices. The fraud
checker announces: captured. The email program reacts, and reads the old status. That's the café owner's buzz, and
her empty list. It's a friend texting: we're boarding! while the board in front of you still says on time. One of you
is about to miss a train. So the order that matters is real time, because any message between programs can expose it.

## Scene 6 · The good history, and the names · 3:50–4:25 · [SHOW] [NAME]

VO: Had the email program read 2, the instants would be: 10, 18, 25, and 45... every answer matches. That order is
called a linearization, and each chosen instant is a linearization point... Maurice Herlihy and Jeannette Wing gave
this exact rule in 1990.

## Scene 7 · Guardrails · 4:25–5:05 · [GUARDRAIL]

VO: The instant is a thought experiment. The store never reports it... Inside, a store may hold writes back, copy
them, retry them. What it may not do is let any client see something one copy couldn't have produced. The rule works
value by value, so a checker can take each value on its own. And sending each write to every copy, sooner or later,
doesn't give you this rule.

## Scene 8 · Moral and check · 5:05–5:40 · [MORAL] [PREDICT] [PAUSE]

VO: So: one copy, one timeline... Suppose the email's read had run from 22 to 32, overlapping the fraud check, and
returned the old status. Allowed? (three seconds) Yes. Put the email at 23, the write at 24, and the fraud check at
26. A read that overlaps the change may see either side.

---

### Beat check

QUESTION (1) → FAMILIAR + ANALOGY + MAP (2) → SHRINK (3) → SHOW, PREDICT + PAUSE, BREAK (4) → the skeptic's BREAK
and the loop paid off (5) → NAME after the show (6) → GUARDRAIL (7) → MORAL + check (8). Light moment: the friend
texting "we're boarding!" (5).

### Accuracy notes for the producer

- The lab's checker (7 and 6 search steps, longest prefix) is left to the next section.
- The lesson's locality example (two keys in Consistency models' lab) is summarised as "value by value".
- "Sending each write to every copy, sooner or later, doesn't give you this rule" is the lesson's sentence; the
  quorum case is left to the third section.
