# Which box gets the payment? Keys, a hash, and the order you keep

- Slug / scene: `keys-partitions`, `videos/scenes/keys_partitions.py:KeysPartitions`
- Lesson: `msg-05`, section 0, "Which partition gets the payment: the key and the hash"
- Audience / level: a complete newcomer. Has met a log (adds at its end, keeps its order); doesn't know what a
  topic, a partition, a producer or a hash is.
- Length: about 5 minutes (~880 words of narration plus two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: the `poster` stamp (the moral: acct-42's payment and refund side by side in partition 3, lane glowing green)
- The learner's real question: a log keeps its order, so how can a refund ever show up before its payment?
- Misconception to steelman and break: (1) "taking turns is a fine rule, it spreads the load" (broken: acct-42's
  payment and refund land in two partitions with two readers, the refund is handled first); (2) "step three is fussy,
  just use Math.abs" (broken: 1871546916 % 6 is 0, the producer said 2).
- Concept chain: a topic is six logs → the producer picks one per record → round robin scatters an account → one
  account, one partition, worked out locally by every copy → the hash in four steps → the sum lives in the client and
  divides by the count (hardest last)
- Analogy family: the lesson's post room. Pigeonholes are partitions, the account number on the envelope is the key,
  a clerk is a copy of the app with its producer, the clerks' shared sum is the hash. A clerk with a different sum is
  librdkafka; adding two boxes is growing the topic.
- Open loops: "how did the order get swapped?" planted in scene 1 → answered in scene 10.
- Assumptions: all numbers are the lesson's demo output (acct-17 -1871546916 / 275936732 / partition 2; acct-42
  -1294421753 / 853061895 / partition 3; acct-18 212957696 / partition 2; card-1 830907359 / partition 5; acct-1
  294059390, partition 2 of 6, 6 of 8). The thank-you-note joke is new.

## The one picture

Left: the payments app (gold, "producer inside"), later a second copy under it. Right: the payments topic as six
pigeonhole lanes numbered 0 to 5 (blue); records drop in at the left end and stack in order. Bottom: the producer's sum
as five chips in a row (the key, its bytes, murmur2, clear the sign bit, remainder), each with a label underneath.
Captions on the last line. Gold is the producer, blue the partitions, yellow the key under study, purple a wrong or
different rule, red a broken order, green a correct partition, teal the two lanes added by growing the topic.

## Scene 1 · The refund before the payment · 0:00–0:25 · [QUESTION] [LOOP-PLANT]

VO: You pay for a coffee. A minute later you ask for a refund, because the order was wrong. That evening, your bank's
app lists the refund first. For a moment, it looks as if the café paid you. In a program that keeps account balances,
it's worse: a refund for a payment it has never seen. How did the order get swapped? Hold that question.

SCREEN: "what happened": 1 coffee paid, 2 refund a minute later. On the right, the bank app lists refund above coffee
and its outline turns red. Captions carry the two questions.

## Scene 2 · Six logs side by side · 0:25–1:05 · [FAMILIAR]

VO: Here's the setup. The payments app sends every payment and every refund to Kafka. Kafka is a program that keeps
logs of messages and lets other programs read them. Each message is a record: a key, a value, which is the payment
itself, and a few extra fields. A log only ever adds at its end, so a log keeps its order. That's true. But the
payments topic, Kafka's name for one stream of records, is six logs side by side. They're called partitions, numbered 0
to 5. When the app sends a record, one of the six has to get it. And the one who chooses is the producer: the part of
the Kafka library that runs inside the app.

SCREEN: The app box, a record chip `acct-17 | payment` (key and value pulse in turn), one lane, then five more and the
title "the payments topic". The producer label pulses.

## Scene 3 · Taking turns · 1:05–1:55 · [PAIN] [BREAK] [JOKE:amplify] [WISH]

VO: So what rule should the producer use? The simplest is taking turns, called round robin. Record one to partition 0,
record two to partition 1, and so on. The load spreads perfectly. Now watch account 42. Its payment lands in partition
0. Its refund lands in partition 1. Each partition has its own reader, and each reads at its own pace. Reader 1 is
quick. So the balance program gets the refund first, for a payment it has never heard of. That's a thank-you note for a
present nobody has posted yet. So the point really is: taking turns spreads the records, and scatters each account.
What we want is one rule: every record of one account goes to the same partition. And the app runs as several copies on
several computers, so the rule has to work without them asking each other.

SCREEN: Six numbered chips fly one per lane. Then `acct-42 pay` into lane 0 and `acct-42 refund` into lane 1; two
reader boxes; reader 1 pulses red, "handled 1st", then reader 0, "handled 2nd". A second app copy appears.

NOTE: The joke comes right after the failure is shown, and is cashed back at once.

## Scene 4 · The post room · 1:55–2:35 · [ANALOGY] [MAP]

VO: A post room solves this exact problem. Picture a wall of pigeonholes, little open boxes where letters wait to be
collected. Every clerk works out the box from the account number on the envelope, with the same sum. Letters for one
account land in one box, stacked in the order they came. No clerk asks another. Let's map it. The account number is the
record's key. The box is the partition. The clerks are the copies of the app, each with a producer. And the sum is
called a hash.

SCREEN: The lanes glow in turn as pigeonholes; "clerk" over each app. Copy 1 drops `acct-42 pay` and copy 2 drops
`acct-42 refund` into lane 3, side by side. Each mapping appears as a caption while its element glows.

## Scene 5 · The producer's sum · 2:35–3:30 · [SHRINK] [SHOW] [NAME]

VO: A hash function turns any bytes into a number. The same bytes always give the same number. Let's follow account 17
through the producer's sum, in four steps. One: turn the key into bytes. The text acct-17 is seven bytes. Two: hash the
bytes with murmur2, a fast hash function. Out comes a 32-bit number, and here it's negative. Three: clear the sign bit,
the leftmost bit, which says whether a number is negative. A partition number can't be negative, so the producer keeps
the other 31 bits. Four: divide by the number of partitions and keep the remainder. That's 2. So account 17 goes to
partition 2, from every copy of the app, every time. This is the default partitioner, the code in the Java client
library that picks the partition. And account 42? Its hash leaves a remainder of 3. Its payment and its refund both land
in partition 3, in the order they were sent.

SCREEN: The bottom row builds chip by chip: `acct-17` → `7 bytes` → `-1871546916` (the minus pulses red) →
`275936732` (caption "2^31 minus 1871546916") → `% 6 = 2` (green). Both copies drop `acct-17` into lane 2. Then the
row shows acct-42: `-1294421753` → `853061895` → `% 6 = 3`, and its payment and refund land in lane 3 in order.

NOTE: No narration of the long numbers; they stay on screen.

## Scene 6 · Predict a neighbour · 3:30–4:00 · [PREDICT] [PAUSE] [SHOW]

VO: Now a guess. acct-18 differs from acct-17 by one character. Will its hash be close to 17's? Pause and guess.
(three seconds) Not even close. A completely different number. That's the job of a good hash: keys that look alike
spread out evenly. And it still lands in partition 2, by luck. With six partitions, any two keys share one about one
time in six.

SCREEN: The row shows `acct-18` and "close to 17's?"; countdown bar. Then `212957696` twice, `% 6 = 2`; acct-18 drops
into lane 2 next to the two acct-17 records.

## Scene 7 · Break the shortcut · 4:00–4:35 · [BREAK] [JOKE:release]

VO: Here's a trap many of us would walk into. Step three looks fussy. Why not make the number positive the usual way,
with Math.abs? Let's try it. Math.abs of that negative number, divided by 6, leaves 0. Partition 0. The real producer
said 2. Clearing the sign bit isn't the same as dropping the minus sign. So a test that predicts partitions with
Math.abs gets most negative hashes wrong. Well... that's one very confident clerk, standing at the wrong box.

SCREEN: Back to acct-17. Step three glows, becomes `1871546916` (purple, "3. Math.abs"), step four `% 6 = 0` (red); the
acct-17 record in lane 2 pulses green. Then the row goes back to `275936732` and `% 6 = 2`. The app box wiggles.

## Scene 8 · Two warnings · 4:35–5:20 · [GUARDRAIL] [BREAK of the analogy]

VO: Two warnings. First, the sum lives in each client library, not in Kafka. Programs in Python or Go often use
librdkafka, a library written in C, and by default it hashes with a different function, CRC32. That's a clerk with a
different sum. Same key, maybe a different box, unless that program is set to use murmur2 too. Second, the sum divides
by the number of partitions. Grow the topic from 6 to 8, and acct-1 moves from partition 2 to partition 6. Its old
records stay behind in 2. About three keys in four move. So choose the partition count once, with room to grow.

SCREEN: The second app turns purple, "Go app, librdkafka"; step two reads "CRC32 ..." and steps three and four "?"; a
purple `acct-17 ?` stops short of the lanes. Caption `partitioner=murmur2_random`. Then the row clears, `acct-1 old`
goes into lane 2, two teal lanes 6 and 7 appear, `acct-1 new` goes into lane 6 (caption "294059390 % 6 = 2,
294059390 % 8 = 6"), and the old record pulses red.

## Scene 9 · The code · 5:20–5:35 · [SHOW]

VO: In Java and Kotlin, all you choose is the key. Pass the account id as the record's key, and the producer does the
four steps for you.

SCREEN: Two panels over the dimmed diagram. Java: `new ProducerRecord<>("payments", "acct-17", payment)`,
`producer.send(record)`, and the same sum by hand, `Utils.toPositive(Utils.murmur2(keyBytes)) % 6`. Kotlin: the same
lines. The key lines, then the sum lines, flash.

## Scene 10 · The moral, and a check · 5:35–6:10 · [MORAL] [LOOP-PAYOFF] [RECAP] [PREDICT] [PAUSE]

VO: So how did the refund get ahead of its payment? They went into two different logs, and nothing keeps order across
logs. One key per account puts both in one partition, and inside one partition, order holds. Same key, same sum, same
box. Choose the key for the order you need. One quick check. card-1 hashes to a positive number. Would a test that uses
Math.abs pick the right partition for it? Pause and think. (three seconds) Yes. For a positive number, Math.abs changes
nothing, so both give partition 5. It only goes wrong when the hash is negative.

SCREEN: acct-42's payment and refund appear in lanes 0 and 1, then slide together into lane 3, which glows green.
Caption "same key, same sum, same box". For the check, the row shows `card-1`, `6 bytes`, `830907359`, "3. Math.abs ?";
countdown; then `830907359` and `% 6 = 5`.

---

### Beat check

- Opens with QUESTION (scene 1), from a felt symptom.
- FAMILIAR (scene 2): the log the viewer has met, then the topic as six of them.
- PAIN, BREAK and WISH (scene 3) before the ANALOGY and MAP (scene 4).
- SHRINK and SHOW (scene 5), with NAME (hash function, default partitioner) after the post room.
- PREDICT with PAUSE (scene 6, and the check in scene 10).
- BREAK of the wrong model (scene 7) and of the analogy's clerk with another sum (scene 8).
- GUARDRAIL (scene 8) and MORAL (scene 10) last. Light moments: the thank-you note (1:45), the confident clerk (4:30).
- Open loop "how did the order get swapped?" paid off by name in scene 10.

### Accuracy notes for the producer

- Every hash and partition on screen is from the lesson's `PartitionForDemo` output (6 partitions) and its growth Try
  it (acct-1 at 8 partitions). The acct-42 payment and refund placement in partition 3 follows from its hash.
- The round-robin picture is the lesson's thought experiment; the real producer never round-robins keyed records.
  Records with no key go in sticky runs (section 2), left out here.
- "Each partition has its own reader" stands for one consumer per partition in a group (section 1); readers at their
  own pace is the lesson's reason the refund can be handled first.
- Order is the order records reach the leader; two copies racing on one account, and producer retries, can still swap
  them (section 1 and the next lesson). Left out of the video.
- "About three keys in four move" is the lesson's 6-to-8 figure (6 of every 24 hash values stay).
- librdkafka's default is CRC32; `partitioner=murmur2_random` matches Java (lesson). The video doesn't claim which
  partition the Go program picks.
- Explicit partition numbers and `partitioner.class` are left to the lesson.
