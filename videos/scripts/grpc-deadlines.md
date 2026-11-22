# How long should a call wait? A deadline that travels down the chain

- Slug / scene: `grpc-deadlines`, `videos/scenes/grpc_deadlines.py:GrpcDeadlines`
- Lesson: `enc-04`, section 2, "gRPC: a contract file, binary messages and a deadline on every call"
- Audience / level: a complete newcomer. Has written a function call; doesn't know what a network call, a thread,
  a header or gRPC is.
- Length: 5:11 (~800 words of narration)
- Poster: `POSTER=185` (the real run done: three lanes stopping together, the demo's five printed lines)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: when one program calls another and no answer comes, how long should it wait? And
  when it gives up, does the work on the far side stop too?
- Misconception to steelman and break: "payments set no deadline of its own, so the issuer has none and works its
  full 500 ms". Broken by the lesson's real run: the issuer's call arrives with 173 ms left and everyone stops at
  about 310 ms.
- Concept chain: a remote call can end in silence → gRPC waits forever unless told → a deadline bounds the wait →
  it travels as time remaining, so the next call knows what's left → when it runs out, every side stops (hardest
  last: why time remaining and not a clock time)
- Analogy family: a phone call to a bike shop. "I can hold for five minutes"; the clerk phones the warehouse and
  says "I need it within three minutes"; a careless clerk says nothing and the warehouse searches for a customer
  who hung up.
- Open loops: "does the far side stop too?" planted in scene 1 → paid off in scene 5; the careless clerk planted in
  scene 3 → paid off in scene 5 ("the library was the good clerk")
- Assumptions: all timings are the lesson's Try (`DeadlineDemo.kt` output: 299, 173, 311, 312, 321 ms; a 300 ms
  deadline, 120 ms of payments work, an issuer that needs 500 ms). The "627 ms" in the wrong model is 127 + 500.
  The bike-shop minutes are made up for the analogy.

## The one picture

Top row: three boxes, checkout (white), payments (blue), issuer (gold), joined by two arrows; a chip over each
arrow says what the call carries. Below: three lanes on a time axis from 0 to 650 ms, one per program. Grey means
waiting, blue payments' own work, gold the issuer working, red work for nobody. A dashed yellow line marks the
300 ms deadline. Under the axis: the demo's printed lines, one at a time. Captions at the bottom.

## Scene 1 · The question · 0:00–0:30 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: Picture buying a book online. You press Pay, and the shop's program asks another program, far away, to charge
your card. Then it waits. How long should it wait? And when it gives up, does the far side stop working too?

In your own code, a function call returns, or it throws, faster than you can blink. A call to another computer can
do a third thing: nothing at all. The question gets lost, or the answer does, and no reply ever comes.

SCREEN: Title card. Checkout box appears, an arrow, a dot leaves and stops halfway; a "?". Caption "a local call:
returns or throws"; "a remote call: returns, throws, or... nothing".

## Scene 2 · Waiting forever · 0:30–1:15 · [PAIN] [WISH] [JOKE:amplify]

VO: Let's give the programs names. Checkout is the shop's program. It calls payments, which calls the issuer, the
bank that gave the customer the card. They talk with gRPC, a free tool from Google that lets one program call a
function inside another program, over the network.

And here's the catch. gRPC sets no time limit unless you set one. So if a reply is lost, checkout waits forever.
While it waits, it holds a thread, one path of work in the program. Lose enough replies, and the shop runs out of
threads. Forever is a long time, even for a computer.

What we want is a rule: wait this long, and no longer. And when we stop waiting, everyone down the line should stop
too.

SCREEN: Payments and issuer boxes join with arrows. Caption "gRPC: one program calls a function in another, over
the network". A "no limit" chip; a grey waiting bar grows under checkout and keeps growing; little thread icons in
checkout fill up and turn red. Caption "wait this long, and no longer. Then everyone stops."

## Scene 3 · The bike shop · 1:15–2:00 · [ANALOGY] [MAP] [JOKE:is-the-explanation]

VO: Think of a phone call. You ring a bike shop and ask for a part. You say: I can hold for five minutes. The clerk
puts you on hold and phones the warehouse. A good clerk says: I need it within three minutes. Two minutes have gone
already, so three are left.

A careless clerk says nothing. So the warehouse climbs a ladder and searches for ten minutes, for a customer who
hung up long ago.

Let's map it. You are checkout. The clerk is payments. The warehouse is the issuer. And "I can hold for five
minutes" is the deadline: the moment after which the caller stops waiting.

SCREEN: Grey role labels under the boxes: "you", "the clerk", "the warehouse". Chip "I can hold 5 min" over the
first arrow; chip "within 3 min" over the second. Then the second chip turns into a red "(nothing)", and the
warehouse box shows "searching: 10 min" while "you" shows "hung up". Role labels then fade as the mapping is said.

## Scene 4 · The numbers, and a guess · 2:00–2:35 · [SHRINK] [PREDICT] [PAUSE]

VO: Now the real numbers, from the lesson's demo. Checkout calls payments with a deadline of 300 milliseconds.
Payments does 120 milliseconds of its own work, then calls the issuer, and sets no deadline of its own. The issuer
is slow today. It needs 500 milliseconds.

So when the issuer's call arrives, how much time does it see left? And who gives up first? Pause and guess.

SCREEN: The time axis and lanes draw in. Chip "deadline 300 ms" on the first arrow, "no deadline set" on the
second. Dashed deadline line at 300. Small labels: "120 ms of work" on payments, "needs 500 ms" on issuer.
Countdown bar.

## Scene 5 · The fair guess, then the real run · 2:35–3:35 · [BREAK] [SHOW] [LOOP-PAYOFF] [JOKE:release]

VO: The fair guess goes like this. Payments set no deadline, so the issuer has none. At 300, checkout gives up. But
the issuer works on until about 627. A third of a second of work for nobody, holding a thread the whole time. The
careless clerk.

Now the real run. Payments gets the call with 299 milliseconds left. At 127, the issuer gets its call, with 173
milliseconds left. Payments never set a deadline, and still the issuer knew.

At 311, checkout gets deadline exceeded. One millisecond later, payments' call to the issuer ends too. And at 321,
the issuer sees its call cancelled, and stops.

So the library was the good clerk all along.

SCREEN: Wrong model: lanes fill (grey, blue, gold), checkout's lane ends at 300 with a cross; the issuer's gold bar
runs on past the line, in red, to 627: "work for nobody". Then the lanes clear and the real run replays with the
demo's printed lines appearing below: "1 ms payments got pay-1, 299 ms left", "127 ms issuer got pay-1, 173 ms
left", "311 ms checkout gets DEADLINE_EXCEEDED", "312 ms payments issuer call ended", "321 ms issuer sees the
call cancelled, stops". Chips over the arrows change to "299 ms left" and "173 ms left". All three lanes end
together near the line.

NOTE: The light line comes only after the trace ends.

## Scene 6 · How it travels, and its name · 3:35–4:15 · [NAME] [BREAK]

VO: Here's how it travels. Every call carries headers, lines of extra detail sent with it. The deadline rides in
one named grpc-timeout, as time remaining, not as a time on the clock.

Why not send a clock time, like "stop at 12 o'clock and 300 milliseconds"? Because two machines' clocks never
agree exactly. "I can hold for five minutes" works whatever each watch says.

grpc-java, gRPC's library for Java and Kotlin, and its library for the Go language, pass the time that's left on to
the next call by themselves. When it runs out, the caller gets deadline exceeded, and the server's side of the call
is cancelled.

SCREEN: The second arrow's chip becomes "grpc-timeout: 173 ms". A purple "stop at 12:00:00.300" chip with two clocks that differ, crossed out. Caption
"time remaining, so the clocks don't have to agree".

## Scene 7 · In code · 4:15–4:35 · [SHOW]

VO: In code, it's one setting on the call: with deadline after, 300, milliseconds. And payments' own call to the
issuer needs nothing extra.

SCREEN: The demo's two lines, Kotlin:
    call(toPayments, charge, "pay-1", CallOptions.DEFAULT.withDeadlineAfter(300, TimeUnit.MILLISECONDS))
    call(toIssuer, authorize, request) // grpc-java passes the remaining deadline on by itself

## Scene 8 · Rules · 4:35–5:05 · [GUARDRAIL]

VO: Three rules. One: gRPC sets no deadline unless you do, so give every call one. Two: Java and Go pass it on for
you. With another library, check, and pass it on yourself if you have to. Three: deadline exceeded means nobody
knows what happened. The card may have been charged just before the end. So calling again isn't safe yet. Later in
this lesson, a retry gets a key, so it can't charge a card twice.

SCREEN: Three rule lines appear one by one in the caption area.

## Scene 9 · The moral, and a check · 5:05–5:40 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So how long should a call wait? As long as its caller can, and no longer. Give the first call a deadline. It
travels down the chain as time remaining, and when it runs out, everyone stops together. No warehouse searching for
a customer who hung up.

One quick check. Checkout sets 300 milliseconds again. This time, payments works for 250 before it calls the issuer.
About how much time does the issuer see left? Pause and think.

About 50 milliseconds. 300, minus the 250 already spent.

SCREEN: The real-run picture glows lane by lane. For the check: payments' blue bar stretches to 250; the second chip
shows "?"; countdown bar; the chip becomes "about 50 ms left".

---

### Beat check

- QUESTION (scene 1) from a felt situation; FAMILIAR (the local function call).
- PAIN and WISH (scene 2), ANALOGY with MAP said out loud (scene 3).
- PREDICT with PAUSE (scenes 4 and 9), SHOW right after each.
- BREAK: the fair guess run to its end (scene 5) and the clock-time idea (scene 6).
- NAME after the first SHOW: deadline (scene 3, from the analogy), grpc-timeout and DEADLINE_EXCEEDED (scene 6).
- GUARDRAIL (scene 8) and MORAL (scene 9) last. Light moments: forever for a computer, the warehouse up a ladder,
  the library as the good clerk, the closing callback.

### Accuracy notes for the producer

- Timings are the Try's output; the lesson says they vary by a few milliseconds from run to run.
- The wrong model's 627 ms is the issuer's start (127) plus its 500 ms of work; the lesson says it "would have spent
  its full 500 ms on an answer nobody was waiting for".
- On the wire, `grpc-timeout` is a number and a unit letter (`173m`); the picture writes "173 ms" for a newcomer.
- "Other libraries: check" is a hedge; the lesson only says grpc-java and grpc-go pass the deadline on.
- The check's "about 50 ms" ignores the few milliseconds the calls themselves take (the demo shows 7).
- Left to the lesson: the `.proto` contract, Protobuf, HTTP/2 streams, status codes beyond the deadline, retry
  policies and idempotency keys (section 4 and the worked example).
