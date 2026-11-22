# Count, don't read the clock: Lamport timestamps

- Slug / scene: `logical-clocks`, `videos/scenes/logical_clocks.py:LogicalClocks`
- Lesson: `dist-06`, section 1, "Lamport timestamps: count events, and jump past every message"
- Audience / level: a complete newcomer. Has used a group chat; knows nothing about nodes, clock skew or NTP.
- Length: 5:35 (~820 words of narration, two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=236` (all three lanes stamped, both messages, the sorted list of eleven stamps)
- The learner's real question: if no two clocks agree, how do you put events in the order they could really have
  happened?
- Misconceptions to steelman and break: (1) "fix it with better clocks", broken by a 40 ms gap against a 5 ms trip;
  (2) "a smaller stamp means it happened first, or caused it", broken by (2,0) < (3,2) with no path between them.
- Concept chain: phone clocks flip a chat → the same skew flips a payment → we need causes before effects, and a
  cause travels only along a node or a message → tallies that jump past each message → Lamport's rule on three
  nodes → one total list → the rule runs one way only (hardest last)
- Analogy family: the lesson's group chat. Ana and Ben stop reading phone clocks and keep a tally on a notepad.
- Open loops: "how do you order events?" planted in scene 1 → answered in scene 9 ("an answer can never sort above
  its question"); "smaller means first?" raised in scene 7 and broken there.
- Assumptions: chat times 7:30 and 7:29 are illustrative (the lesson says only "a minute slow"). Payment numbers
  (10:00:00.100, 40 ms ahead, 5 ms later, stamps .140 and .105, 35 ms) and every stamp on the three lanes are the
  lesson's stepper. The check (counter 9, message carries 4) is a made-up question.

## The one picture

Three horizontal lanes (top blue, middle green, bottom purple), labelled first "Ana's phone" / "Ben's phone", then
"auth" / "capture", then "Ana" / "Ben", then "auth (0)" / "capture (1)" / "ledger (2)". Events are circles on the
lanes with their stamp inside; gold arrows are messages, labelled with what they carry. A counter box ("tally",
then "counter") at the right end of each lane. A screen box under the lanes shows a sorted chat or sorted stamps;
later the sorted list of eleven stamps sits there. Captions at the bottom.

## Scene 1 · The chat · 0:00–0:35 · [QUESTION] [LOOP-PLANT]

VO: Picture a group chat that sorts messages by the time on the phone that sent each one. Ana asks: dinner at
eight? Ben answers: yes, see you there! But on the screen, the answer sits above the question. Ben's phone runs a
minute slow, so his answer got an earlier time than her question. So here's the real question. If no two clocks
agree, how do you put things in the order they could really have happened?

SCREEN: Two lanes; the question dot (7:30), an arrow to Ben, his answer dot (7:29 in red). The chat screen lists
the answer first.

## Scene 2 · The same bug, with money · 0:35–1:35 · [FAMILIAR] [PAIN] [BREAK] [WISH]

VO: In a chat, that's a funny moment. With money, it's a bug. Take a card payment in two steps, on two computers.
We'll call each computer a node. Auth approves a payment and sends a message to capture, which moves the money 5
milliseconds later. Auth's clock runs 40 milliseconds ahead. So the approval is stamped a hundred and forty
milliseconds past ten, and the capture a hundred and five. Sort by those stamps, and the money moves 35
milliseconds before the payment was even approved. The obvious fix is better clocks. But NTP, the service that
keeps computer clocks close to the right time, can easily leave 40 milliseconds between two servers. And a message
often takes less than that. Whenever the gap between two clocks is bigger than the trip, sorting by time can flip a
cause and its effect. Wouldn't it be nice to have an order that stays right, whatever the clocks say?

SCREEN: Lanes relabelled auth and capture; approve pay-81723, the message, the capture; gold stamps
10:00:00.140 and 10:00:00.105; "sorted by stamp" puts the capture first in red. Captions "clock gap 40 ms > message
trip 5 ms", then the wish.

## Scene 3 · What we need · 1:35–2:05 · [SHRINK]

VO: So what order do we actually need? Not the time of day. Causes before their effects. And a cause can reach an
effect in only two ways. Along one node's own events, one after another. Or along a message, from the send to its
arrival. So if a stamp only ever grows along both, an effect can never get a smaller stamp than its cause.

SCREEN: A yellow segment along capture's lane, then the message arrow turns yellow.

## Scene 4 · The tallies · 2:05–3:05 · [ANALOGY] [MAP] [JOKE:reward]

VO: People can do this with no clock at all. Back to the chat. Ana and Ben stop trusting their phones, and each
keeps a tally instead, a number on a notepad. Before Ana sends anything, she adds one to her tally, and writes it
on the message. Her question carries 1. When Ben reads a message, he takes the bigger of his tally and the
message's, and adds one. His tally was 0, the message says 1, so the read becomes 2. Then his answer carries 3.
Sort by tally: question 1, answer 3. The right order, and nobody read a clock. Ben's phone can stay a minute slow
forever. Nobody asks it any more. Let's map it. Each friend is a node. The tally is a counter. The number on the
message is the stamp it carries. And the bigger of the two, plus one, is the jump past the message.

SCREEN: Tally boxes at the lane ends; question 1, arrow "carries 1", read 2, answer 3; chat sorted by tally (green).
Mapping captions one by one.

## Scene 5 · Three nodes · 3:05–4:00 · [SHRINK] [PREDICT] [PAUSE] [SHOW]

VO: Now three nodes. Auth approves payments, capture moves the money, and the ledger keeps the balances. Each counts
its own events, starting at 1. Auth approves, and gets 1. Capture is at 1, and the ledger counts 1, 2, 3. Auth counts
the send as 2, and the message carries 2. Capture's counter says 1. What does capture's receive get? Pause and guess.
(three seconds) 3. The bigger of 1 and 2 is 2, plus one. Capture sends to the ledger, with 4. But the ledger has
counted to 5 on its own. So the receive becomes the bigger of 5 and 4, plus one: 6. A receive always ends up above
the send that caused it. That's the whole guarantee.

SCREEN: The lesson's stepper, built event by event, counters ticking; a yellow "?" on capture's receive during the
countdown.

## Scene 6 · The name, one list · 4:00–4:35 · [NAME]

VO: This is called a Lamport timestamp, after Leslie Lamport, who described it in 1978. And could have caused has a
name too: happens before. A stamp is the counter plus the node's own number... Sort all eleven stamps, and every
event gets one place in one list. Every cause sits before its effect.

SCREEN: (1,0) (1,1) (1,2) (2,0) (2,2) (3,1) (3,2) (4,1) (4,2) (5,2) (6,2), coloured by node.

## Scene 7 · Smaller means first? · 4:35–5:10 · [BREAK]

VO: So, does a smaller stamp mean it happened first? ... Auth's send has 2. The ledger's third event has 3. But the
only path from auth reaches the ledger at 6, long after its 3. They're concurrent... A smaller stamp doesn't mean a
caused b, or even that it came first. Telling those apart takes vector clocks: one counter per node, in every stamp.

SCREEN: Rings on (2,0) and (3,2); the path auth 2 → capture 3 → 4 → ledger 6 drawn in yellow; vectors [2,0,0] and
[0,0,3].

## Scene 8 · Limits · 5:10–5:40 · [GUARDRAIL] [JOKE:is-the-explanation]

VO: A counter has no idea what time it is. It's great at after, and hopeless at when. Ask it for everything after
ten o'clock, and it just stares at you. A quiet node's counter can drift thousands away from a busy one's. Use these
stamps for causes before effects; for the time of day, the clock comes back in, carefully, next.

## Scene 9 · Moral and check · 5:40–6:05 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: Count events instead of reading clocks, and jump past every message you receive. Then an answer can never sort
above its question. One quick check: capture's counter is at 9, and a message arrives carrying 4. (three seconds)
10. Not 5. The jump only ever goes up.

---

### Beat check

QUESTION (1) → FAMILIAR/PAIN/BREAK of "better clocks"/WISH (2) → SHRINK (3) → ANALOGY+MAP (4) → PREDICT+PAUSE+SHOW
(5) → NAME (6, after the show) → BREAK of "smaller means first" (7) → GUARDRAIL (8) → MORAL + check (9). Light
moments: the slow phone nobody asks (4), the counter that stares at you (8).

### Accuracy notes for the producer

- All lane stamps, the two messages and the sorted list are the lesson's stepper frames. The vectors [2,0,0] and
  [0,0,3] are its fourth frame.
- "NTP can easily leave 40 ms" paraphrases the lesson's "well within what NTP can leave between two servers".
- The tally analogy is the lesson's chat; the lesson itself doesn't number the chat. Chat times are illustrative.
- Left to the lesson: hybrid logical clocks, ids that sort by their maker's clock, and what concurrent events
  ordered against real time cost (its last section).
