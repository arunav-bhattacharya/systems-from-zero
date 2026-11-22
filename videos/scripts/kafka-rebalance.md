# Who reads partition 3 now? A rebalance, and the handover that keeps its bookmark

- Slug / scene: `kafka-rebalance`, `videos/scenes/kafka_rebalance.py:KafkaRebalance`
- Lesson: `msg-08`, section 1, "Handing a partition over without losing its bookmark"
- Audience / level: a complete newcomer. Has met partitions, a consumer and its committed offset (the bookmark);
  doesn't know what a consumer group or a rebalance is.
- Length: about 5 minutes (~880 words of narration plus two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: the `poster` stamp (partition 3 handed to c2 with the bookmark at 340, "nothing repeated", the processed
  span green)
- The learner's real question: we added consumers to go faster, so why were payments added twice?
- Misconception to steelman and break: (1) "more copies share the work like more hands" (broken: c2 starts at the old
  bookmark, 300 to 339 again); (2) "commit in onPartitionsLost too, to be safe" (broken: a late commit drags the
  bookmark back).
- Concept chain: one owner per partition (a group) → owners change (a rebalance) → the new owner starts at the
  committed offset → so commit before the partition leaves (onPartitionsRevoked) → why that's safe (revoke before
  assign) and where it isn't (lost, crashes) (hardest last)
- Analogy family: the lesson's restaurant. Tables are partitions, waiters are consumers, one waiter per table is the
  group, the note to the next waiter about what's been served is the committed offset, the moment before walking away
  is the handover. A waiter sent home phoning in a change is a commit in onPartitionsLost.
- Open loops: "where did the doubles come from?" planted in scene 1 → answered in scene 8.
- Assumptions: month-end numbers (8 a second, 30 arrive, 79,200 behind), partition 3 (processed before 340, committed
  300, c2 repeats 300 to 339), the ownership moves (c2 gets 3, 4, 5; c3 gets 2 and 5) and the no-handover lab (200
  processed for 120, 80 twice) are the lesson's. The onPartitionsLost scenario's 360 and the check's 500 and 520 are
  made up, and the check says so.

## The one picture

Top: six partitions as tables 0 to 5, each outlined in its owner's colour with a small owner tag under it (c1 gold, c2
teal, c3 purple). Sides: the members c1 (left), c2 and c3 (right). Middle: partition 3 up close, a bar from offset 280
to 360 with ticks; a blue bookmark post above it ("committed: 300"), a gold pointer under it ("c1 has processed
everything before 340"), a gold span for the processed records, a red span for repeats.

## Scene 1 · Month-end · 0:00–0:35 · [QUESTION] [LOOP-PLANT]

VO: Picture the last day of the month. Card payments pour into Kafka, a program that keeps logs of messages and lets
other programs read them. The ledger, the program that keeps each account's balance, reads them. It handles 8 payments
a second, and 30 arrive. After an hour, it's 79,200 payments behind. So the team starts two more copies. A few seconds
later, the logs show payments added twice. Where did the doubles come from? Hold that question.

## Scene 2 · One owner per partition · 0:35–1:15 · [FAMILIAR] [ANALOGY] [NAME]

VO: First, how copies share the work. A restaurant gives each table to one waiter, and a waiter looks after several
tables. Nobody gets three desserts, and courses come in order. Kafka does the same. The three copies form a consumer
group, and the group gives each partition to exactly one member. When members join or leave, partitions change owner.
That's called a rebalance. The partition moves. But what happens to its bookmark?

SCREEN: Tables glow in turn; c2 takes 3, 4 and 5, then c3 takes 2 and 5.

## Scene 3 · Partition 3 up close · 1:15–2:15 · [PAIN] [PREDICT] [PAUSE] [BREAK]

VO: Take partition 3, before the move. c1 owns it, and has processed everything before offset 340. It commits after
every batch of 100, so the group's bookmark says 300. Now c2 joins, and the group gives partition 3 to c2. Where does c2
start? Pause and guess. (three seconds) At 300, where the bookmark says. c2 knows nothing else. So it processes 300 to
339 a second time. And if c1 is still busy with that batch when c2 starts, both apply the same payments at the same
moment. The lesson's lab takes the handover away. Three consumers, 120 payments in the topic, and the group processes
200. Eighty of them twice, just from adding two consumers.

SCREEN: The zoom bar for partition 3, the gold span to 340, the bookmark at 300; c2's tag on 3, 4, 5; countdown; the
red span 300 to 340, "c2 again: 300 to 339"; c1 and c2 pulse red; lab captions.

## Scene 4 · The waiter's note · 2:15–2:45 · [ANALOGY] [MAP]

VO: Back to the restaurant. A good waiter doesn't walk away from a table in the middle of a meal. Before the table
moves, they tell the next waiter what's been served. Let's map it. The table is the partition, the waiter is the
consumer, and the note is the committed offset. The moment just before leaving is the handover.

## Scene 5 · The listener · 2:45–3:45 · [SHOW] [NAME]

VO: Kafka gives the consumer that moment. You register a ConsumerRebalanceListener: three functions the consumer calls,
from inside poll, when its partitions change. onPartitionsRevoked: these are leaving, and they're still yours. Finish
or drop the current work, and commit how far you got. onPartitionsAssigned: these are new to you, and you start at
their committed offsets. Replay the move with that commit, and c2 starts at 340. Nothing is processed twice. And
onPartitionsLost: the group has already given these to someone else, usually because this member was thrown out. Don't
commit. That bookmark isn't yours to move any more.

SCREEN: The bookmark moves to 340 on the revoke; partition 3 turns teal; "c2 starts at 340"; "nothing repeated"; the
processed span turns green.

## Scene 6 · Why it's safe, and a tempting mistake · 3:45–4:45 · [GUARDRAIL] [BREAK] [JOKE:is-the-explanation]

VO: Why is this safe? One rule about order. The group never gives a partition to its new owner until the old owner has
revoked it. So c1's commit always lands before c2 reads the bookmark. Now a tempting idea: commit in onPartitionsLost
too, just to be safe. Follow it through. c1 was thrown out while stuck at 300. c2 already owns partition 3 and has
moved the bookmark to 360. Then c1's late commit drags it back to 300, and the next owner repeats sixty payments. It's
a waiter who was sent home, phoning in to change the bill of a table someone else now serves. One more note. A member
that dies without revoking can't commit anything, so repeats can still happen. That's why the ledger still checks each
payment's idempotency key. But a planned rebalance repeats nothing.

## Scene 7 · The code · 4:45–5:00 · [SHOW]

VO: In Java and Kotlin, you pass the listener to subscribe. Commit in onPartitionsRevoked, and in onPartitionsLost, just
forget the partitions.

SCREEN: The lesson's listener in Java (an anonymous class) and Kotlin (an `object :` expression), shortened.

## Scene 8 · The moral, and a check · 5:00–5:40 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So where did the doubles come from? Partitions that moved without a commit. The new owner started at an old
bookmark. A partition that moves without a commit gets processed twice. One quick check, with numbers made up for it.
c1 owns partition 4, has processed everything before 520, and last committed 500. It commits in onPartitionsRevoked.
Where does the new owner start? Pause and think. (three seconds) At 520. The handover commit moves the bookmark to the
next record to read, so nothing repeats.

---

### Beat check

- QUESTION (scene 1); FAMILIAR + ANALOGY and NAME (group, rebalance) in scene 2.
- PREDICT with PAUSE and the BREAK (scene 3), ANALOGY + MAP (scene 4), SHOW and NAME of the listener (scene 5).
- GUARDRAIL and a second BREAK (scene 6), MORAL (scene 8). Light moments: three desserts (0:45), the waiter phoning in
  (4:25).
- Open loop "where did the doubles come from?" paid off in scene 8.

### Accuracy notes for the producer

- Section 1 is the source for partition 3 (340, 300, repeats 300 to 339), the three functions and their rules, and the
  order rule (revoke before assign). The no-handover lab output (200 for 120) is the section's Try it.
- The video shows c2 joining and taking 3, 4 and 5 as in the lab log; which rebalance protocol stops which partitions
  is section 2's, left out.
- The onPartitionsLost scenario's numbers (stuck at 300, c2 at 360) are illustrative.
- `processedOffsets` counts only fully processed records: the last processed offset plus one.
- Why a member gets thrown out (session timeout, `max.poll.interval.ms`) is section 3's.
