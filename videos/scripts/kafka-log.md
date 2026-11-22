# Reading deletes nothing: the log, and a bookmark for each reader

- Slug / scene: `kafka-log`, `videos/scenes/kafka_log.py:KafkaLog`
- Lesson: `msg-02`, section 0, "Keep every payment, and give each reader a bookmark: the log"
- Audience / level: a complete newcomer. Uses a group chat; met a broker's queue in Queues and brokers; knows nothing
  about Kafka.
- Length: 4:06 (~640 words of narration, two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=138` (the log with five records, the ledger at 5 and the fraud check at 4)
- The learner's real question: if reading doesn't use a message up, what does a reader keep, and how can a new
  program read last week's payments?
- Misconception to steelman and break: "a message is used up once it's read" (letters, to-do lists, the broker's
  queue). Broken by the fraud check reading two records and only its number moving, the weekly report starting at 0,
  and the ledger moving its number back to read again.
- Concept chain: the queue deletes on read → three costs → keep every payment in a file that only grows, numbered →
  each reader is one number → reading moves only that number (hardest last: the names log, position, Kafka, record,
  producer, consumer, topic)
- Analogy family: the lesson's family group chat. Posts, each phone's "you stopped here", a new member, editing a
  post; the closing's "leave a busy chat unread for a day".
- Open loops: "a new program wants last week's payments; from the broker: nothing" planted in scene 1 → scene 5 (the
  weekly report starts at 0); "a bug means yesterday must be worked through again" planted in scene 2 → scene 5.
- Assumptions: the five records are the lesson's section 1 table (offsets 0 to 4). The readers' numbers (ledger at
  4 then 5, fraud check at 2 then 4, weekly report at 0 then 3) are hand-picked for the picture.

## The one picture

A row of record boxes (key and amount, coloured by kind: auth blue, capture green, refund gold), each with its
number in yellow on the left, and a dashed slot at the end where the next record goes. Under the row, one coloured
bookmark per reader (ledger gold, fraud check green, weekly report purple), each in its own lane, carrying its
number and pointing up at the record it will read next. The payments program sits above the end and drops records
in. Captions at the bottom.

## Scene 1 · The chat · 0:00–0:25 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: Picture a family group chat. Your aunt posts a photo, and everyone reads it in their own time. Each phone
remembers where its owner stopped. And your reading deletes nothing for anyone else. Now a payments company wants a
new program to study last week's payments. With the broker from the last lesson, it gets nothing. Why? And what
would a chat do differently?

SCREEN: Title card. Two phones with the same four posts; "you stopped here" after post 2 on one, after post 4 on
the other. The phones leave; captions "a new program wants last week's payments", "from the broker: nothing".

## Scene 2 · The queue, and its cost · 0:25–1:06 · [FAMILIAR] [PAIN] [JOKE:amplify] [WISH] [LOOP-PLANT]

VO: Here's the broker's queue, with four payments. The ledger reads one, says done, and the broker deletes it. A
message is used up once it's read. Letters work that way, and so do to-do lists. It's a library that shreds each
book as soon as the first reader brings it back. Very tidy shelves. A very unhappy second reader.

It costs three things. To feed four programs, the broker keeps four queues, with a copy of every payment in each. A
new program starts with nothing. And if a bug means yesterday's payments must be worked through again, the queue
can't give them back. Wouldn't it be nice if every payment stayed, and each reader kept only its own place? That's
the chat.

SCREEN: The four records in the queue; the ledger's tag steps along and each record drops away. The weekly report's
tag arrives under an empty queue: "the weekly report: nothing left to read". Three red captions, then the yellow
wish.

## Scene 3 · The log · 1:06–1:38 · [ANALOGY] [MAP] [SHRINK]

VO: So, keep every payment. The payments program adds each one to the end of a file that only grows. Every payment
gets a number, its place in the file: 0, 1, 2, 3. The number never changes. Each reader remembers one thing: the
number of the next payment it wants. The ledger has read everything, so it's at 4. The fraud check is slower. It's
at 2. Map it out. The chat is the file. Each post is a payment. And each phone's place is one number for each
reader.

SCREEN: The same records return as a file with a dashed end slot; numbers 0 to 3 pop in. Bookmarks "ledger: 4"
(under the end slot) and "fraud check: 2". Captions "chat = the file", "post = payment", "you stopped here = one
number per reader".

## Scene 4 · Predict, then show · 1:38–2:07 · [PREDICT] [PAUSE] [SHOW]

VO: Now the fraud check reads two payments. What changes in the file? Pause and guess.

(three seconds)

Nothing. Its number moves from 2 to 4, and that's all. The records are still there for anyone else. A new payment
arrives. Account 42 gets a refund of 12.50. It goes at the end, as number 4. No reader moves. Both now have one more
to read. The ledger reads it, and moves to 5, the end.

SCREEN: Records 2 and 3 pulse green; countdown. The fraud check's bookmark steps 3, 4; the records pulse, unchanged.
The payments program appears and drops the refund into slot 4; a new dashed slot 5 appears; the ledger's bookmark
moves to 5.

## Scene 5 · Break the wrong model · 2:07–2:25 · [BREAK] [LOOP-PAYOFF]

VO: So, is a payment used up once it's read? The new program, the weekly report, starts at 0, the first payment of
all. Nobody else noticed. And the bug in yesterday's sums? Fix it, move the ledger's number back, and read again.
One number moved. Nothing copied.

SCREEN: Purple caption "used up once it's read?". The weekly report's bookmark appears under record 0; the others
pulse. The ledger's bookmark slides back to 0 and steps through 1 to 5. Caption "a second reading: move one number
back".

## Scene 6 · Where the chat breaks · 2:25–2:41 · [BREAK of the analogy]

VO: The chat picture breaks in two places. A chat may hide old posts from a new member. A log shows them to anyone.
And a chat lets you edit or delete a post, while a log never changes a record once it's written. To correct
something, you add a new record at the end.

SCREEN: The report's bookmark pulses; a red cross over record 3 comes and goes ("a record never changes once
written"); the refund at 4 pulses ("to correct something, add a new record").

## Scene 7 · The names · 2:41–3:10 · [NAME]

VO: This is called a log: an ordered list of records that only grows at the end. Each reader's number is its
position, the next record it will read. Kafka is a program that keeps logs like this on disk, and lets many programs
read them. In Kafka, each payment is a record. The program that adds them is a producer, and the readers are
consumers. And the log's name, payments, is a topic. Here a topic is one log; the next lesson splits it into many.

SCREEN: The heading becomes "a log", then "topic: payments"; captions for each name as its part pulses (records,
the payments program with its arrow, the bookmarks).

## Scene 8 · Two cautions · 3:10–3:31 · [GUARDRAIL]

VO: Two cautions. If reading deletes nothing, what does? Only a limit you set on each topic: how old, or how big, it
may get. By default, Kafka keeps seven days. And since every record stays, readable by any program allowed to read
the topic, never write anything you aren't allowed to keep for days, such as full card numbers.

SCREEN: Captions "only a limit per topic: how old, or how big", "default: seven days"; the records pulse red; "never
write what you can't keep for days: no full card numbers".

## Scene 9 · Moral and check · 3:31–4:06 · [JOKE:reward] [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: Leave a busy chat unread for a day, and the app still knows where you stopped. It saved one number for you. So:
one file you only add to, and a bookmark for each reader. Reading moves a bookmark. It never deletes.

One quick check. The weekly report reads three payments. Where is its number now, and what happened to the
ledger's? Pause and think.

(three seconds)

The report is at 3. The ledger hasn't moved. It's still at 5. Readers never touch each other.

SCREEN: "one number per reader", "one file you only add to, a bookmark for each reader", "reading moves a bookmark;
it never deletes". Countdown; the report's bookmark steps 1, 2, 3; the ledger's pulses at 5; the moral stays.



---

### Beat check

- Opens with QUESTION from the familiar chat (scene 1); PAIN and WISH from the queue the viewer met last lesson
  (scene 2).
- ANALOGY and MAP said out loud (scene 3), before any Kafka word.
- PREDICT with PAUSE (scene 4, and the check in scene 9), SHOW right after.
- BREAK: the "used up once read" model (scenes 4 and 5), the analogy's two limits (scene 6).
- NAME after the picture is built (scene 7). GUARDRAIL (scene 8) and MORAL (scene 9) last. Light moments: the
  shredding library (0:45), the chat that saved one number (3:31).

### Accuracy notes for the producer

- The records are the lesson's section 1 table: 0 acct-17 auth 40.00, 1 acct-42 auth 12.50, 2 acct-17 capture
  40.00, 3 acct-99 auth 300.00, 4 acct-42 refund 12.50. The video shows record 4 arriving live.
- The three costs, the four queues, the bug in yesterday's fee sums and the chat's two breaking points are the
  section's own. The readers' numbers are illustrative.
- "By default, Kafka keeps seven days" is section 3's `retention.ms` default; how deletion works (whole files) is the
  next lesson. "Never write full card numbers" is section 3's flip side.
- Left to later sections: offsets given by the broker (section 1), committed offsets and consumer groups (section 2),
  partitions beyond one (the next lesson). The video calls the number a position, as section 2 does.
- No code on screen: the section has none, and the producer and seek code belong to sections 1 and 2.
- Pronunciation: `SAY` rules say amounts as people do ("twelve fifty", "forty") and acct-42 as "account 42".
