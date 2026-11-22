# Four careful guards, and the money moved twice

- Slug / scene: `end-to-end`, `videos/scenes/end_to_end.py:EndToEnd`
- Lesson: `derive-03`, section 2, "Every layer's exactly-once stops at its own edge"
- Audience / level: a complete newcomer. Has used a banking app; doesn't know TCP, Kafka, a producer, an offset or a
  unique constraint.
- Length: 4:50 (~880 words at Kokoro's ~175 words a minute, plus a pause and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=246`, the lab table with all four rows (103, 78, 47, 0) under the path, every guard badge lit
- The learner's real question: every layer on the way promises "exactly once". So how did one tap move 90.00?
- Misconception to steelman and break: "a stack of exactly-once layers adds up to exactly once overall" (the lesson's
  warm-up trap), broken by the lost answer and the consumer crash, which pass every guard.
- Concept chain: the path of a transfer → four faults, one per hop → each guard catches its own fault → the retry and
  the redelivery look new to every layer (hardest) → only the ends know: one id from the tap, checked at the ledger
- Analogy family: a posted present. Every depot scans parcels so none goes through twice; you hear nothing for a week
  and post a second, identical present; every depot sees a new parcel. Only you and your friend know it's the same
  gift, so you write a reference number on it and your friend keeps a list.
- Open loops: "how did one tap move 90.00?" planted in scene 1 → answered in scene 5; the reference number on the
  parcel in scene 3 → paid off as `req-7f3a` in scene 6.
- Assumptions: the path, the faults and the numbers are the lesson's (45.00, 80 ms, 10 seconds, 90.00; 1,000 transfers;
  103, 78, 47, 0 duplicate rows; 53,025.23 extra; `req-7f3a`). The parcel analogy is invented for the video; the
  lesson has none for this section.

## The one picture

Five boxes in a row across the middle: phone, API server, broker (the Kafka log), consumer, ledger (PostgreSQL), joined
by arrows. Under each hop, the guard that lives there (TCP, idempotent producer, exactly-once mode, one transaction),
grey until it acts, green when it catches its fault, red-outlined when a fault slips past. Gold request tokens travel
the arrows; ledger rows stack above the ledger box. Bottom: the lab's table fills in row by row. Captions at the
bottom.

## Scene 1 · One tap, 90.00 · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: You're on a train, sending 45.00 to a friend from your banking app. You tap send, and the train enters a tunnel.
Ten seconds later, the app sends the request again. Out of the tunnel, your balance is 90.00 lower. And here's the odd
part. Every layer on the way promises to handle each thing exactly once. So how did one tap move the money twice?
Hold that question.

SCREEN: Title card. The phone box, a gold "45.00" token; a tunnel shading; a second token; the ledger with two rows
and a red "-90.00"; a "?".

## Scene 2 · The path · 0:30–1:05 · [FAMILIAR]

VO: Here's the path. The phone sends the request over TCP, the rules that carry bytes between two machines, to the API
server, the bank's program that takes requests from apps. The server writes a record to Kafka, a log that the next
program reads. The program that keeps that log is called the broker. Then a consumer reads the record, and adds a row
to the ledger, the bank's list of every movement of money, kept in PostgreSQL, a database.

SCREEN: The five boxes appear one by one with their arrows; a token travels the whole path; one ledger row lands.

## Scene 3 · A posted present · 1:05–1:40 · [ANALOGY] [MAP]

VO: Picture posting a present to a friend. Every depot on the way scans each parcel, so nothing goes through twice. A
week passes, no word, so you post a second one, the same present. Every depot scans it happily. New parcel, new
label. Only you and your friend know they're the same gift. Map it. You're the phone. The parcel is the request. The
depots are the layers, and each scan is a guard. Keep the second parcel in mind.

SCREEN: Captions for the story; on "map it", the phone, a token, the middle boxes and the guard badges glow in turn.

## Scene 4 · Each guard, and its edge · 1:40–3:05 · [SHOW] [PREDICT] [PAUSE] [BREAK] [NAME]

VO: Now the faults, one per hop, and the guard that lives there. One: a packet is sent again although the first copy
arrived. TCP numbers every byte on a connection and drops bytes it has already delivered. That one is caught. Two: the broker adds
the record, but its "got it" is lost, so the server sends it again, with the same sequence number. The idempotent
producer lets the broker spot the repeat and add nothing. That one is caught too. Idempotent means safe to repeat.

Now the train. The server saved the transfer, 80 milliseconds after the tap, and the answer died in the tunnel. Ten
seconds later, the phone sends again. Which guard catches this one? Pause and guess.

(three seconds)

None of them. The retry comes on a new connection, and TCP's numbers start fresh. The server sends a new record, which
gets a new sequence number. Every guard sees a new, perfectly good transfer. Second row. 90.00 gone.

One more. The consumer writes the row, then dies before it saves how far it has read, its offset. On restart, it gets
the record again. Kafka's exactly-once mode saves offsets and Kafka writes together, but the ledger lives in
PostgreSQL, outside it. And the database runs each insert as a fine new transaction. So each guard is right, but only
inside its own layer. Each one's exactly-once stops at its own edge.

SCREEN: A red spark on each hop as its fault fires; badges turn green ("caught") for faults one and two. For the train:
countdown, then a second token passes the TCP and producer badges, both outlined red, and a second ledger row lands
with "-90.00". For the crash, a red cross on the consumer, a token from the broker again, a third row, the exactly-once
badge outlined red. Caption "each guard's exactly-once stops at its own edge".

## Scene 5 · The lab's count · 3:05–3:40 · [SHOW] [JOKE:release] [LOOP-PAYOFF]

VO: The lab measures it. 1,000 transfers, the same faults, each guard switched on in turn. With none, the ledger gets
103 extra rows, and 53,025.23 moves that nobody asked to move. TCP's guard brings it to 78. The idempotent producer, to
47. Four careful guards, and every one of them would pass an audit. The 47 left are lost answers and consumer crashes.
They happen above every layer: one in the phone's retry, one in the gap between two systems.

SCREEN: The lab table fills: "no guards 103, 53,025.23", "+ TCP 78", "+ idempotent producer 47"; a red outline around
the 47.

## Scene 6 · One id, from the tap · 3:40–4:25 · [SHOW] [LOOP-PAYOFF of the parcel]

VO: Back to the present. You write a reference number on it, and your friend keeps a list. Here, only the phone knows
that two requests are one transfer. So it makes an id when you tap, req-7f3a, and sends the same id on every attempt.
It rides in a header on the request, then a header on the Kafka record, all the way to the ledger. There, the insert
says: if this id is already here, do nothing. And the money moves only if a row went in. The retry: nothing. The
redelivery: nothing. And the lab's last line: 0.

SCREEN: A gold id chip "req-7f3a" on the phone, riding each arrow; a new "request id, unique" badge under the ledger;
the extra rows fade; replayed retry and redelivery each bounce with a green "already here". The table's last row
"+ request id at the ledger 0".

## Scene 7 · The guardrail and the moral · 4:25–5:00 · [GUARDRAIL] [MORAL] [PREDICT] [PAUSE]

VO: So are the lower guards useless? No. TCP's resending saves you from redoing a whole transfer for every lost packet.
Lower layers make the common case fast. Correctness is checked at the ends. And make the id once per tap. A fresh id
on every attempt is a fresh transfer every time.

One quick check. Kafka's exactly-once mode is on, and there's no request id. The consumer dies after the insert,
before saving its offset. One row, or two? Pause and think.

(three seconds)

Two. The ledger's save happened outside Kafka, so only an id checked at the ledger stops it.

SCREEN: Captions "lower layers make the common case fast" and "correctness is checked at the ends"; "one id per tap,
not per attempt". For the check, the request-id badge greys out, the consumer crashes, a second row lands.

---

### Beat check

- QUESTION (scene 1) from the lesson's train; FAMILIAR (scene 2), each product named after a plain sentence.
- ANALOGY + MAP (scene 3), paid off in scene 6.
- PREDICT with PAUSE in scene 4 and the check in scene 7; SHOW after each.
- BREAK: the stacked exactly-once model (scene 4), counted in scene 5.
- NAME after SHOW: idempotent, offset, "exactly-once stops at its own edge".
- GUARDRAIL and MORAL last. Light moments: "every depot scans it happily" (about 1:20), "every one of them would
  pass an audit" (about 3:30).

### Accuracy notes for the producer

- The four faults and guards are the lesson's lab: a repeated packet (TCP), a lost broker acknowledgement (the
  idempotent producer), a lost answer and a retry on a new connection (nothing below the app), a consumer crash
  between the insert and the offset (Kafka's EOS covers only Kafka writes).
- Lab numbers with seed 2026: NONE 103 rows and 53,025.23; TRANSPORT 78; BROKER 47; END_TO_END 0. Other seeds change
  the counts, not the shape; END_TO_END is 0 for every seed.
- "If this id is already here, do nothing" is `INSERT ... ON CONFLICT (request_id) DO NOTHING`, with the money moved in
  the same transaction only if a row went in. The header is `Idempotency-Key`.
- The parcel analogy is the video's own; the lesson's analogy for the principle is the 1984 file-copy example, left
  to the lesson. Temporal and durable execution are left to the lesson.
- Where the parcel breaks: real posts don't scan for duplicates the way TCP does; the picture only carries "each check
  sees its own copies".
