# When can the slip go in the bin? Acks, redelivery, and the order of the work

- Slug / scene: `queue-redelivery`, `videos/scenes/queue_redelivery.py:QueueRedelivery`
- Lesson: `msg-01`, section 2, "A message leaves only when it's acknowledged, and redelivery changes the order"
- Audience / level: a complete newcomer. Has paid by card in a café; knows nothing about brokers, queues,
  RabbitMQ or delivery guarantees.
- Length: 5:26 (~840 words of narration at Kokoro's ~175 words a minute, plus three pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=233.5` (the ledger's order m1 m2 m4 m3 m5, the capture in red, B crashed: the key picture)
- The learner's real question: a program is handed a message and crashes halfway. Is the message gone? And if a
  queue is first in, first out, how can the work come out in the wrong order?
- Misconception to steelman and break: (1) "delete a message once it's sent", broken by a crash that loses m1
  (auto-ack, at-most-once); (2) "a FIFO queue keeps the order of the work", broken by the five-message run where the
  ledger books m4 before m3.
- Concept chain: the slip stays until the dish goes out → ack, unacked, redelivery → a crash after the work and
  before the ack repeats it (at-least-once) → two competing consumers plus redelivery invert the order → FIFO only
  where the queue hands messages out (hardest last)
- Analogy family: the lesson's café rail. Slips on a rail above the kitchen hatch, a slip clipped above the cook's
  station until the dish goes out, a cook who walks out, the next free cook.
- Open loops: "what if she walks out halfway?" planted in scene 1 → scene 2 (the slip goes back) and scene 6 (the
  crash before the ack); "first in, first out, so the order is safe. Right?" planted in scene 7 → broken in scene 7,
  named in scene 8; the receipt email twice (the lesson's closing) → scene 11.
- Assumptions: all numbers are the lesson's stepper (five messages for account 17: m1 auth 40, m2 capture 40, m3 auth
  25, m4 capture 25, m5 refund 10; two consumers, prefetch 1, manual acks; B crashes holding m3). The one-consumer
  scenes (auto-ack losing m1, m2 booked twice) are small demos built from the section's prose with the same messages.

## The one picture

Top left: the queue (grey box, "front" at its right end), five message boxes coloured by kind (auth blue, capture
green, refund gold), a status under a message when it's unacked or back. Right: consumer A (teal) and, from scene 7,
consumer B (purple), each with a status line; a message a consumer holds sits just left of it. Bottom: the ledger's
row, "the ledger books, in this order:". Captions sit between the consumers and the ledger. Green chips are acks;
red is lost, crashed or wrong; gold is redelivered.

## Scene 1 · The rail · 0:00–0:20 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: Picture the rail above a café kitchen. The cashier clips each order slip to it, and the cooks take them from the
front. A cook takes a slip. When can it go in the bin? When she takes it, or when the dish goes out? And what if she
walks out halfway? Hold that thought.

SCREEN: Title card. The rail draws in, three slips slide onto it, a cook box appears. A slip moves to the cook's
station; a yellow "?"; the cook's outline pulses red on "walks out".

## Scene 2 · The kitchen's rule · 0:20–0:36 · [ANALOGY]

VO: The kitchen has a rule. The slip stays clipped above the cook's station until the dish goes out. Only then is it
thrown away. If the cook walks out halfway, her slip goes back on the rail, and the next free cook picks it up.

SCREEN: Caption "the slip stays above the station until the dish goes out"; the slip drops away ("dish out: slip in
the bin"). The next slip goes to the station, the cook turns red ("walked out"), the slip slides back onto the rail,
the cook returns and takes it, and it goes in the bin.

## Scene 3 · The map · 0:36–1:05 · [MAP]

VO: Programs pass messages the same way. A message is a small piece of data, such as: an account asks to pay 40
euros. A broker is a program in the middle that holds messages. Its queue is the rail. The program that sends is the
cashier, and each program that reads is a cook, called a consumer. We'll use RabbitMQ, a free broker program that
many companies run. Our consumer is the ledger, the program that keeps each account's balance.

SCREEN: The slips become five messages m1 to m5. Captions one at a time: "slip = message", "rail = queue, in a broker
that holds messages", "cashier = the program that sends", "cook = consumer". The rail's label becomes "queue, inside
the broker: account 17", the cook becomes "consumer A", and the ledger's row appears.

## Scene 4 · The tempting shortcut · 1:05–1:40 · [BREAK] [JOKE:amplify] [NAME]

VO: Now, the tempting shortcut: delete each message the moment the broker sends it. Watch the ledger take m1 and
crash halfway. The broker already deleted it. The payment is gone. That's a kitchen that bins each slip as soon as a
cook glances at it. Very tidy. Until the cook goes home with your lunch in her head. RabbitMQ calls this auto-ack,
and its own guide calls it unsafe. Nothing twice, and some never: that's at-most-once delivery.

SCREEN: m1 moves to A and its slot vanishes at once. A turns red ("crashed"); m1 fades under a red cross and drifts
away. Captions "auto-ack: deleted when sent. RabbitMQ's guide: unsafe", then "at-most-once: never twice, some never".

NOTE: The joke comes right after the failure and is cashed back by the name and the guide's verdict.

## Scene 5 · The ack · 1:40–2:25 · [SHOW] [NAME]

VO: Let's put m1 back, and do it the kitchen's way. The broker sends m1, and keeps it. Until the consumer is done, m1
is unacked: still in the queue, set aside for that consumer. The slip above the station. After it books the payment,
the consumer sends a short note: done, delete it. That note is an acknowledgement, or ack. If the connection closes
before the ack, the broker puts the message back and sends it again, flagged as redelivered. That's redelivery.

SCREEN: m1 returns. A copy goes to A while the slot dims with "unacked, A". The copy moves to the ledger; a green
"ack" chip flies back to the slot and the slot is deleted. Captions "unacked: sent, still in the queue, set aside",
"ack: the work is done, delete it", "no ack and the connection closes: back in the queue, flagged redelivered".

## Scene 6 · Predict: a crash after the work · 2:25–3:00 · [PREDICT] [PAUSE] [SHOW] [NAME]

VO: Here's a puzzle. The ledger books m2, adding it to the balance, and crashes just before its ack leaves. What
happens next? Pause and guess.

(three seconds)

The broker can't tell this crash from one before the work started. So m2 comes back, and the ledger books it a
second time. Nothing is lost, and some messages are handled twice: that's at-least-once delivery. The ledger must
spot the repeat itself, and the lesson's worked example shows how.

SCREEN: m2 goes to A and into the ledger; A turns red ("crashed before the ack"); countdown bar. m2's slot comes back
("redelivered", gold), A takes it again ("m2, redelivered") and books it: two m2 boxes in the ledger, both outlined
red. Caption "at-least-once: nothing lost, some twice".

## Scene 7 · Two consumers, five messages · 3:00–3:57 · [SHRINK] [PREDICT] [PAUSE] [SHOW] [BREAK] [JOKE:release]

VO: One ledger is slow. So we run two copies, A and B, on one queue, and the broker gives each message to only one.
They're called competing consumers. Five messages for account 17 wait in order. Each card payment takes two. When you
tap your card, the bank first sets the money aside: that's the auth. Later the money really moves to the shop: that's
the capture. The ledger must book each auth before its capture. And this is a queue: first in, first out. So the
order is safe. Right?

Each holds one message at a time. m1 goes to A, and m2 to B. Both book, and ack. So far so good. Next, B takes m3, the
auth of 25, and A takes m4, its capture. Now B crashes before its ack. The broker puts m3 back at its old place, the
front of the queue. In what order does the ledger book the rest? Pause and guess.

(three seconds)

Consumer A was still busy with m4. It finishes, and books the capture of 25, for money the ledger never saw set
aside. Then A gets m3, marked redelivered, and books it. Then m5. The ledger's order: m1, m2, m4, m3, m5. Well...
that's a capture before its auth.

SCREEN: The ledger row clears and all five messages are back; consumer B appears. Auths and captures pulse in their
colours with captions. Purple caption "first in, first out... so the order is safe?". The stepper plays: m1 to A, m2
to B, both booked and acked; m3 to B, m4 to A (both "unacked"); B red with a cross, m3 slides back ("back");
countdown. m4 lands in the ledger outlined red ("a capture before its auth"); m3 (redelivered) and m5 follow. The
five ledger boxes pulse, m4 and m3 in red.

## Scene 8 · Where the order really lives · 3:57–4:35 · [NAME] [PRINCIPLE] [BREAK of the analogy]

VO: Nothing was lost, and nothing was booked twice. The queue even kept its order: it handed out m3 before m4. The
work didn't, because two machines finish at their own pace. A queue is first in, first out, FIFO for short, only at
the moment it hands messages out. It can't make two consumers finish in order. Here the café picture stops working. A
broker writes each message to disk on several machines first. And it never knows if a dish was cooked, only whether
a cook said so.

SCREEN: B comes back. The queue glows green ("the queue handed out m3, then m4: in order"), the consumers pulse
("two machines finish at their own pace"), then "FIFO: in order where it hands messages out, and only there" and "a
FIFO queue can't make two consumers finish in order". Captions for the analogy's limit.

## Scene 9 · The code · 4:35–4:47 · [SHOW]

VO: Here's that consumer in Java and Kotlin. false turns auto-ack off, the middle books the payment, and basicAck
comes last.

SCREEN: The diagram dims. Java and Kotlin panels side by side (the lesson's consumer, with the delivery tag on its own
line); the `false`, `book(...)` and `basicAck` lines light up in turn.

## Scene 10 · The guardrail · 4:47–5:03 · [GUARDRAIL] [LOOP-PLANT]

VO: The fix for order, inside a broker, is one consumer per queue, which RabbitMQ calls single active consumer. You
keep the order, and give up sharing the work. The next two lessons show a log that keeps both.

SCREEN: Consumer B dims: "one consumer per queue: single active consumer", "order kept; one machine does all the
work". B returns: "next: a log keeps the order and shares the work".

## Scene 11 · Moral and check · 5:03–5:40 · [JOKE:reward] [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: Ever had the same receipt email twice? Now you know: somewhere, a consumer crashed before its ack. So: the slip
stays above the station until the dish goes out. A crash brings it back. And two cooks can finish in the wrong order.

One quick check. Turn auto-ack back on, and let B crash holding m3 again. What does the ledger book? Pause and think.

(three seconds)

m1, m2, m4, m5. m3 was deleted when it was sent, so it never comes back, and the capture of 25 has no auth at all.

SCREEN: Captions "the same receipt email, twice?", "a consumer crashed before its ack: at-least-once", then the
three-line recap. For the check, the ledger keeps m1 and m2, m3 to m5 return to the queue, both consumers say
"auto-ack"; m3 goes to B and m4 to A and their slots vanish at once; B crashes. Countdown. m4 (red) and m5 land in
the ledger, the m3 that B held fades, caption "auto-ack: m3 is lost, not late".

---

### Beat check

- Opens with QUESTION (scene 1) from a familiar picture (the café rail).
- ANALOGY (scene 2) and MAP said out loud, part by part (scene 3), before any product word.
- BREAK: auto-ack loses m1 (scene 4); "first in, first out, so the order is safe" broken by the stepper (scene 7);
  the analogy's limit (scene 8).
- PREDICT with PAUSE three times (scenes 6, 7 and 11), each followed by SHOW.
- NAME after the picture: auto-ack and at-most-once (scene 4), unacked, ack, redelivery (scene 5), at-least-once
  (scene 6), competing consumers (scene 7), FIFO (scene 8), single active consumer (scene 10).
- GUARDRAIL (scene 10) and MORAL (scene 11) come last. Light moments: the cook who goes home with your lunch in her
  head (1:22), "that's a capture before its auth" (3:52), the receipt email twice (5:03).

### Accuracy notes for the producer

- The five messages, two consumers with prefetch 1, manual acks, B's crash holding m3, m3 returning to the head and
  the ledger's order m1 m2 m4 m3 m5 are the lesson's stepper, step for step.
- The auto-ack demo (m1 lost) and the at-least-once demo (m2 booked twice by one consumer) are small illustrations of
  the section's prose ("a consumer that crashes loses every message it was holding"; "picture the ledger booking a
  payment and crashing before its ack leaves"), not lab output.
- The video shows a returned message flagged "redelivered". On a quorum queue the lesson's try-it also shows the
  `x-delivery-count` header; left to the lesson.
- "Its own guide calls it unsafe": RabbitMQ's consumer acknowledgements documentation, as the section cites.
- The check's answer (m1, m2, m4, m5, m3 lost) follows from the section's auto-ack rule; it isn't a lab run.
- Prefetch (how many unacked messages a consumer may hold) is the next section; the video only says "each holds one
  message at a time". The worked example's idempotency key is named only as "the ledger must spot the repeat".
- The code is the lesson's consumer without `basicQos`, with the delivery tag read into `tag` first so the lines fit;
  the calls are the same.
- Pronunciation: `SAY` rules for "eh" (consumer A), M one to M five, Rabbit M Q, auto ack, un-acked, fye-foe and
  basic ack.
