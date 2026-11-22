# Initials on the order board: a Redis consumer group and its pending list

- Slug / scene: `redis-streams`, `videos/scenes/redis_streams.py:RedisStreams`
- Lesson: `msg-12`, section 2, "A consumer group shares the stream out and writes down every delivery"
- Audience / level: a complete newcomer. Can read a little code; doesn't know Redis, streams, consumer groups or
  acknowledgements.
- Length: 4:43 (~830 words of narration, plus two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=168` (after the restart: 1-1 and 1-2 back with w1, deliveries 2 in the PEL)
- The learner's real question: two workers share one stream. How does each payment go to exactly one of them, and if a
  worker dies holding one, how does anybody know?
- Misconceptions to steelman and break: (1) "a crashed worker's entries are lost", and (2) "Redis quietly gives them to
  someone else": both broken by the PEL keeping them under w1's name, and `>` never handing them out again; (3) "a Redis
  consumer group is a Kafka consumer group", broken in scene 8.
- Concept chain: called out once (pub/sub) → written down (a stream) → shared out once each (a consumer group, `>`) →
  every delivery written down (the PEL) → XACK crosses it off → a crash leaves entries pending → a restart reads its own
  with ID 0, count 2 → at-least-once, so settle idempotently (hardest last)
- Analogy family: the lesson's café. A drink called out once ("Flat white for Sam!"), the order board, each barista's
  initials next to the orders they took, a barista on a break with two orders still marked.
- Open loops: "how would anybody know?" planted in scene 1 → the PEL (scene 3) and the crash (scene 5); "if w1 never
  comes back" planted in scene 8 → claiming, the lesson's next section.
- Assumptions: commands and replies are the lesson's Try-it (IDs 1-1 to 1-4 with p-1 1250, p-2 4000, p-3 990, p-4 310;
  w1 and w2 COUNT 2; w2's third read `(nil)`; XPENDING 4 pending, 2 each; `XACK ... 1-3 1-4` → 2; w1's read with ID 0
  returns 1-1 and 1-2 and their count becomes 2). The Try-it's key is `settle`; the video uses the section's key
  `payments` with the same commands. 1-5 in the check is made up.

## The one picture

Top: the stream (the order board), entries 1-1 to 1-4 (blue, green once acknowledged), and the group box `settlers`
with "last handed out". Left: workers w1 and w2 (teal) with the entries they hold (gold chips). Right: the pending
entries list, a table of ID, owner and deliveries. Under them: the command line, as typed at `redis-cli`. Captions at the
bottom.

## Scene 1 · Called out, then written down · 0:00–0:55 · [FAMILIAR] [QUESTION] [LOOP-PLANT]

VO: A busy café calls out each drink when it's ready: flat white for Sam! At that moment Sam is washing his hands.
Nobody calls it twice. His coffee goes cold. Redis, a program that keeps its data in memory, has a tool that works like
that, pub/sub. And one that writes every message down, like an order board. It's called a stream. Here's the board for
paying shops. Four payments arrive, and Redis gives each an ID: 1-1, 1-2, 1-3, 1-4. Each night, workers settle each
payment: they add it to what the company owes that shop. Two workers, w1 and w2, share the board. Each payment must go
to exactly one of them. And if a worker dies holding a payment, how would anybody know? Hold that question.

## Scene 2 · The group · 0:55–1:30 · [ANALOGY] [NAME] [SHOW]

VO: In the café, the baristas share one board, and each writes their initials next to an order they take. In Redis,
that's a consumer group. Ours is called settlers. w1 asks for two entries with a greater-than sign, which means: never
handed to anyone in this group. It gets 1-1 and 1-2. w2 asks the same way, and gets 1-3 and 1-4. Each entry went to one
worker only.

## Scene 3 · The list of initials · 1:30–2:00 · [MAP] [NAME]

VO: Redis also writes down every delivery: the entry's ID, who has it, when it went out, and how many times it has been
delivered. That's the pending entries list, the PEL. Our initials on the board.

## Scene 4 · Predict · 2:00–2:35 · [PREDICT] [PAUSE] [SHOW]

VO: Now w2 asks again, with the greater-than sign. What does it get? Pause and guess.

(three seconds)

Nothing. Every entry has been handed out once, and the greater-than sign never hands one out twice. w2 settles its two
and says so with XACK. Redis crosses them off the list.

## Scene 5 · The crash · 2:35–3:15 · [BREAK] [JOKE:release] [LOOP-PAYOFF]

VO: Now w1 crashes, before its XACK. Are 1-1 and 1-2 lost? Or does Redis quietly give them to w2? Neither. They stay on
the list, under w1's name. Nothing is lost. It's only stuck. And the greater-than sign will never hand them out again,
because they were already delivered. In the café, a barista went on a break with two orders still marked with their
initials. Every other barista politely walks past them. That's manners, not a plan.

## Scene 6 · The restart · 3:15–3:45 · [SHOW]

VO: When w1 comes back, it reads its own pending entries first. It asks with the ID 0 instead of the greater-than sign,
and gets back the same two. Each one's delivery count goes to 2. When that read comes back empty, w1 switches back to the
greater-than sign.

## Scene 7 · At-least-once · 3:45–4:25 · [NAME] [GUARDRAIL]

VO: Notice what this means. Say w1 settled 1-1, then crashed before its XACK. After the restart it settles 1-1 again.
This is called at-least-once delivery: every entry is settled at least once, and now and then twice. So the settling must
be safe to run twice. Key it by the payment's id, and the second time finds the payment done. w1 settles both and sends
its XACK. The list is empty.

## Scene 8 · Two kinds of group · 4:25–5:05 · [GUARDRAIL] [LOOP-PLANT]

VO: Careful: Kafka has consumer groups too, and they share little more than the name. A Kafka group gives each partition
to one reader, with one bookmark. Order holds, and one stuck record holds up everything behind it. A Redis group keeps a
state for every entry, and hands entries to whoever asks. A slow one holds up nobody. The price: entries finish in any
order. And the question we're holding: if w1 never comes back, someone must take its entries over. That's called
claiming, and it's the next part of the lesson.

## Scene 9 · The code · 5:05–5:30 · [SHOW]

VO: Here's a worker's loop, in Java and in Kotlin, with Jedis, a library for talking to Redis. Read new entries through
the group, waiting up to two seconds. Settle each one, keyed by the payment, then XACK it. If settling fails, leave it
pending on purpose.

SCREEN: The lesson's settlement loop (compare block), Java left and Kotlin right, with the comments shortened.

## Scene 10 · The moral, and a check · 5:30–6:05 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So, how does each payment reach exactly one worker, and how do we know when a worker dies holding one? The group
hands each entry out once, and writes the worker's initials next to it until the worker says done. One quick check. w2
reads a new entry, 1-5, and crashes before its XACK. Then w3 joins and asks with the greater-than sign. Does w3 get 1-5?
Pause and think.

(three seconds)

No. 1-5 was already delivered, so it stays pending under w2, until w2 comes back for it, or someone claims it.

---

### Beat check

- FAMILIAR (the called-out flat white) and QUESTION (scene 1); ANALOGY + MAP (initials, scenes 2 and 3).
- PREDICT + PAUSE (scene 4, scene 10); BREAK: lost or quietly reassigned (scene 5).
- NAME after the picture: consumer group, PEL, XACK, at-least-once.
- GUARDRAIL: idempotent settling (scene 7), Redis vs Kafka groups (scene 8). MORAL and RECAP last.
- Light moments: "that's manners, not a plan"; the cold flat white at the start.

### Accuracy notes for the producer

- Commands and replies follow the lesson's Try-it, with the key `payments` (the section's name) in place of `settle`.
  The Try-it's `DEL` and the explicit IDs' meaning (`*` in real programs) are left out.
- Idle time is in the PEL but not drawn; it matters for claiming (the next section).
- "When it went out" is the PEL's delivery time; the video's table shows ID, owner and deliveries only.
- The code is the lesson's Jedis loop (compare block), with the read parameters pulled out into `params` and `fresh` (static imports assumed), the consumer name as `me`, and shorter comments. Lettuce and the coroutine caution are left out.
- In the check, w3 is drawn in w1's place on screen (w1 has finished), and 1-5 is a made-up entry.
