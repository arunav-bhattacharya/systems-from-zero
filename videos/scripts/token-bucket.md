# A burst, then a steady rate: a jar of tokens that never needs a timer

- Slug / scene: `token-bucket`, `videos/scenes/token_bucket.py:TokenBucket`
- Lesson: `cache-08`, section 2, "A token bucket, or GCRA, allows a burst and then a steady rate"
- Audience / level: a complete newcomer. Has met a per-window count (5 a minute) in the lesson's first sections;
  doesn't know a token bucket, a Redis hash or GCRA.
- Length: 4:52 (~750 words of narration plus two pauses and the steady stream)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=171.1` (after the second burst: the full tally and "a token bucket")
- The learner's real question: a program that sends its refunds in one burst is honest; one that floods forever
  isn't. How can one limit tell them apart?
- Misconception to steelman and break: "a limit is a count per window" (it can't say "bursts fine, floods not"); and
  "something must drop a token in every 500 ms" (a timer per client), broken by the lazy refill.
- Concept chain: windows can't express a burst → a jar of 10 tokens, one more every 500 ms → predict: 15 at once gets
  10; one every 250 ms gets 10 of 20 → no timer: tokens and ts in a hash, earned when someone arrives → one script, TTL
  of 5 s → GCRA: one number, the same answers (hardest last)
- Analogy family: the lesson's jar of tokens on a counter (arcade tokens), with a lazy shopkeeper who tops it up only
  when someone walks in.
- Open loops: "one limit that lets the burst through and stops the flood?" planted in scene 1 → paid off in scene 8.
- Assumptions: all numbers are the lesson's (40 refunds in a second; 5 a minute, 40 a second; a burst of 10 and 2 a
  second; the demo's 15 / 20 / 15 traffic and its output 10, 10 of 20 `.+.+...`, 10; state `{tokens=0,
  ts=1762500010000}` and GCRA `1762500015000`; TTL just under 5 s). The clock on screen counts from the demo's t0 as 0.
  The check (2 quiet seconds, then 10 at once: 4 in) is worked out from the lesson's formula.

## The one picture

Left: the shop's refund program (purple). Middle: the jar (gold) of up to 10 tokens, "+1 token every 500 ms" under it.
Right: the payments service (blue) with the tally: the burst, the 20 marks (`+` in, `.` refused) and the second burst.
Under everything, the Redis hash line `bucket:merchant:m-17 tokens ts`, later the GCRA schedule. Green dots got in,
red ones were refused.

## Scene 1 · The question · [QUESTION] [LOOP-PLANT] [JOKE:pivot]

VO: Picture a shop's program that sends the hour's refunds all at once: 40 requests in one second, at the end of every
hour, and nothing in between. Is that an attack? No, just a program in a hurry. But a broken program that sends 40
every second, forever, is a problem. How do you write one limit that lets the first through and stops the second?

SCREEN: 40 white dots stream from the program to the service, "40 requests in 1 second", "then nothing for an hour";
then red floods for the broken program.

## Scene 2 · Windows can't say it · [FAMILIAR] [PAIN] [WISH]

VO: The limits so far count requests per window. A limit of 5 a minute refuses most of the burst. A limit of 40 a
second lets the broken program flood you, forever. One number per window can't say: bursts are fine, floods are not.
What we want sounds like this: a burst of up to 10, then 2 a second on average.

SCREEN: "5 a minute: 5 of 40 get in", "40 a second: the flood gets in" in red; the wish in yellow.

## Scene 3 · The jar · [ANALOGY] [MAP]

VO: Picture a jar of tokens on a counter, like tokens for an arcade. It holds at most 10, and gains one token every
500 milliseconds. Each request takes a token. If the jar is empty, the request is refused. Map it: a token is
permission for one request. The jar's size, 10, is the burst. One new token every 500 milliseconds is the rate: 2 a
second.

SCREEN: The jar fills with 10 tokens; one request takes a token and goes on; each mapping as a caption.

## Scene 4 · Predict, then the steady stream · [SHRINK] [PREDICT] [PAUSE] [SHOW]

VO: The program was quiet, so its jar is full. It sends 15 requests at once. How many get in? Pause and guess. Ten. It
spends the whole jar, and the last 5 find it empty. Now it sends one request every 250 milliseconds, for 5 seconds.
That's 20 requests. How many get in? Ten. A new token arrives every 500 milliseconds, so every second request finds
one. Refused, let in, refused, let in: 2 a second, exactly the rate.

SCREEN: Countdown; 15 dots: 10 take tokens and go on, 5 are refused with crosses; "burst of 15 at t = 0: 10 in". Then
20 requests while the clock steps by 250 ms and a token drops in every second step: the marks `.+.+...`, "10 of 20 got
in".

## Scene 5 · No timer · [BREAK] [ANALOGY] [SHOW] [NAME] [JOKE:skeptic]

VO: So who drops a token into the jar every 500 milliseconds? A timer for every client? With a million clients, that's
a million timers ticking for jars nobody is using. The trick is a lazy shopkeeper. He tops up the jar only when
someone walks in, by checking the clock. Store two numbers per client in a Redis hash, a small table of named fields
under one key: tokens, what was left after the last request, and ts, when the jar was last topped up. On each request,
work out the tokens earned since ts: the time gone by, divided by 500 milliseconds, rounded down. Add them, never
above 10, and take one. Watch it after 5 quiet seconds. Nothing moved while the program was quiet. Then a burst of 15
arrives. The time gone by is 5,000 milliseconds: 10 tokens earned, and the jar is full again. Ten get in. This is a
token bucket. The jar is the bucket.

SCREEN: "a timer per client?" in purple, "a million timers" in red; the refill label dims ("a lazy shopkeeper"). The
hash line glows; `earned = floor((now - ts) / 500)` and `tokens = min(10, tokens + earned)`. Clock 10,000 ms: the jar
fills at once, 10 of 15 get in, "burst after 5 quiet s: 10 in". "a token bucket".

## Scene 6 · Details, and GCRA · [GUARDRAIL] [NAME] [SHOW]

VO: Two details. The whole calculation runs as one script inside Redis, so two servers never both take the last token.
And the key gets a TTL of 5 seconds, the time to fill an empty jar. After 5 quiet seconds the jar would be full
anyway, so Redis may forget it. There's a version with only one number, called GCRA, the generic cell rate algorithm.
It keeps a schedule instead of a jar: the time the client's next request would be due, if it sent at exactly the
allowed rate. Each request that gets in pushes that time 500 milliseconds later. A request is refused if it would push
it more than 10 steps past now. In the lesson's demo, the bucket and GCRA got the same traffic, and agreed on every
single request. The bucket keeps two numbers, GCRA keeps one. When should you use one? When you want to cap how often
a customer's program calls your service, and still allow its bursts. For a small exact limit, like attempts per card,
the sliding log from earlier fits better.

SCREEN: One script, TTL 5 s (the hash line fades and returns). A schedule axis: "now", a yellow "next due" marker that
steps right 10 times, a red dashed limit at "now + 10 x 500 ms", the 11th step bounces with a cross. Captions with the
demo's two state lines; then when to use which.

## Scene 7 · The code, in Java and Kotlin · [SHOW]

VO: In Java and Kotlin, the call is the same: run the script on the client's key, with 10 tokens, 500 milliseconds,
and the time now. A 1 means let it in.

SCREEN: The worked example's `take` in Java and Kotlin side by side; the eval, the arguments and the `1` glow.

## Scene 8 · The moral, and a check · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, a burst, then a steady rate: the jar's size is the burst, and its refill is the rate. And the jar never needs
a timer. It only needs to remember how full it was, and when it last looked. One quick check. A program empties its
jar, then stays quiet for 2 seconds, and sends 10 requests at once. How many get in? Pause and think. Four. Two
seconds is 2,000 milliseconds: four tokens earned, so four get in, and six are refused. Next, the customer who pressed
Pay twice. A limit lets both presses through, so we'll learn to recognize a repeat.

SCREEN: Clock 12,000 ms; countdown; 4 tokens drop in ("2,000 ms / 500 ms = 4 tokens earned"); 4 of 10 get in.

---

### Beat check

- QUESTION (scene 1), FAMILIAR and PAIN (scene 2), WISH (scene 2), ANALOGY and MAP (scene 3).
- PREDICT with PAUSE (scene 4, the check in scene 8); the timer model broken (scene 5).
- NAME after SHOW: token bucket (scene 5), GCRA (scene 6).
- GUARDRAIL (scene 6: one script, TTL, when to use which), MORAL and the check (scene 8). Light moments: the program
  in a hurry (0:20), a million timers for jars nobody uses (2:30), the lazy shopkeeper (2:40).

### Accuracy notes for the producer

- Output is the lesson's `TokenBucketDemo`: both limiters print `burst of 15 at t = 0: 10   every 250 ms for 5 s: 10 of
  20 .+.+.+.+.+.+.+.+.+.+   burst after 5 quiet s: 10`; states `{tokens=0, ts=1762500010000}` and `1762500015000`.
- The clock shows milliseconds since the demo's pretend t0 (1,762,500,000,000).
- The lazy refill keeps the leftover part of an interval in `ts` (the worked example); the video shows only the
  whole-token formula.
- GCRA's refusal rule is "the new TAT more than 10 intervals past now"; the axis draws exactly that.
- The video names only the sliding log beside the bucket; the lesson's comparison also covers the fixed window and
  the sliding window counter.
- The jar "+1 every 500 ms" is the model; the script computes it on arrival, so nothing runs between requests.
