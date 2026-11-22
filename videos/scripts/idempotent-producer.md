# Did that payment go twice? Retries, and the idempotent producer

- Slug / scene: `idempotent-producer`, `videos/scenes/idempotent_producer.py:IdempotentProducer`
- Lesson: `msg-06`, section 3, "Retries can duplicate and reorder; the idempotent producer stops both"
- Audience / level: a complete newcomer. Has met a partition's log, offsets, the producer and the leader; doesn't know
  what a sequence number or a producer id is.
- Length: about 5 minutes (~900 words of narration plus one pause)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: the `poster` stamp (the retry of seq 16 answered with offset 16, nothing written at 17, the leader's note
  "producer 5: next 17")
- The learner's real question: the send failed, so the payment isn't there, right? And if I retry, is that safe?
- Misconception to steelman and break: "an error means nothing happened, so retrying is harmless" (broken by the lost
  answer: pay-16 at offsets 16 and 17); then "one request at a time fixes it" (keeps order, costs speed, still
  duplicates).
- Concept chain: a timeout means "stopped waiting" → a retry of a written batch duplicates it → five in flight lets a
  retry land late → a name and a number on every message, and a note per sender → producer id, sequence number, the
  leader's last five batches → the settings, the silent trap, and where the promise stops (hardest last)
- Analogy family: the lesson's train tunnel. Your phone is the producer, your friend is the leader, her chat is the
  log. Added for the mechanism: every message carries your name and a number ("Sam, message 16"), and your friend keeps
  a note per sender (the next number, the last five). Tapping Retry yourself is your own second `send()`.
- Open loops: "why did you send that twice?" planted in scene 1 → answered in scene 10.
- Assumptions: producer id 5, pay-16 at offset 16, the duplicate at 17, "next 17", refused 18 are the lesson's stepper.
  The name "Sam" is invented. The reorder picture with idempotence off (pay-18 at offset 17, pay-17 at 18) and the
  check's offsets are illustrative, built from the stepper's numbers.

## The one picture

Top left: the producer (gold), top right: the leader (blue), each with a title, a grey alias line and a state line.
Between them two lanes: requests run right along the top lane, answers run left along the lower one. A red cross
marks a lost answer or a timed-out request. Bottom: one partition's log, cells for offsets 14 to 21 with the offsets
above. Yellow is pay-16, gold pay-18, red a duplicate or a refusal, green a correct answer, purple your own second send.

## Scene 1 · The tunnel · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: You're on a train, sending a message to a friend, just as it goes into a tunnel. The message turns red: not sent.
So you tap Retry. Out of the tunnel, your friend writes back: why did you send that twice? The red mark looked like a
fact about the message. It was only a fact about your phone: it had stopped waiting. The first copy got through.

SCREEN: "your phone" and "your friend", the two lanes, three cells labelled "your friend's chat". The message runs
across and lands; the phone's state turns red "not sent"; the retry lands in the next cell. Both cells pulse red,
then the first green. Caption "not sent? no: stopped waiting".

## Scene 2 · The same trap in Kafka · 0:30–0:55 · [FAMILIAR] [MAP]

VO: Kafka, a program that keeps logs of messages and lets other programs read them, sets the same trap. The program
that writes is the producer, inside the payments app. It sends each payment to the leader, the server that adds it to
the partition's log, and waits for an answer: the offset, the payment's place in the log.

SCREEN: The boxes become "producer, inside the payments app" and "leader, adds to the log"; the log grows to eight
cells with offsets; pay-14 and pay-15 in place; an "offset 15" answer runs back.

## Scene 3 · A lost answer · 0:55–1:45 · [PAIN] [SHOW] [JOKE:amplify]

VO: Watch pay-16. It reaches the leader, and the leader writes it at offset 16. Then the answer is lost. After a while,
all the producer knows is that it heard nothing. So it retries, on its own. The leader can't tell a retry from a new
record, so pay-16 goes in again, at offset 17. Every reader of this log now sees the payment twice. One coffee, charged
twice. Customers have a gift for noticing exactly that. So the point really is: a retry is only safe if the leader can
recognise it.

SCREEN: State lines "idempotence off" and "remembers nothing". pay-16 lands at 16; the answer stops halfway with a red
cross, "answer lost"; "heard nothing"; the retry lands at 17; both turn red.

## Scene 4 · Reordering, and the obvious fix · 1:45–2:35 · [PAIN] [BREAK] [WISH]

VO: There's a second problem. The producer keeps up to five requests in flight at once. Say pay-17's request times
out, while pay-18 gets through. The retry of pay-17 lands after pay-18. If pay-18 were a refund, it would now overtake
its payment, inside one partition. You could send one request at a time. That keeps the order, but each connection
then waits a round trip for every batch, and the lost answer still gives you a duplicate. What we'd love is for the
leader to say: oh, it's you again, I already have that one.

SCREEN: pay-17 stops halfway on the request lane, "timed out"; pay-18 lands at 17; the retried pay-17 lands at 18, and
the swap pulses red. Captions for the fix and its costs, then the wish in yellow.

## Scene 5 · The friend's note · 2:35–3:15 · [ANALOGY] [MAP]

VO: Back to the train. Suppose every message carries your name and a number: Sam, message 16. And your friend keeps a
little note for each sender: the next number she expects, and the last five she got. Resent 16? She already has it.
No second copy; she just replies again. 18 before 17? She says: wait, send me 17 first. Let's map it. Your name is the
producer id. The number is the sequence number. Your friend is the leader, and her note is what the leader remembers
for each producer.

SCREEN: The boxes go back to "your phone" ("Sam, message 16") and "your friend" ("Sam: next 17", "and the last five she
got"). "Sam 16" and "Sam 18" run across with their replies as captions; then each mapping is a caption.

## Scene 6 · The idempotent producer · 3:15–4:05 · [SHOW] [NAME]

VO: Here's the real thing. At start-up, the producer gets a producer id from the broker: 5. It numbers its records for
each partition, so pay-16 has sequence number 16. The leader writes it at offset 16, and notes: producer 5, next 17.
Then the answer is lost again. The retry carries the same id and the same number. The leader finds 16 among the last
five it remembers, writes nothing, and answers with the offset it gave the first time: 16. This is the idempotent
producer. Idempotent means doing something twice has the same effect as doing it once. It has been on by default since
Kafka 3.0.

SCREEN: "producer id 5"; "pay-16: seq 16"; the request "id 5 | seq 16" lands at 16; the note reads "producer 5:
next 17"; the answer is lost; the retry runs across, cell 17 pulses grey, "nothing written", and "offset 16" runs back
(green). The names appear as captions.

## Scene 7 · Predict the gap · 4:05–4:40 · [PREDICT] [PAUSE] [SHOW]

VO: Now the reordering case, with idempotence on. pay-17 times out, and pay-18 arrives first. The leader expects 17.
What does it do with 18? Pause and guess. (three seconds) It refuses it, with an error called out of order sequence
number. Then the producer resends 17, then 18, and both are written once, in send order.

SCREEN: seq 17 stops halfway, "timed out"; seq 18 reaches the leader, which pulses; countdown. A red "refused: out of
order" runs back; caption `OUT_OF_ORDER_SEQUENCE_NUMBER: expected 17, got 18`; seq 17 lands at 17, seq 18 at 18;
"producer 5: next 19".

## Scene 8 · Settings, a trap, and the limit · 4:40–5:40 · [GUARDRAIL] [JOKE:soften]

VO: It needs three settings: acks=all, retries above zero, and at most five requests in flight. Five is exactly how
many batches the leader can recognise. And here's the trap. Set acks=1 for speed, without mentioning idempotence, and
the producer quietly turns it off. No warning. Polite of it, and terrible manners for a payment. So set
enable.idempotence to true by name. Then the same conflict stops the producer at start-up, where you'll see it. And
know where it stops. It covers this producer's own retries. If your code catches a TimeoutException and calls send()
again, that's a new record, with a new number. That's you, tapping Retry in the tunnel. A restarted program gets a new
producer id, too. Copies across those lines need the payment's own idempotency key, checked by the consumer.

SCREEN: Captions for the three settings and the five batches (the leader pulses). The producer's lines change to
"acks=1, idempotence off?!" (red), then "enable.idempotence=true" (green). A purple "id 5 | seq 19" lands at 19 as
"again?"; the producer becomes "producer id 6 (restarted)".

## Scene 9 · The code · 5:40–5:55 · [SHOW]

VO: In Java and Kotlin, it's two lines in the producer's settings. Turn idempotence on by name, and keep acks at all.

SCREEN: Java and Kotlin panels over the dimmed diagram: `props.put("enable.idempotence", "true")`,
`props.put("acks", "all")`, `new KafkaProducer<String, String>(props)`; the Kotlin `Properties().apply { ... }`.

## Scene 10 · The moral, and a check · 5:55–6:35 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So why did your friend get two copies? Your phone retried a message that had already arrived. With a name and a
number on every message, the receiver spots the copy. Retries are safe only when the receiver can recognise them. Turn
idempotence on by name. One quick check. Your code catches a TimeoutException for pay-20 and sends it again.
Idempotence is on. Can pay-20 end up in the log twice? Pause and think. (three seconds) Yes. Your second send gets a
new sequence number, 21, so the leader sees a new record. Only the payment's own idempotency key can catch that one.

SCREEN: The poster state again; the retry is recognised. For the check: pay-20 with seq 20 lands, its answer is lost,
"TimeoutException"; countdown; a purple "pay-20 | seq 21" lands as a second pay-20.

---

### Beat check

- Opens with QUESTION (scene 1) from a felt moment; FAMILIAR (scene 2) maps it onto Kafka.
- PAIN (scenes 3 and 4), the obvious fix broken (scene 4), WISH (scene 4).
- ANALOGY + MAP (scene 5) before the NAME (scene 6).
- PREDICT with PAUSE (scene 7, and the check in scene 10).
- GUARDRAIL (scene 8) and MORAL (scene 10) last. Light moments: customers noticing (1:35), polite and terrible
  manners (4:55).
- Open loop "why did you send that twice?" paid off in scene 10.

### Accuracy notes for the producer

- The stepper and section are the source: producer id 5, sequence 16, offset 16, duplicate at 17 without idempotence,
  refusal of 18 when 17 is expected, the last five batches (`ProducerStateEntry.NUM_BATCHES_TO_RETAIN`).
- Sequence numbers count records per partition, and a batch carries the number of its first record. The video sends
  one record per batch, so a batch's number and the record's number are the same.
- The reorder-without-idempotence offsets (pay-18 at 17, pay-17 at 18) are illustrative.
- `acks=all` also makes sure a new leader rebuilds the same memory from its copy of the log; left out for time.
- "Five requests in flight" is `max.in.flight.requests.per.connection`'s default and the idempotence limit.
- Silent fallback: a conflicting setting without `enable.idempotence` turns idempotence off; with
  `enable.idempotence=true` the conflict throws a `ConfigException` at start-up (lesson).
- In the check, the first pay-20 may or may not be in the log; the video shows the case where it is, which is the one
  that matters.
