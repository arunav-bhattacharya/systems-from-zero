# A lock on every slip: how share groups let many readers share one partition

- Slug / scene: `share-groups`, `videos/scenes/share_groups.py:ShareGroups`
- Lesson: `msg-11`, section 1, "A lock on every record, and an answer from the reader"
- Audience / level: a complete newcomer. Can read a little code; doesn't know Kafka partitions, consumer groups, locks
  or acknowledgements.
- Length: 5:04 (~820 words of narration, plus two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=175` (after c1's locks run out at 10:00:30)
- The learner's real question: if every reader can read every partition, what stops two readers taking the same record?
- Misconceptions to steelman and break: (1) "more readers need more partitions" (the idle cooks); (2) "the group must
  notice a dead reader before its work moves", broken by the lock running out by itself at 10:00:30; (3) "a released
  record comes back in order", broken by the prediction (c2 gets 5 and 6, so 5 finishes after 6 started).
- Concept chain: one rail, one cook (consumer group) → any cook, any slip (share group) → a state and a 30-second lock on
  every record → answers (ACCEPT, RELEASE, REJECT, RENEW) → the lock runs out by itself → the start offset → the
  delivery limit archives a poison record → the price: no order (hardest last)
- Analogy family: the lesson's café kitchen. Six rails, six cooks, four idle cooks by the door; a cook who takes a slip
  has 30 seconds to say how it went; a cook who wanders off loses the slip back to the rail.
- Open loops: "what stops two cooks making the same order?" planted in scene 1 → answered in scene 3 and the moral.
- Assumptions: everything on the partition is the lesson's stepper (eight records, c1 to c3, two per poll, 10:00:00 and
  10:00:30, ACCEPT 2 and 3, ACCEPT 4 and RELEASE 5, c2 takes 5 and 6, c1 frozen, c3 takes 0 and 1 at delivery 2, start
  offset to 5, record 5 archived on its fifth delivery, a dead-letter copy with `__dlq.errors.offset=5` in 4.4, start
  offset to 8). 6 partitions, 30 texts a second and 300 at a sale are the lesson's section 0.

## The one picture

Top: one partition of `notifications`, eight record boxes 0 to 7, each with its owner inside and "count n" (its delivery
count) under it; a gold triangle for the start offset; a clock top right. Middle: three readers c1, c2, c3 (teal) with a
status line, and their answers above them. Bottom: a legend of the four states, grey available, gold acquired, green
acknowledged, red archived. Captions under it.

## Scene 1 · Six rails, four idle cooks · 0:00–0:55 · [FAMILIAR] [PAIN] [WISH] [QUESTION] [LOOP-PLANT] [JOKE:pivot]

VO: Picture a café kitchen on a Saturday morning. Order slips hang on six rails, and each rail belongs to one cook, who
works its slips in order. Orders pour in, so the owner calls in four more cooks. They stand by the door with nothing to
do, because every rail already has its cook. Paid to admire the rails. That's a Kafka consumer group. Kafka keeps a log
of records, split into partitions, and in a consumer group each partition has exactly one reader. The texting program
reads six partitions, so a seventh reader sits idle. Six readers send 30 texts a second. On a sale day, payments reach
300 a second. Wouldn't it be nice if any free cook could take any slip? Kafka 4.2 can do that. It's called a share
group. Its readers don't own partitions. They all read from all of them, and the broker, the server that runs Kafka,
hands out records one by one. But then, what stops two cooks from making the same order? Hold that question.

## Scene 2 · One partition, three readers · 0:55–1:25 · [SHRINK]

VO: Let's shrink it to one partition with eight text messages, and three readers, c1, c2 and c3, in the share group
notify. The broker keeps a state for every record. Each one starts out available, waiting for a reader. And it keeps a
start offset: every record before it is finished. Right now that's 0. Nothing is finished.

## Scene 3 · The lock · 1:25–2:10 · [SHOW] [ANALOGY] [MAP] [LOOP-PAYOFF]

VO: At ten o'clock, each reader asks for two records. Each one it gets is acquired: locked to that reader for 30
seconds. And its delivery count goes from 0 to 1. In the kitchen, a cook who takes a slip has 30 seconds to say how it
went. That's the answer to our question: a locked slip can't be taken by anyone else. Records 6 and 7 stay available.

## Scene 4 · The answers · 2:10–2:45 · [NAME] [SHOW]

VO: Each reader answers for each record. ACCEPT means done. c2's texts went out, so 2 and 3 are acknowledged. c3 sent 4.
But the texting company timed out on 5, which may pass. RELEASE gives it back: available again, with its count still 1.
REJECT would give up on it for good. The start offset stays at 0, because records 0 and 1 aren't finished.

## Scene 5 · Predict the next poll · 2:45–3:10 · [PREDICT] [PAUSE] [BREAK]

VO: Now c2 asks again, for two records. Which two does it get? Pause and guess.

(three seconds)

5 and 6. Record 5 again, now on its second delivery, and on a different reader. And 6 started before 5 finished. Order
is gone.

## Scene 6 · A reader freezes · 3:10–3:50 · [BREAK] [JOKE:release]

VO: Now c1 freezes. The Java runtime stops it to clean up memory, and it says nothing. You might think the group has to
notice c1 is gone first. It doesn't. At 10:00:30 the locks on 0 and 1 run out, and the broker makes them available
again, for anyone. Nobody had to notice anything. When c1 wakes up and answers, its answers are refused. Like coming back
from a nap to find your orders cooked by someone else. So the point is: a lock that runs out frees the work without a
meeting.

## Scene 7 · The start offset, and the limit · 3:50–4:45 · [SHOW] [NAME]

VO: c3 picks up 0 and 1, their second delivery, and accepts both. Now 0 to 4 are all done, so the start offset moves to
5. The share group forgets what's before it, but the records stay in the log for any other reader. Record 5 keeps timing
out. Released, taken, released, taken. Its count climbs: 3, 4, 5. On its fifth delivery, a release no longer makes it
available. The limit is five by default, so the broker archives it: given up on, never delivered again. Since Kafka 4.4,
the broker can also copy it to a dead-letter topic, with a header that says it was offset 5. Then 6 and 7 are accepted,
and the start offset moves to 8.

## Scene 8 · The price · 4:45–5:15 · [GUARDRAIL]

VO: Here's the price. Readers work side by side, and released records come back late. So a share group keeps no order,
not per key, not per partition. For text messages, that's fine. Two receipts can go out either way round. For a ledger,
where a refund must follow its payment, never. And the broker keeps the knobs in bounds: the lock between 15 and 60
seconds, the delivery limit between 2 and 10.

## Scene 9 · The code · 5:15–5:35 · [SHOW]

VO: Here's a reader that answers for every record, in Java and in Kotlin. It reads with KafkaShareConsumer, which has
the same poll as before. Sent: ACCEPT. Timed out: RELEASE. A bad phone number: REJECT. Then commitSync sends the answers
to the broker.

SCREEN: The lesson's explicit-mode loop, Java left and Kotlin right; ACCEPT, RELEASE, REJECT and commitSync light in turn.

## Scene 10 · The moral, and a check · 5:35–6:05 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So, what stops two cooks from making the same order? A lock on every slip. Any free reader takes any record, the
lock runs out by itself, and the count stops a record that never works. One quick check. A reader takes record 9 and
then crashes, silently. When can another reader get record 9? Pause and think.

(three seconds)

When its 30-second lock runs out. Then it's available again, and the next reader to take it makes its count 2.

---

### Beat check

- FAMILIAR + PAIN + WISH + QUESTION in the kitchen (scene 1); SHRINK (scene 2); ANALOGY + MAP at the lock (scene 3).
- PREDICT + PAUSE (scene 5, scene 10); BREAK: order (scene 5), "the group must notice first" (scene 6).
- NAME after the picture: acquired, delivery count, ACCEPT/RELEASE/REJECT, start offset, archived.
- GUARDRAIL: no order, never for a ledger, the bounds (scene 8). MORAL and RECAP last.
- Light moments: "paid to admire the rails", "back from a nap to find your orders cooked by someone else".

### Accuracy notes for the producer

- The partition's story is the lesson's stepper, frame by frame. Record 7's owner is not named there; the video gives it to c3.
- "Start offset" is the share-partition start offset (SPSO); the video uses the short name in captions.
- RENEW (Kafka 4.2, KIP-1222) is named in a caption only. Implicit mode (the next poll accepts the whole batch) is left
  to the lesson; the code shown is explicit mode, `share.acknowledgement.mode=explicit`.
- The dead-letter copy needs `share.version` 2, `errors.deadletterqueue.topic.name` and a topic name starting with `dlq.`;
  the video says only "since Kafka 4.4, the broker can also copy it".
- "Production-ready since 4.2" is said as "Kafka 4.2 can do that".
- The code is the lesson's explicit-mode loop with `AcknowledgeType.*` imported (so `ACCEPT` rather than `AcknowledgeType.ACCEPT`), `var` for the record type, and shorter comments.
