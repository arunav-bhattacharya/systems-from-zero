# Five seconds slow, a minute down: retry storms and the retry budget

- Slug / scene: `retry-storm`, `videos/scenes/retry_storm.py:RetryStorm`
- Lesson: `found-03`, section 3, "Retry storms: when trying again keeps the outage going"
- Audience / level: a complete newcomer. Knows "try again" from everyday life; knows nothing about servers,
  queues, timeouts or outages.
- Length: 5:04 (~790 words of narration at Kokoro's ~180 words a minute, plus two pauses and the builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=259` (after the last fix: the full scoreboard, the bin, goodput 880 a second)
- The learner's real question: the slowdown lasted five seconds, so why is the program still down a minute later?
  Isn't trying again the safe thing to do?
- Misconception to steelman and break: "retries are always safe, and if they hurt, wait longer between them". Broken
  twice: the storm outlives its trigger, and backoff with jitter never recovers, because every attempt still times
  out.
- Concept chain: a queue served in order → a slowdown makes waits longer than the timeout → every attempt times
  out and is sent again, so 800 requests become 3,200 attempts → the server answers clients that left (goodput
  zero) → the state keeps itself going (metastable failure) → backoff spreads retries but doesn't remove them → a
  retry budget caps them → dropping expired work makes every answer useful (hardest last)
- Analogy family: the lesson's coffee counter. Slips on a rail, a barista who works in order, customers who give
  up after three minutes and order again (leaving the first slip), a slow coffee machine, a café full of ghosts, a
  barista who throws away slips older than three minutes.
- Open loops: "what's keeping it down?" planted in scene 1 → answered in scene 9; "the rail stays full after the
  machine recovers" in scene 3 → the numbers in scene 5; the bin promised by "drop those too" in scene 7.
- Assumptions: all numbers are the lesson's lab simulation (`RetryStormDemo.kt`), which runs the same way every
  time. The café has no numbers. The t = 16 s readings in the shedding run are rounded to the lab's printed rows.

## The one picture

Left: the customers, later the clients (blue box). Middle: the rail of slips, later the queue; a slip is yellow while
someone waits for it and grey once its customer has left. Right: the barista, later the server (teal; red while
slow), with its speed. Arrows: customers → rail → barista. A red loop over the top carries reorders, later retries,
back to the customers. A grey path along the bottom carries drinks, later answers, back to the customers: a green
dot arrives, a red dot fades halfway because nobody is there. Readouts: the time (top left), attempts a second (on
the first arrow), queued (under the rail), goodput and wasted (bottom). Top right: a scoreboard of fixes and when
each run recovers. A small gold bin under the rail's front for the last fix.

## Scene 1 · The symptom · 0:00–0:25 · [QUESTION] [LOOP-PLANT] [JOKE:pivot]

VO: Here's a strange outage. A program slows down for five seconds, then gets its speed back. Yet a minute later,
it's still giving useful answers to nobody. The cause is long gone, so what's keeping it down? The culprit is the
most innocent habit in programming: trying again.

SCREEN: A small chart of useful answers a second against time (0 to 60 s). A red band from 10 to 15 s, "slow for 5
s". The green line drops from 800 to zero at 11 s and stays at zero, in red, to 60 s. Captions "the cause: gone
after 5 seconds. useful answers: still zero a minute later", then "the culprit: trying again".

## Scene 2 · The coffee counter · 0:25–1:05 · [FAMILIAR] [ANALOGY]

VO: Picture a coffee counter. Each order is a slip on a rail, and the barista makes drinks in the order the slips
sit there. On a normal morning she keeps up, and the rail stays almost empty. One more rule. A customer who has
waited three minutes gives up, goes back to the till and orders again. The first slip stays on the rail.

SCREEN: Customers, the rail, the barista and the drinks path draw in. Dots run: orders to the rail, slips to the
barista, green drinks back to the customers. The rail holds one slip. The red loop grows, "waited 3 minutes: order
again", and one red dot runs round it.

## Scene 3 · The slow machine · 1:05–1:45 · [PAIN] [SHOW] [JOKE:release]

VO: Now the coffee machine runs slowly for a few minutes. Slips pile up. People give up and order again, so the pile
grows even faster. Soon the barista is making drinks for people who have left. Then the machine recovers, and it
makes no difference. The reorders keep coming faster than she can work. She's busier than ever, serving a café full
of ghosts. So the slowdown is over, but the reorders keep the rail full.

SCREEN: The barista turns red, "slow machine". The rail fills; front slips go grey; red dots run round the loop.
Drinks now fade halfway along the bottom path (red). The barista turns teal again, but the loop keeps feeding the
rail. Captions "a café full of ghosts", then "the slowdown is over; the reorders keep the rail full".

NOTE: The ghosts are the light moment and the mechanism: work done for people who already left.

## Scene 4 · The program, with numbers · 1:45–2:30 · [MAP] [SHRINK]

VO: Programs do the same. The barista is the server, the program doing the work. The rail is its queue. The
customers are clients, programs that send it requests. Three minutes is the timeout, how long a client waits before
giving up. And ordering again is a retry.

Now with numbers. The server can finish 1,000 requests a second, and gets 800. So it's 80% busy, and answers in about
a millisecond. Clients give up on an attempt after 200 milliseconds and try again at once, up to 4 attempts in all.

SCREEN: Labels swap one by one as each is said: server, the queue, clients, "timed out after 200 ms: a
retry", answers. The clock shows t = 5 s; "800/s" on the first arrow; "queued: 0"; "goodput: 800 a second",
"wasted: 0 a second". Caption "each request: up to 4 attempts".

## Scene 5 · Predict, then watch · 2:30–3:40 · [PREDICT] [PAUSE] [SHOW] [NAME] [JOKE:release]

VO: At ten seconds in, something the server depends on slows down. For five seconds, it can finish only 400 a
second. Then it's back to 1,000. When does the service recover? Pause and guess.

(three seconds)

Let's watch. In a fifth of a second, 80 are queued: 200
milliseconds of work at this speed. So anything joining now times out before it's served. Every attempt times out,
so every request is sent four times. 800 new requests become 3,200 attempts a second. The server can't tell who's
still waiting. It works through the queue in order, and every answer goes to a client that already gave up.

At fifteen seconds, the server is back to full speed. It makes no difference. 3,200 attempts arrive each second,
more than three times what it can do. A minute in, 111,557 attempts are queued, and not one answer is useful.
Well... that was a long five seconds.

The rate of answers someone is still waiting for is called goodput. Here it's zero, and it stays zero. A trigger
pushed the system into a bad state, and its own behaviour keeps it there after the trigger is gone. That's called a
metastable failure. Getting out takes a strong push, like cutting the load or restarting.

SCREEN: Countdown bar. The clock steps t = 10 s, 10.2 s, 11 s, 16 s, 59 s, with the lab's readings: queued 80,
4,157, 16,957, 111,557; attempts 800/s then 3,200/s; goodput 400, then 0; wasted 0, 400, 1,000. Red dots stream round
the loop; slips at the front go grey; answers fade halfway. Captions name goodput and metastable failure.

## Scene 6 · The obvious fixes · 3:40–4:15 · [BREAK]

VO: So what fixes it? The obvious idea: wait longer before each retry, doubling the wait each time, with a random
part so clients don't retry in step. That's exponential backoff with jitter. To be fair, it spreads the retries out.
But every attempt still times out, so there are just as many. This run never recovers.

No retries at all? It recovers at 24 seconds. But then every everyday hiccup, like a dropped connection, becomes an
error.

SCREEN: The scoreboard starts: "retry up to 4, at once: never". A tag "wait, then double" sits on the loop. The
attempts readout wobbles 1,438/s, 3,063/s, 3,228/s. "backoff with jitter: never". The loop fades: "no retries at
all: 24 s". Caption "a dropped connection needs exactly one retry".

## Scene 7 · A budget, and the bin · 4:15–5:05 · [NAME] [SHOW] [LOOP-PAYOFF]

VO: A better rule is a retry budget: retries may add at most 10% to the work coming in. Now the server never gets
more than 880 a second. It recovers at 34 seconds. Slowly, because it still serves a backlog of attempts nobody is
waiting for.

So drop those too. Picture a barista who throws away slips older than three minutes. In a program, each request carries its
deadline, and the server drops attempts that are past it without working on them. Clients still retry four times.
During the slowdown, all 400 answers a second are now useful. And the moment the server is back to full speed, at
fifteen seconds, so is the service.

SCREEN: The loop returns with a green tag "budget: +10%"; "880/s"; "retry budget, 10%: 34 s"; queued 2,257 at t = 15 s,
then 457 at t = 30 s. The storm is set up again at t = 11 s; a gold bin appears under the front of the rail and the grey slips drop
into it. Readings from the lab's shedding run: attempts 2,000/s, queued 404, goodput 400; then t = 16 s, queued 0,
goodput 880. "retry up to 4, drop expired: 15 s".

## Scene 8 · A word of fairness · 5:05–5:25 · [GUARDRAIL] [BREAK of the analogy]

VO: So retries aren't the villain. The trouble is retries under overload.
And here the café picture breaks: a real customer reorders once and goes home. A program retries four times and
never gets tired.

SCREEN: Captions "the trouble: retries under overload", "a customer: reorders once, goes home", "a
program: retries four times, never tires", with four red dots round the loop.

## Scene 9 · The moral, and a check · 5:25–5:55 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So why was it still down a minute later? Its own clients kept it down, asking again for answers nobody would
wait for. Give retries a budget, and drop work nobody waits for.

One quick check. With a 10% budget and 800 new requests a second, what's the most the server is ever sent? Pause and
think.

(three seconds)

880 a second: the 800 new ones, plus 10% more.

SCREEN: The loop and the clients glow; "give retries a budget, and drop work nobody waits for"; the bin glows. For the
check, "?/s" on the first arrow and a countdown; then "880/s" and "880 a second: 800 new, plus 10%". The moral stays
on the last frame.

---

### Beat check

- Opens with QUESTION (scene 1) from a felt symptom (a short slowdown, a long outage).
- FAMILIAR + ANALOGY (scene 2) before any technical word; MAP said out loud (scene 4).
- PREDICT with PAUSE twice (when does it recover; the check); SHOW right after each.
- BREAK: the obvious fix (backoff) run to its end (scene 6), and the analogy's limit said out loud (scene 8).
- NAME after the SHOW: server, queue, clients, timeout, retry (scene 4), goodput and metastable failure (scene 5),
  exponential backoff with jitter (scene 6), retry budget (scene 7).
- GUARDRAIL (scene 8) and MORAL (scene 9) come last. Light moments: "the most innocent habit" (0:20), the café full
  of ghosts (1:35), "a long five seconds" (3:10).

### Accuracy notes for the producer

- Every number is from the lesson's lab run (`RetryStormDemo.kt`, deterministic): capacity 1,000 a second, 800 new
  requests a second, 200 ms timeout, up to 4 attempts, capacity 400 a second from t = 10 s to t = 15 s.
- Plain retries: attempts 3,200 a second; queued 80 at t = 10.2 s (from the stepper), 4,157 at t = 11 s, 16,957 at
  t = 16 s, 111,557 at t = 59 s; goodput 0 from t = 11 s; wasted 400 then 1,000 a second. Never recovers.
- Backoff with jitter: attempts 1,438, 3,063, 3,228 in seconds 10 to 12; never recovers. No retries: recovers at
  t = 24 s. Budget 10%: attempts 880 a second; queued 2,257 at t = 15 s and 457 at t = 30 s; recovers at t = 34 s.
- Dropping expired attempts with 4 retries: at t = 11 s attempts 2,000 a second, goodput 400, queued 404; at
  t = 16 s attempts 800, goodput 880, queued 0; recovers at t = 15 s.
- The chart in scene 1 is drawn from the plain-retries run (800, then 161 at t = 10, then 0).
- The "dropped connection needs exactly one retry" line refers to the lesson's earlier Try it.
- Left to the lesson: the Bronson (2021) and Huang (OSDI 2022) papers and the AWS outage counts, and how a real
  server learns a request's deadline.
- The slips on the rail are a picture of the queue, not to scale: at most twelve are drawn.
