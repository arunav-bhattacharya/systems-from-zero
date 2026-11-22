# Wait somewhere else: retry topics for a bank that's down

- Slug / scene: `retry-topics`, `videos/scenes/retry_topics.py:RetryTopics`
- Lesson: `msg-09`, section 2, "Long waits belong in retry topics, not in the poll loop"
- Audience / level: a complete newcomer. Can read a little code; doesn't know Kafka, partitions, offsets, consumer
  groups or what a retry topic is.
- Length: 5:44 (~950 words of narration at Kokoro's ~175 words a minute, plus two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=246` (the staircase complete: both retry rails, the stair arrows, the tray, the bank back)
- The learner's real question: the card's bank is down for three minutes. What should the ledger do with the payment
  in front of it: keep trying, throw it away, or something else?
- Misconceptions to steelman and break: (1) "retry harder": quick waits flood the tray with 5,400 good payments, long
  waits hold the rail for 3 of the 5 minutes allowed between polls; (2) "skip it and come back later": the bookmark is
  one number, so moving it past pay-5 says pay-5 is done.
- Concept chain: a rail read in order with one bookmark → permanent goes to the tray, transient gets a quick retry →
  an outage beats both → a second rail with a time on each slip (a retry topic) → a retry reader that pauses and keeps
  polling → a staircase of waits, then the DLT → one wait per topic, and the cost: the record has left its rail (hardest last)
- Analogy family: the lesson's kitchen. The rail of order slips (a partition), the cook (the ledger), the smudged slip on
  the problem tray (a permanent failure, the DLT), the oven that isn't hot yet (a transient failure), and the second rail
  where a slip waits with a time on it (a retry topic).
- Open loops: "what should the ledger do with the one in front of it?" planted in scene 1 → answered in scene 10; the
  account out of order planted in scene 8 → handed to the lesson's next section (park the key).
- Assumptions: numbers are the lesson's (30 payments a second, a 3-minute outage, 100/200/400 ms, 5,400 on the tray,
  30-second waits and 6 tries, 5 minutes between polls, `payments.retry-10s`, `payments.retry-1m`, `payments.DLT`).
  The slips pay-0 to pay-10, the "due 0:10" times and "acct-1" are made up for the picture.

## The one picture

Top: the main rail (partition 0 of `payments`), eight slips pay-0 to pay-7, a gold bookmark under the next slip. Left:
the cook (the ledger) and below it the card's bank, joined by a call arrow. Middle and lower right: the second rail
(`payments.retry-10s`) and the third (`payments.retry-1m`), gold, with the retry reader's box at their left. Bottom:
the problem tray (`payments.DLT`), red, with a counter. Green = applied, gold = waiting, red = failed, purple = the
wrong idea or the out-of-order account. Captions on one line at the bottom.

## Scene 1 · The question · 0:00–0:35 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: Picture the payments app on an ordinary day. Payments arrive in a line, and a program called the ledger takes them
one at a time, in order, and keeps each account's balance. The line is kept by Kafka, a program that stores records in
order, for other programs to read. The ledger keeps a bookmark: how far it got. Now the card's bank, which has to say
yes to each payment, stops answering. For three minutes. Thirty payments arrive every second. What should the ledger
do with the one in front of it? Keep that question.

SCREEN: Title card. Eight slips fade in left to right ("payments, in the order they arrived"); the ledger box; pay-0
and pay-1 turn green; the bookmark under pay-2. The bank box grows with a call arrow, turns red ("down for 3 min");
"30 payments a second"; a "?" by pay-2.

## Scene 2 · The kitchen · 0:35–1:25 · [ANALOGY] [MAP] [NAME]

VO: Let's step into a kitchen for a minute. Order slips hang on a rail, and the cook takes them in order. A smudged
slip that nobody can read goes onto a problem tray, with a note, and the cook moves on. That's a permanent failure:
trying again won't help. In the app, it's pay-3, whose amount came in as 12x50. But if the oven isn't hot yet, the slip
is fine. Wait a moment and try again. That's a transient failure. The ledger does the same with a slow bank: wait 100
milliseconds, then 200, then 400. So the rail is one partition of the payments log, the cook is the ledger, and the tray
is a separate log for records it gave up on, a dead-letter topic, called payments.DLT.

SCREEN: A rail line and pins appear over the slips; "the cook". pay-3 turns red, a copy drops onto the red tray, the
bookmark moves on; "12x50" under it. pay-4 glows blue; three tries ("try 1: no answer", "wait 100 ms, try 2...",
"wait 200 ms, try 3: yes"); pay-4 turns green. The labels change as each mapping is said: "the rail = partition 0 of
payments", "the ledger", "payments.DLT".

## Scene 3 · The outage, predicted · 1:25–2:05 · [PAIN] [PREDICT] [PAUSE] [SHOW] [JOKE:release]

VO: Now back to the bank, down for three minutes. Waits of 100, 200 and 400 milliseconds give up in under a second.
So pay-5 goes onto the tray. And so does the next one. Thirty a second, for three minutes. How many good payments end
up on the tray? Pause and guess.

(three seconds)

Five thousand four hundred. Thirty times a hundred and eighty seconds, every one a good payment, waiting for a person
to send it back by hand. That's not a problem tray any more. That's a problem room. So quick retries are for a hiccup,
not for an outage.

SCREEN: pay-5 and pay-6 go red and onto the tray; the counter reads 3; countdown bar. The counter runs to 5,400 with
"30 a second x 180 seconds = 5,400". The tray stretches on "problem room".

NOTE: The joke comes right after the number, and is cashed back at once ("for a hiccup, not for an outage").

## Scene 4 · Wait longer? · 2:05–2:40 · [BREAK] [WISH]

VO: Fine, then wait longer. Thirty seconds between tries, up to six tries. That gives the bank time to come back. But
now the cook stands at the oven with pay-5 for three minutes, and every slip behind it waits. And Kafka gives a reader
five minutes between two requests for more. After that, it treats the reader as gone. Short waits flood the tray. Long
waits hold up the rail. Well... neither is the kitchen we wanted. What we want is for pay-5 to wait somewhere else,
while the rail keeps moving.

SCREEN: pay-5 and pay-6 come back to the rail; pay-5 gold, "pay-5: try 1 of 6" ... "try 6 of 6"; pay-6 and pay-7 pulse;
a gauge fills to 3 of 5 minutes; the cook's box pulses red. Caption: the wish.

## Scene 5 · Skip it and come back? · 2:40–2:55 · [BREAK]

VO: Can't the ledger skip pay-5 and come back to it later? A queue program can hold one message back like that. But
Kafka's bookmark is a single number. Move it past pay-5, and you've told Kafka that pay-5 is done.

SCREEN: Purple caption "skip it, and come back later?"; the bookmark reads 5, then 6; a red cross over pay-5;
"bookmark at 6 means: everything before 6 is done".

## Scene 6 · The second rail · 2:55–3:30 · [ANALOGY] [SHOW] [NAME]

VO: A good kitchen has a second rail, for slips that wait on something. The cook pins the slip there with a time on it,
and carries on with the main rail. In Kafka, the second rail is another topic, a separate log, called
payments.retry-10s. The ledger writes pay-5 there, waits for Kafka to confirm it, moves its bookmark past it, and
carries on at full speed. Every record carries the time it was written. So a reader knows pay-5 is due ten seconds
after that, and the one behind it a little later.

SCREEN: A gold rail draws in the middle ("second rail", then `payments.retry-10s`); pay-5 is copied to it and fades on
the main rail; "due in 10 s"; the bookmark moves on; pay-6 follows; "due 0:10", "due 0:11".

## Scene 7 · The retry reader · 3:30–4:20 · [SHOW] [BREAK] [NAME]

VO: A second reader, in a group of its own, reads the retry topic. Its first record isn't due yet. Does it sleep? No. A
long sleep breaks the same five-minute rule. Instead, it pauses that partition, and keeps asking Kafka for more. A
paused partition hands back nothing, but asking keeps the reader in its group. At ten seconds, it resumes, goes back to
pay-5, and calls the bank again. Still down? Then pay-5 moves one step down, to a topic with a longer wait,
payments.retry-1m. The last step is the tray. Steps with growing waits, one under the other, like a staircase. These
are called retry topics. When the bank comes back, the main rail carries on at once. The records on the steps go
through on their next try. Only what still fails at the last step reaches the tray.

SCREEN: The retry reader's box; "paused, still asking" pulses while the rail dims; "resumed: pay-5"; pay-5 red; a third
rail (`payments.retry-1m`) and pay-5 on it; two stair arrows down to the tray. The bank turns blue; pay-7 on the main
rail goes green at once, then pay-6 and pay-5 on the steps.

## Scene 8 · The guardrails · 4:20–5:05 · [GUARDRAIL] [LOOP-PLANT]

VO: One rule keeps the retry reader simple: each topic has one wait. Every record on the ten-second rail waits the same
ten seconds, so they come due in the order they were written. The reader only ever watches the first one. And one
cost. Notice what just happened. pay-7 went through first, while pay-5 was still waiting on a step. Say they belong to
the same account. Its payments are now out of order. For a receipt email, that does no harm. For a payment and its
refund, it does. Keeping an account in order is the next part of the lesson.

SCREEN: "one wait per topic"; "acct-1" appears on pay-7 and pay-5; "one account: pay-7 applied before pay-5"; the
receipt/refund caption.

## Scene 9 · The code · 5:05–5:30 · [SHOW]

VO: Here's the heart of it, in Java and in Kotlin. The ledger sends the payment to the retry topic, waits for the
answer, and only then commits its bookmark. The retry reader adds ten seconds to the record's time. Not due yet: pause,
and keep polling. Due: resume, and seek back to the record.

SCREEN: The diagram dims; two panels, Java left, Kotlin right, the same lines: `retry.send(...).get()`,
`consumer.commitSync(nextOffsets(records))`, and the retry reader's `pause` / `resume` + `seek`. Lines light as read.

## Scene 10 · The moral, and a check · 5:30–6:10 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, what should the ledger do with the payment in front of it while the bank is down? Not stand at the oven, and
not throw it on the tray. Pin it to a second rail with a time, and keep the main rail moving. Quick retries for a
hiccup. Retry topics for an outage. The tray for what's really broken. One quick check. Someone puts a ten-minute
record and a ten-second record on the same retry topic, the ten-minute one first. When does the ten-second one get its
try? Pause and think.

(three seconds)

After ten minutes. The reader only watches the first record, so the short wait is stuck behind the long one. That's why
each wait gets its own topic.

SCREEN: The diagram returns; the cook, tray and rails glow in turn. For the check, two slips on the second rail ("waits
10 min" in red, then "waits 10 s"); countdown; "one wait per topic" stays on the last frame.

---

### Beat check

- QUESTION (scene 1) from a felt situation (the bank is down; what now?).
- ANALOGY + MAP (scene 2): the kitchen, mapped out loud (rail = partition, cook = ledger, tray = DLT).
- PREDICT with PAUSE: 5,400 on the tray (scene 3) and the check (scene 10).
- BREAK: quick retries (scene 3), long waits (scene 4), skip-and-come-back (scene 5).
- NAME after the picture: dead-letter topic (scene 2), retry topics (scene 7, after the rails are built).
- GUARDRAIL: one wait per topic, the out-of-order cost (scene 8). MORAL and RECAP last (scene 10).
- Light moments: "a problem room" (scene 3), "neither is the kitchen we wanted" (scene 4).

### Accuracy notes for the producer

- "Five minutes between two requests for more" is `max.poll.interval.ms` (default 5 minutes); past it, the member
  leaves its group and its partitions go to another member. The lesson's "3 of the 5 minutes" is for 6 waits of 30 s.
- The retry reader's `pause` keeps `poll` returning nothing for that partition while the member stays in its group;
  on `resume` it seeks back to the record. The code on screen is a sketch of that check, using the real
  `KafkaConsumer.pause`, `resume`, `seek` and `ConsumerRecord.timestamp()` calls; `nextOffsets` is the lesson's helper.
- The video doesn't say how many steps a staircase needs for a 3-minute outage; it shows pay-5 failing at 10 s and
  going on to the 1-minute step, and the bank coming back before its next try. The step count is a design choice.
- The "a queue program can hold one message back" line is the lesson's RabbitMQ 4.4 delayed delivery, left unnamed.
- "One wait per topic" and the 10-minute-ahead-of-10-second check come from the lesson's deeper notes.
- The lesson's aside on Spring's `@RetryableTopic` was cut for length. The ordering cost (park the key) is the lesson's next section.
- The slip names, the due times and "acct-1" are made up for the picture.
