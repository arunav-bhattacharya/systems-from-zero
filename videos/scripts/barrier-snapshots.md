# A coloured card in each shoebox: snapshotting a program that never stops

- Slug / scene: `barrier-snapshots`, `videos/scenes/barrier_snapshots.py:BarrierSnapshots`
- Lesson: `stream-07`, section 1, "A snapshot of a running program, taken with markers in the stream"
- Audience / level: a complete newcomer. Knows a log of records with offsets and a count per card from earlier
  lessons; knows nothing about Flink, operators, channels, checkpoints or barriers.
- Length: about 5:08 (~830 words of narration, two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=197`, the aligned moment: both B1 barriers at the counter, "14 counted = 7 + 7", the snapshot on its way to storage
- The learner's real question: the program never stops, so how do you save its count and its place in the input
  at the same moment, without counting a payment twice after a crash?
- Misconception to steelman and break: (1) "stop everything, then save" (consistent, but the whole job stops for
  seconds at every checkpoint); (2) "save the moment the first marker arrives and keep reading" (the count then
  includes records after the saved offsets, and a restore counts them twice).
- Concept chain: a snapshot must be consistent (count and places describe one moment) → stopping works but costs
  seconds → a marker in each stream splits it into before and after → an operator with two inputs waits at the first
  marker (alignment) → the snapshot holds 14 = 7 + 7 → the sink commits at the checkpoint → after a crash, everything
  goes back to checkpoint 1 and each record's effect shows once (hardest last)
- Analogy family: the lesson's desk with two shoeboxes of receipts, a tally per card on a sheet, a note of the tally
  and how far you've got in each box, and a coloured card slipped into each box.
- Open loops: "how do you save a moment of a program that never stops?" planted in scene 1 → scene 6; "the email
  went twice" planted in scene 1 → scene 8.
- Assumptions: every number is the lesson's stepper (9 counted, 4 and 5; offsets 7 and 7; 13 counted at alignment;
  14 = 7 + 7; 17 counted and 3 uncommitted updates at the crash; the world sees 14) and its Try it (the rule "records
  counted = sum of the offsets", checkpoint 2 at [9, 7] with 16). The record chips' card labels follow the stepper.

## The one picture

Left: two sources stacked, each with its offset under it. From each, a channel runs right to a tall counter box with
two inputs; records are small blue chips, barriers are tall yellow bars marked B1, and the front of each queue is on
the right. From the counter, one channel runs to the sink, with "the world sees N updates" above it. Bottom right: the
durable checkpoint storage. In the analogy, the same places hold two gold shoeboxes, a tally sheet and a note card.
Red marks a blocked input and the crash. Captions at the bottom.

## Scene 1 · The email that went twice · 0:00–0:35 · [QUESTION] [LOOP-PLANT]

VO: Picture a small program that counts every card's payments. When a card has paid ten times, it emails the owner:
was this you? One busy Saturday its machine loses power. A minute later it's back, carrying on from where it last
wrote down. On Monday, a customer calls: she got the same email twice, and the counts show some payments twice too.
So how do you save the place of a program that never stops, so that nothing counts twice?

SCREEN: Title card. Two sources, a counter, a sink; records flowing; a red flash and "power lost"; "email sent: 2"
and a counter with a doubled payment. The question in white.

## Scene 2 · The desk · 0:35–1:20 · [FAMILIAR] [ANALOGY] [NAME]

VO: Picture yourself at a desk, counting receipts from two shoeboxes, with a tally per card on a sheet. Every so
often, you write a note: the tally, and how far you've got in each box. After an interruption, you start again from
the note. But the note only works if the tally and the two places describe the same moment. If the tally includes
five receipts the note says you haven't reached, you'll count those five twice. A snapshot like that, where every
record counted comes before the saved places and none after, is called consistent.

SCREEN: Two gold shoeboxes on the left, a tally sheet in the middle, a note card bottom right. Receipts move from the
boxes to the sheet. The note fills in: "tally, box A: 7, box B: 7". A red "5 counted twice" when the note lags the
tally. Caption "consistent: everything counted comes before the saved places".

## Scene 3 · Stop everything? · 1:20–1:45 · [PAIN] [WISH]

VO: The easy way is to stop. Stop reading both boxes, finish what's in your hands, write the note, start again. It's
consistent. But a real program does this every few seconds, and every time, everything stops. Wouldn't it be nice to
take the note while the counting goes on?

SCREEN: Red "stop" over both boxes; caption "consistent, and everything stops at every note". Then the yellow wish.

## Scene 4 · The program, named · 1:45–2:20 · [MAP] [NAME]

VO: Flink is a program that runs stream jobs across many machines. A job is a chain of steps called operators.
Sources read the input, here two Kafka logs of payments: those are the shoeboxes. A counter keeps the count per card:
that's the tally. A sink, the last step, writes results out to the world. Between two steps runs a channel, a queue
where records wait in the order they were sent. Every few seconds, Flink saves every operator's state and every
source's offset. That saved snapshot is called a checkpoint: the note.

SCREEN: The shoeboxes become source 0 and source 1 ("offset 7"), the sheet becomes the counter ("9 counted"), the note
becomes "checkpoint storage". Channels with record chips appear; the sink and "the world sees" appear.

## Scene 5 · A coloured card · 2:20–2:55 · [ANALOGY] [SHOW] [NAME]

VO: Here's the trick, from Chandy and Lamport in 1985. Slip a coloured card into each shoebox. Flink calls it a
barrier. It starts checkpoint 1: each source writes down its offset, 7 and 7, and puts barrier B1 into its channel,
behind the records it has already sent. Barriers never overtake records, so B1 splits each channel into before the
checkpoint and after it. And nothing stops. The sources keep reading.

SCREEN: Yellow B1 bars slide into both channels behind the chips; storage "checkpoint 1 started: offsets 7, 7".
Shading marks "before" right of each B1 and "after" left of it. New chips keep arriving.

## Scene 6 · The first card arrives · 2:55–3:50 · [PREDICT] [PAUSE] [BREAK] [SHOW] [NAME] [LOOP-PAYOFF]

VO: B1 reaches the counter on input 0 first. Input 1 still has a record ahead of its B1. Two new records from source
0 are queuing behind the barrier. Should the counter read them? Pause and guess.

(three seconds)

Let's steelman yes. Reading never stops, which is the whole point. But those two records come after offset 7. Count
them now, save, and after a crash the source rewinds to 7 and counts them again. That's the five receipts from the
desk. So the counter blocks input 0, and keeps reading input 1. At the desk, you reach the coloured card in box A, so
you stop taking from box A until you reach the card in box B. This waiting is called alignment. B1 arrives on input
1. The counter has counted exactly 14 records: 7 from each source, 7 plus 7, the offsets in the note. It saves its
state, sends one B1 on to the sink, and unblocks input 0.

SCREEN: B1 at input 0; two chips behind it; countdown. A ghost path shows the two chips going in and a red "counted
twice after a restore". Then input 0 turns red, "blocked"; input 1's last record goes in, "13 counted", then "14
counted = 7 + 7" as its B1 arrives. A dot carries the snapshot to storage; B1 moves on to the sink lane.

## Scene 7 · Commit, crash, restore · 3:50–4:40 · [SHOW] [PREDICT]

VO: B1 reaches the sink. The sink has held its 14 updates in an open transaction, a batch that nobody outside can see
until it's committed. Every operator has now saved its part, so checkpoint 1 is complete, and the sink commits. The
world sees 14 updates. Then the machine dies. The counter's 17, the channels and the sink's open batch are gone. The
3 updates after the checkpoint were never committed, so there's nothing to undo. Every operator loads checkpoint 1,
and each source rewinds to offset 7. Those records are read again, and since none were in the 14, each is counted
once. Records processed twice, effects shown once.

SCREEN: The sink box "open: 14 updates" → "committed"; "the world sees 14 updates"; the counter climbs to 17, offsets
10 and 9. Red crash: the counter, the channels and "open: 3 updates" vanish; the logs and storage stay. Restore: the
counter shows 14 "loaded", the offsets go back to 7 and 7, and chips flow again.

## Scene 8 · Names, and the limits · 4:40–5:15 · [NAME] [GUARDRAIL] [LOOP-PAYOFF]

VO: Flink calls all this asynchronous barrier snapshotting. Asynchronous because each operator writes its state to
storage in the background while processing goes on. Two limits. The desk picture breaks: you count alone and can
pause whenever you like, but Flink's operators run on different machines, so the barriers do the lining up. And
waiting at the coloured card is still waiting; the next section measures it. As for the email: it left the program
before the restore, and no snapshot can call it back.

SCREEN: Caption with the name; input 0's blocked stretch glows red as "waiting"; an envelope chip outside the sink
with "sent twice: outside the checkpoint".

## Scene 9 · The moral, and a check · 5:15–5:45 · [MORAL] [PREDICT] [PAUSE]

VO: So the moral of the story: a marker in every stream splits it into before and after, and a step with two inputs
waits for both markers before it saves. Then the count always equals the sum of the saved offsets. One quick check.
A checkpoint saved offsets 9 and 7. How many records does the counter's saved count hold? Pause and think.

(three seconds)

16. 9 plus 7.

SCREEN: Moral in yellow; caption "records counted = sum of the offsets". Storage shows "offsets 9, 7"; countdown;
"16 counted".

---

### Beat check

- QUESTION (scene 1); FAMILIAR and ANALOGY with the name "consistent" after the desk (scene 2).
- PAIN and WISH (scene 3); MAP and NAME (scene 4); the coloured card mapped to the barrier (scene 5).
- PREDICT with PAUSE twice (scenes 6 and 9); BREAK twice ("stop everything" in scene 3, "keep reading" in scene 6).
- SHOW: the walk, commit, crash and restore (scenes 5 to 7). GUARDRAIL and the analogy's breaking point (scene 8).
  MORAL and check (scene 9).

### Accuracy notes for the producer

- All counts are the lesson's stepper; "a record ahead of its B1" on input 1 and two records behind B1 on input 0 match
  its alignment frame (source 0 at offset 9, source 1 at offset 8, 13 counted).
- The sink in the stepper is transactional: it pre-commits at B1 and commits when the coordinator marks the checkpoint
  complete. The video says "holds its updates in an open transaction" and "commits".
- Chandy and Lamport (1985) also save in-flight messages as channel state; alignment keeps that empty, so Flink saves
  only operator state. The video leaves channel state out.
- The check uses the Try it's checkpoint 2 (offsets [9, 7], 16 counted).
- The opening's email is the lesson's; the video doesn't show the counting rule's code.
