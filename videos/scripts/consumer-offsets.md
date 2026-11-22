# Where does a restart start? Commit before or after the work

- Slug / scene: `consumer-offsets`, `videos/scenes/consumer_offsets.py:ConsumerOffsets`
- Lesson: `msg-07`, section 2, "Commit before or after the work: what a crash costs"
- Audience / level: a complete newcomer. Has met a partition's log and offsets; doesn't know what a consumer, a
  position or a committed offset is.
- Length: about 5 minutes (~880 words of narration plus two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: the `poster` stamp (consumer 2 skipped pay-05 and pay-06, the ledger reads 100.00, "right")
- The learner's real question: after a crash, where does the program pick up, and why did my balances come out wrong?
- Misconception to steelman and break: "a restart carries on where the crash stopped" (broken: the position was in
  memory); then the other team's fix, "commit first so nothing ever repeats" (broken: pay-07 to pay-09 lost forever).
- Concept chain: poll, process, commit → the finger (position) and the bookmark (committed offset) → process then
  commit: a crash repeats (at-least-once) → commit then process: a crash loses (at-most-once) → payments need
  at-least-once plus skipping seen ids; auto-commit's condition; why "exactly once" isn't two writes (hardest last)
- Analogy family: the lesson's long book read over many evenings. The finger is the position, the bookmark is the
  committed offset, nodding off is the crash. Moving the bookmark to the end of the chapter before reading it is
  commit-first. The closing's podcast app is the check.
- Open loops: "which two lines?" planted in scene 1 → answered in scene 9.
- Assumptions: all numbers are the lesson's stepper and Try it: pay-00 to pay-09 at offsets 0 to 9, 10.00 each for
  acct-1, batches of 5, crash while adding pay-07; 120.00 (20.00 too high), 70.00 (three lost), 100.00 with the ids
  checked.

## The one picture

Top: partition 0 of payments, ten cells pay-00 to pay-09 with offsets under them. A blue post and flag above the log is
the bookmark (later "committed"); a yellow pointer under the offsets is the finger (later "position"). Bottom left:
the consumer (gold), with a title and a state line. Bottom right: the ledger (green) with acct-1's balance and a note.
A yellow dot runs from a record to the ledger when it's added. Yellow cell outlines mark the batch the consumer holds;
green text is added once, red added twice or lost.

## Scene 1 · The Saturday crash · 0:00–0:40 · [QUESTION] [LOOP-PLANT]

VO: Picture the payments app on a busy Saturday. Every card payment goes into Kafka, a program that keeps a log of
messages and lets other programs read it. A second program, the ledger, reads each payment and adds it to the right
account's balance. At 11:02 the ledger crashes and restarts by itself. By Monday, one account is 20.00 too high: two
payments were added twice. Another team ran the same program with two lines swapped, and lost three payments instead.
Which two lines? Hold that question.

SCREEN: The ten payments drop into the log; the ledger box (0.00) and the reader box appear. "11:02: crashed,
restarted" in red; the balance shows 120.00, "should be 100.00: 20.00 too high", then 70.00, "three payments lost".

## Scene 2 · The loop · 0:40–1:05 · [FAMILIAR] [WISH]

VO: The ledger's reader is a consumer, and it runs a loop. Poll: ask Kafka for the next few payments. Process: add
each one. Commit: save how far you got. Repeat. A restart doesn't carry on where the crash stopped. Everything in
memory is gone. It carries on from the last place it wrote down. So when should it write that place down?

## Scene 3 · The book · 1:05–1:35 · [ANALOGY] [MAP] [NAME]

VO: Think of reading a long book over many evenings. Your finger marks the line you're reading now. A bookmark marks
where you'll start tomorrow. If you nod off, your finger slips, and only the bookmark is left. In Kafka, the finger is
the position: the next offset the consumer will read. It lives in memory. The bookmark is the committed offset. Kafka
saves it for the group, and it moves only when you commit.

SCREEN: The finger and the bookmark appear at 0; the finger slides down and fades, the bookmark pulses; their labels
become "position" and "committed".

## Scene 4 · The first batch · 1:35–2:05 · [SHRINK] [SHOW]

VO: Let's run it. Consumer 1 polls and gets offsets 0 to 4. The position jumps to 5 at once, before a single payment
is added. The committed offset is still 0. It adds pay-00 to pay-04 to the ledger. Then it commits 5: the next record
to read.

SCREEN: Cells 0 to 4 outlined yellow; position 5; five dots run to the ledger, 10.00 to 50.00; the bookmark moves to 5.

## Scene 5 · The crash, predicted · 2:05–2:55 · [PREDICT] [PAUSE] [SHOW] [NAME]

VO: Next poll: 5 to 9, and the position moves to 10. It adds pay-05 and pay-06, and dies while adding pay-07.
Consumer 2, a new copy of the program, takes over. Where does it start, and what happens to pay-05? Pause and guess.
(three seconds) It knows only what Kafka saved: committed offset 5. So pay-05 and pay-06, already in the ledger, arrive
a second time. Then the rest, and a commit of 10. The balance ends at 120.00. That's the Saturday bug: 20.00 too high.
Process, then commit, means every payment is processed at least once, and some twice. It's called at-least-once.

SCREEN: 60.00, 70.00; the consumer turns red "crashed at pay-07" and the position pointer slips away. "consumer 2";
countdown; the bookmark pulses; pay-05 and pay-06 turn red as they're added again (80.00, 90.00), then 100 to 120.00.

## Scene 6 · Swap the two lines · 2:55–3:45 · [BREAK] [NAME] [JOKE:amplify]

VO: So the other team thought: commit first, then nothing can ever repeat. Let's be fair and replay the second batch
their way. Consumer 1 polls 5 to 9 and commits 10 at once. It adds pay-05 and pay-06, and dies at pay-07. Consumer 2
starts at 10. pay-07, pay-08 and pay-09 are never added, and nothing will ever deliver them again. It's like moving
your bookmark to the end of the chapter before you read it. Nod off, and tomorrow you skip three pages, with no idea
what happened in them. That's at-most-once: each record processed at most once, and some never.

SCREEN: Reset to 50.00 with the bookmark at 5; the bookmark jumps to 10 before the work ("committed 10, before the
work", purple); crash at pay-07; consumer 2 starts at 10; pay-07 to pay-09 turn red; 70.00.

## Scene 7 · Which one, and the fine print · 3:45–4:45 · [GUARDRAIL] [SHOW]

VO: For payments, at-least-once is the only safe choice. A lost payment is a missing line that nobody notices. A
repeat can be spotted. Watch. Consumer 2 starts at 5 again, and the ledger skips any payment id it has already applied.
pay-05 and pay-06: skipped. The rest: added. 100.00. Two notes. By default, the consumer commits by itself every five
seconds, inside poll. That's at-least-once only if you finish each batch before the next poll. Hand the work to helper
threads, and it can commit payments nobody has added yet. And exactly once? The commit goes to Kafka, but the work
lands somewhere else, like a database. No order of two writes to two systems makes them one step. At-least-once, plus
work that ignores repeats, gets the same result.

SCREEN: The replay with ids checked ("pay-05, pay-06: seen, skipped"), ending at 100.00 "right" (green). Captions for
auto-commit, `enable.auto.commit=false`, and "at-least-once + ignore repeats = the effect lands once".

## Scene 8 · The code · 4:45–5:00 · [SHOW]

VO: In Java and Kotlin: turn auto-commit off, then in the loop, poll, do the work, and only then call commitSync.

SCREEN: Java and Kotlin panels: `enable.auto.commit` false, `poll(Duration.ofMillis(500))`, `ledger.apply(r)`,
`commitSync()`; the lines flash in turn.

## Scene 9 · The moral, and a check · 5:00–5:40 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So which two lines? Process and commit. Both teams had the same two lines, in a different order. Move the bookmark
after the work, give every payment an id, and a crash costs only a little reading twice. One quick check. You pause a
podcast, close the app at once, and open it on another device. It starts a few seconds early, so you hear them twice.
At-least-once, or at-most-once? Pause and think. (three seconds) At-least-once. Its bookmark was saved a little behind
where you were, so you hear a bit twice, and miss nothing.

---

### Beat check

- QUESTION (scene 1), FAMILIAR and WISH (scene 2), ANALOGY + MAP and the names (scene 3), SHOW (scene 4).
- PREDICT with PAUSE (scene 5, and the check), BREAK of the commit-first fix (scene 6).
- GUARDRAIL (scene 7), MORAL (scene 9). Light moments: skipping three pages (3:35), "Monday" in the hook.
- Open loop "which two lines?" paid off by name in scene 9.

### Accuracy notes for the producer

- Stepper and Try it numbers throughout; `max.poll.records` is 5 in the demo (500 by default).
- The dedupe replay is the stepper's last at-least-once frame; how the ledger stores ids (a unique constraint in the
  same database transaction) is the next section's.
- Auto-commit: every `auto.commit.interval.ms` (5 s), inside `poll` and in `close`; at-least-once only if each batch is
  finished before the next poll (KafkaConsumer docs, via the lesson). Coroutines are mentioned in the lesson; the video
  says "helper threads".
- Kafka transactions for topic-to-topic exactly-once are left to the later lesson.
- Amounts are spoken as whole numbers through a `SAY` rule; captions keep "20.00".
