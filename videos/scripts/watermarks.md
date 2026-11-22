# When is a minute's count final? Event time, watermarks and grace

- Slug / scene: `watermarks`, `videos/scenes/watermarks.py:Watermarks`
- Lesson: `stream-04`, section 2, "A watermark says when a window is complete enough"
- Audience / level: a complete newcomer. Has met events and logs; this lesson's earlier sections introduced event time
  and windows, so the video recaps both in one sentence each.
- Length: 4:21 (~780 words of narration, two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=148`, the `poster` stamp (the watermark at 70 s with its grace line, the first window "final: 61", "emitted: 0 to
  60 s = 61")
- The learner's real question: a stream never ends, so when can a program say "this minute's count is done"?
- Misconception to steelman and break: "close the window when the program's clock passes its end, plus 10 seconds"
  (a 60-second redeploy closes the next window with 0 before the backlog is read).
- Concept chain: windows need an end → the program's clock lies after a stop → two clocks → the latest postmark minus
  a few days → the watermark and grace → a straggler counted, a window final, a late event dropped → more grace keeps
  more, and delays everything → a guess, wrong two ways (hardest last)
- Analogy family: the lesson's postcards from a friend on holiday. The postmark is event time, the day it lands is
  processing time, adding up July is closing the window, "the latest postmark minus a few days" is the watermark minus
  grace, and the friend who never writes is the quiet input.
- Open loops: "when is the window 0 to 60 s complete?" planted in scene 1 → answered in scene 5 (at 70 s, with 61).
- Assumptions: shop m-7, one payment a second, the 10 s grace, the straggler from 59 s read at 65 s (count 61, final
  at 70 s), the second window final at 130 s with 60, the payment from 100 s dropped at 150 s, and "grace 10 s: two of
  three dropped; grace 60 s: one" are the lesson's stepper and Try it. The redeploy picture uses the lesson's 60 s
  stop, drawn as the window 60 to 120 s. The check (watermark 125 s, a payment from 115 s) is built from the same rule.

## The one picture

An event-time axis from 0 to 180 s along the middle; three one-minute windows above it (blue, green when final, red
when wrong) with their counts. A yellow strip on the axis is the events seen so far; a yellow vertical line is the
watermark, with a grey dashed line 10 s behind it for the grace. Stragglers drop in from above as gold dots (red when
dropped). "emitted" bottom left, "dropped as late" bottom right.

## Scene 1 · The question · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: A café chain's card payments flow into Kafka, a program that keeps a log of messages for other programs to read.
A counting program reads them, and counts the payments per minute for one shop, m-7. One payment a second, so every
minute should say sixty. The question is when to say it. When is the minute from 0 to 60 seconds complete?

SCREEN: The axis and three windows; the strip fills to 60 s, "count 60"; the question at the top.

## Scene 2 · By the program's clock · 0:30–1:15 · [FAMILIAR] [BREAK] [JOKE:release]

VO: The simple answer is the program's own clock. When it passes the minute's end, wait 10 more seconds for
stragglers, then send out the count. A straggler is an event that arrives later than its neighbours. That works until
the first redeploy. Stop the program for sixty seconds to install a new version. When it comes back, its clock says
that minute is over, so the window closes before it reads a single waiting payment. The count goes out as zero, and
the real payments arrive to find their window gone. A zero, sent with total confidence.

SCREEN: A "clock 70 s" line, "sent: 60". Then a grey "stopped: redeploy" band from 60 to 120 s, the clock jumps to
130 s, the second window "sent: 0" in red, and a pile of red waiting payments lands at 120 s.

## Scene 3 · Two clocks, and the postcards · 1:15–2:15 · [NAME] [ANALOGY] [MAP]

VO: The trouble is mixing two clocks. Event time is when the payment happened, stamped by the till. Processing time
is when our program reads it. A friend on holiday sends you a postcard a day, and you want to add up July. The post
is slow, and sometimes jumbled. So when do you add up July? Not when your calendar says August. When the latest
postmark you've received passes the end of July, minus a few days for slow post. Map it. The postmark is event time.
The latest postmark is how far the stream has got. The few days are your allowance for stragglers. And adding up July
is closing the window.

SCREEN: Captions for the two clocks. The diagram dims; postcards stamped 30 July, 31 July, 2 August, a gold 31 July
out of order, then 4 August; "latest postmark, minus a few days"; "4 August, minus three days, is past July". Mapping
captions one by one.

## Scene 4 · The watermark · 2:15–2:55 · [NAME]

VO: That latest postmark is called a watermark: the program's running claim, I believe no more events older than this
will arrive. Kafka Streams, a library for writing such counting programs, uses the largest event time seen so far,
and gives each window a grace period on top. When the watermark passes a window's end plus its grace, the window is
final, and its count goes out. Sending it on is called emitting.

SCREEN: The axis returns as "event time". The definition at the top. The strip and the watermark at 59 s with the
grace line; "count 60"; "grace here: 10 s"; "emitting: sending a final count on".

## Scene 5 · Watch it work · 2:55–3:50 · [SHOW] [LOOP-PAYOFF]

VO: Watch it with 10 seconds of grace. At 65 seconds, a straggler arrives that happened at 59. Its window is still
open, until 60 plus 10. So it's counted: 61. At 70, the window is final. 61 goes out, once, and the program forgets
it. That wait is the price: every result comes out 10 seconds later. The second window closes at 130, with 60. Then,
at 150, a payment from 100 seconds arrives. Its window is gone, and its count is out. So it's dropped as late, and the
late counter goes up.

SCREEN: The lesson's stepper: watermark 65 s, a gold dot "read at 65 s, happened at 59 s" falls into the first window,
"count 61"; watermark 70 s, "final: 61", "emitted: 0 to 60 s = 61"; watermark 130 s, "final: 60"; watermark 150 s, a
red dot from 100 s bounces off the closed window, "dropped as late: 1".

## Scene 6 · Predict the grace · 3:50–4:25 · [PREDICT] [PAUSE] [GUARDRAIL]

VO: Here's the lesson's test. Three stragglers arrive 5, 30 and 90 seconds after their windows end. With 10 seconds of
grace, two are dropped. With 60 seconds of grace, how many? Pause and guess.

(three seconds)

One. Only the one 90 seconds late. But now every window waits a whole minute before its count goes out. More grace
keeps more stragglers, and delays every result by the same amount.

SCREEN: Captions only, over the picture; countdown bar.

## Scene 7 · A guess, wrong two ways · 4:25–5:05 · [GUARDRAIL] [JOKE:soften]

VO: Remember, a watermark is a guess, and it can be wrong two ways. Too fast: an older event still arrives, from a
phone that was offline. That's a late event. Too slow: Flink, another engine, reads several inputs and takes the
smallest of their watermarks. One quiet input holds every window open. It's like refusing to add up July until every
friend has sent a card, including the one who never writes. So you mark a quiet input as idle, and it stops holding
things back.

SCREEN: "too fast" with the drop counter pulsing; "too slow" with every window's outline pulsing gold; "mark a quiet
input as idle".

## Scene 8 · The code, the moral, a check · 5:05–5:45 · [MORAL] [PREDICT] [PAUSE]

VO: In Kafka Streams, in Java and Kotlin, it's one line: one-minute windows, with 10 seconds of grace. So count by the
postmark, not by the letterbox. The watermark says when a count is final, and the grace says how long you wait for
stragglers.

One quick check. Grace is 10 seconds, and the watermark is at 125. A payment from 115 seconds arrives. Counted, or
dropped? Pause and think.

(three seconds)

Counted. Its window, 60 to 120, stays open until 130.

SCREEN: Java and Kotlin `windowedBy(TimeWindows.ofSizeAndGrace(Duration.ofMinutes(1), Duration.ofSeconds(10)))`
side by side. Then the moral as a caption. For the check: watermark 125 s; a gold dot from 115 s falls into the
second window, "count 61", a tick.

---

### Beat check

- Opens with QUESTION (scene 1). FAMILIAR is the program's clock, broken by the redeploy (scene 2).
- ANALOGY + MAP: the postcards (scene 3). NAME after it: watermark, grace, emitting (scene 4).
- SHOW: the stepper (scene 5). PREDICT with PAUSE: grace 60 s (scene 6) and the check (scene 8).
- GUARDRAIL: the grace trade-off (scene 6) and the two ways a watermark fails (scene 7). MORAL last (scene 8).
- Light moments: "a zero, sent with total confidence" (scene 2); the friend who never writes (scene 7).

### Accuracy notes for the producer

- Kafka Streams keeps one stream time per task (the largest timestamp seen) and closes a window when stream time
  reaches its end plus grace; the video calls that the watermark, as the lesson's stepper does.
- In the stepper, the window 0 to 60 s holds 60 at watermark 59 s; the straggler from 59 s read at 65 s makes it 61;
  it's final at 70 s. "count 6" and "count 11" for the second window at 65 s and 70 s are the stepper's.
- The Try it's stragglers are 5, 30 and 90 seconds past their windows; with grace 10 s two are dropped, with 60 s one,
  and every window waits 60 s.
- Flink's per-partition watermarks, the smallest-of-inputs rule and idle inputs are the lesson's; Spark and the
  Dataflow paper's four questions are left out.
- The redeploy in scene 2 is drawn on the same axis for the picture; the lesson's version is about processing time
  in general (all windows of the stopped minute close with zero).
