# When is a payment safe? Three copies, one leader, and the high watermark

- Slug / scene: `kafka-isr`, `videos/scenes/kafka_isr.py:KafkaISR`
- Lesson: `msg-04`, section 0, "Three copies of every partition, and one leader among them"
- Audience / level: a complete newcomer. Met the log, offsets and partitions in the two lessons before; knows nothing
  about replication.
- Length: 4:09 (~650 words of narration, two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=148` (just after the guess: broker 2 at 8, broker 3 held at 5 in red, the high watermark at 5)
- The learner's real question: if the disk holding a partition dies, are the payments gone? And when can Kafka
  honestly tell a producer "it's safe"?
- Misconception to steelman and break: (1) "answer as soon as the leader has it" (lost with the leader's disk) and
  "wait for every follower" (one slow follower stalls every write); (2) "everyone in the room means three copies",
  broken by the room of one.
- Concept chain: one disk is a single point of loss → copies: leader and followers, offsets given by the leader,
  followers fetch → each replica's end offset → the ISR and the high watermark, the smallest end offset in the ISR →
  acks=1 and acks=all, committed records → a new leader must hold every committed record (hardest last)
- Analogy family: the lesson's shop with three sales books. The owner writes, two assistants copy, "a sale counts once
  everyone in the room has copied it", both assistants home ill.
- Open loops: "when is a payment safe?" planted in scene 1 → scene 6 (the producer hears safe once the line passes);
  "keep that rule in mind" planted in scene 2 → the room of one in scene 8, handed on to the lesson's last section.
- Assumptions: offsets 0 to 4 on every replica, three payments at 5, 6 and 7, broker 2 catching up to 8 and broker 3
  held at 5 are the lesson's stepper (section 2, first three frames); here broker 3 then catches up instead of being
  removed (removal is section 2). The check's end offsets (9, 7, 9) are made up for the question.

## The one picture

Three rows, one per broker: a name box on the left (broker 1 the leader in gold, brokers 2 and 3 followers in teal),
then numbered record cells, then "end: N", the replica's log end offset. A yellow dashed vertical line through all
rows is the high watermark, labelled at the top. A gold dashed box around the rows in sync is the ISR, "the room". The
producer sits top left with an arrow to the leader's next cell. Committed cells turn green. Captions at the bottom.

## Scene 1 · One disk · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: A coffee-shop app sends every card payment to Kafka, a program that keeps logs of records and lets other programs
read them. The payments live in a log called payments-0, stored as files on one computer's disk. The program running
Kafka there is a broker. Now that disk dies. Nobody can write to payments-0 or read it. And if the disk is gone for
good, so are the payments. How do we keep them, and when is a payment really safe?

SCREEN: Title card. Cells 0 to 4 appear with "broker 1, payments-0"; they dim under a red cross; the question as a
caption.

## Scene 2 · The shop · 0:30–0:48 · [FAMILIAR] [ANALOGY] [LOOP-PLANT]

VO: Picture a small shop that keeps three copies of its sales book. The owner writes each sale in her book, and two
assistants copy it into theirs, line by line, in the same order. The house rule: a sale counts once everyone in the
room has copied it. Keep that rule in mind.

SCREEN: The row becomes the owner's book; two assistant rows copy lines 0 to 4. A gold dashed box, "in the room", and
the rule as a caption.

## Scene 3 · The map · 0:48–1:23 · [MAP] [NAME]

VO: Kafka does the same, once per partition. Each copy is a replica, and three is the usual number. The owner's copy
is the leader: every write goes to it, and it decides the order. The assistants are followers. Only the leader gives
out offsets, so offset 4 means the same payment on every broker. Each follower keeps asking the leader: anything after
my last record? It appends what comes back, at the same offsets. Each replica has its own end offset: the offset its
next record will get. Here, every copy holds 0 to 4, so each one's is 5.

SCREEN: Name boxes become broker 1 (leader), brokers 2 and 3 (followers); offset 4 glows in all three rows; "end: 5"
appears on each row.

## Scene 4 · When is it safe? · 1:23–1:46 · [PAIN] [BREAK] [WISH]

VO: Now a producer, the program that writes, sends three payments. The leader adds them at 5, 6 and 7. Its end offset
is 8. When should it tell the producer they're safe? Answer right away, and the producer may hear safe a moment before
the leader's disk dies. Those three are lost. Wait for every follower, and one slow follower holds up every write.

SCREEN: The producer and its arrow; gold cells 5 to 7 on the leader, "end: 8". A red cross dims them ("5, 6 and 7:
lost with the disk"), then they return: "wait for every follower? one slow one holds up every write".

## Scene 5 · The ISR and the high watermark · 1:46–2:09 · [NAME]

VO: Kafka takes a middle path. The leader keeps a list of the replicas keeping up with it: the in-sync replicas, ISR
for short. That's the people in the room. From them it works out the high watermark: the smallest end offset in the
ISR. It's the line up to which everyone in the room has copied. Records below it are on every in-sync copy. They're
called committed.

SCREEN: The room box returns as "ISR: in the room". The yellow high-watermark line at 5. Cells 0 to 4 turn green.

## Scene 6 · Predict · 2:09–2:39 · [PREDICT] [PAUSE] [SHOW] [LOOP-PAYOFF]

VO: Broker 2 fetches 5 to 7. Its end offset is 8. Broker 3 is slow. It's still at 5. Where is the high watermark?
Pause and guess.

(three seconds)

5. The smallest end offset in the room is broker 3's. So consumers still can't see 5, 6 or 7, and the producer is
still waiting. Then broker 3 catches up to 8. The high watermark jumps to 8, and the producer gets its answer.

SCREEN: Broker 2's cells 5 to 7, "end: 8"; broker 3 pulses red, "end: 5" in red; countdown (the line is hidden during the guess). The line returns at 5; the
producer pulses. Broker 3 fills 5 to 7, the line jumps to 8, cells 5 to 7 turn green: "the producer hears safe".

## Scene 7 · acks · 2:39–3:03 · [NAME]

VO: The producer picks how long to wait with a setting called acks. acks=1: answer once your own copy has it.
acks=all: answer once every in-sync replica has it, the moment the high watermark passes the record. acks=all has been
the default since Kafka 3.0. And because consumers read only below the high watermark, they never see a record that
could vanish.

SCREEN: Captions for each setting while the leader, then the room, then the line pulse.

## Scene 8 · Guardrails · 3:03–3:34 · [GUARDRAIL] [JOKE:soften]

VO: When the leader's broker fails, a follower takes over, but only one that has every committed record. Electing one
that missed some would make them disappear without any error, because its shorter log becomes the truth. That's an
unclean leader election, and Kafka forbids it by default. The partition stops taking writes instead of losing data.
And one gap in the house rule. If both assistants go home, the room is the owner alone. Everyone in the room has
copied every sale. It's a very small room.

SCREEN: Broker 1 turns red and dims; broker 2 becomes "new leader". Broker 3's cells 5 to 7 dim ("unclean leader
election: forbidden by default", "no writes, rather than lost payments"). Back to normal; then both followers dim and
the room shrinks to "ISR: the leader alone": "acks=all is met with one copy. The lesson's last section closes this
gap."

NOTE: The joke is the explanation: the rule is met, by a room of one.

## Scene 9 · Moral and check · 3:34–4:09 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So: one leader decides the order, followers copy it, and a record counts once everyone in the room has it. The
room is the ISR, and the line is the high watermark.

One quick check. The leader's end offset is 9, broker 2 is at 7, and broker 3 at 9, all in sync. Where's the high
watermark, and what can consumers read? Pause and think.

(three seconds)

7. Consumers can read up to offset 6. Broker 2 holds everyone back.

SCREEN: The room returns around all three. For the check, the leader and broker 3 gain cell 8 ("end: 9"); broker 2
loses cell 7 ("end: 7" in red); countdown. The line moves to 7; cells 0 to 6 glow green; "the smallest end offset in
the room sets the line".

---

### Beat check

- Opens with QUESTION from a felt loss (scene 1); FAMILIAR and ANALOGY (scene 2) before replication words; MAP out
  loud (scene 3).
- BREAK of both obvious answers (scene 4), then the middle path named only after the pain (scene 5).
- PREDICT with PAUSE (scene 6, and the check in scene 9), SHOW right after.
- GUARDRAIL (scene 8: clean elections only, and the room of one) and MORAL (scene 9) last. Light moment: "it's a very (3:30)
  small room".

### Accuracy notes for the producer

- Offsets 0 to 4 with end offset 5, the three payments at 5 to 7, broker 2 at 8 and broker 3 stuck at 5 with the HW at
  5 come from the lesson's stepper. The stepper then removes broker 3 from the ISR after 30 seconds; the video instead
  lets it catch up, which the section's rule (HW = smallest LEO in the ISR) also covers. Removal and
  `min.insync.replicas` are section 2.
- "Answer right away" is acks=1; the video shows the loss case the section describes.
- The failover scene is schematic: who picks the new leader (the controller, KRaft) is section 1.
- The check's end offsets are made up; the answer follows the section's rule.
- No code on screen: the section has none (the admin-client code belongs to section 2).
- Pronunciation: `SAY` rules for acks equals all, acks equals one, payments zero and Kafka three point oh.
