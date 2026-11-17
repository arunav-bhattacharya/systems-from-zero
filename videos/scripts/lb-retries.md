# Try again, but safely and at random

- Slug / scene: `lb-retries`, `videos/scenes/lb_retries.py:LbRetries`
- Lesson: `net-12`, section 2, "Trying again: retries help only when they're safe and spread out"
- Audience / level: a complete newcomer. Knows the lesson's opening (a café whose first card payment fails and
  works on the second tap); knows nothing about HTTP methods, timeouts or load.
- Length: 4:38 (~720 words of narration, plus the guesses and silent builds)
- Poster: `POSTER=219` (the jitter chart over the dimmed in-step spikes: 1,000 of 1,000 answered by 1.13 s)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: a second tap fixed it, so why shouldn't the app retry every failed payment, and
  how should it wait?
- Misconceptions to steelman and break: (1) "a failed payment wasn't made, so retrying is harmless" (broken: the
  answer was lost after the bank approved, and the retry charges twice); (2) "backoff spreads the retries out"
  (broken by the lesson's simulation: every client counts the same waits, so the rounds still land together and
  only 400 of 1,000 cafés get an answer)
- Concept chain: a timeout means maybe → sort failures by what they tell you (never sent, maybe arrived, an
  answer) → idempotent, and the idempotency key → a thousand clients retrying in step → full jitter → retries
  multiply, so budget them and retry at one layer
- Analogy family: phoning a restaurant to book a table (the three failures, the booking number); a radio call-in
  line where everyone redials on the same beat (the retry storm)
- Open loops: "two questions spoil the plan" planted in scene 1 → the first answered in scenes 2 to 4, the second in
  scenes 5 to 7; "try every failed payment again?" asked in scene 1 → answered in scene 9
- Assumptions: amounts and the key number (4.50, key 812) are made up for the picture; every storm number is the
  lesson's `Jitter.java` with its fixed seed (per-10 ms arrivals were printed from the same code)

## The one picture

Top: the café's app (blue box) and the bank (green box), with a wire between them; messages are small cards that
run along the wire, and a red cross marks a lost one. Under each box, a state line (timeout, charges: 1, key 812).
Middle: three boxes sort the failures (green, yellow, red), later folded into a one-line summary under the actors.
Bottom: the storm chart, requests reaching the bank in each 10 ms, with the bank's limit (100) as a green dashed
line and the 250 ms it was down shaded red; red bars are refused requests, green (or teal with jitter) answered.

## Scene 1 · Tap again · 0:00–0:30 · [FAMILIAR] [QUESTION] [LOOP-PLANT]

VO: At a café, the card reader shows an error message. The cashier asks you to tap again, and this time it works. So why
not let the app do that for you, and try every failed payment again? Many careful teams do exactly that. Two
questions spoil the plan. Was the first payment really not made? And what happens when a thousand apps try again
at the same moment?

SCREEN: Title card. The app shows "error"; the wire and the bank appear; "pay 4.50" crosses; "approved". Captions
for the two questions.

## Scene 2 · One coffee, two charges · 0:30–1:10 · [PAIN] [WISH]

VO: Start with one payment. The app sends it, and the bank approves it. Then the answer gets lost on the way back.
The app waited, and nothing came. That's a timeout. So it tries again, and the bank, seeing a perfectly good
payment, approves it again. One coffee, two charges. And never trying again isn't safe either, because some
payments would never go through. We need to know which failures are safe to try again.

SCREEN: "pay 4.50" crosses; the bank's state "charges: 1"; "approved" sets off back and falls off the wire with a
red cross; the app's state "timeout"; "pay 4.50" again; "charges: 2" in red.

## Scene 3 · Booking a table by phone · 1:10–2:05 · [ANALOGY] [MAP]

VO: Think of booking a table by phone. Three things can go wrong. One, the call never connects. Nobody heard you,
so calling again is always safe. Two, you say, a table for four at eight, and the line drops. Did they write it
down? You can't tell. Calling again might get you two tables. Three, they answer: sorry, we're full. Calling
again gets the same answer. Now map it. A call that never connects is a request that never left: the connection
was refused, or connecting timed out. A dropped line after you spoke is a reset or a read timeout: the request
may have arrived. And sorry, we're full, is an answer, like an error 400 or 500. The same request gets it again.

SCREEN: The actors become "you, on the phone" and "the restaurant". Three boxes fill in: "1. the call never
connects / call again: safe" (green), "2. you order, then the line drops / call again: two tables?" (yellow), "3.
they answer: sorry, we're full / call again: same answer" (red). On "map it" the actors come back and each box
turns into "never sent / retry: always safe", "sent, maybe arrived / retry: only if idempotent", "an answer came
back / retry: no, same answer".

## Scene 4 · Idempotent, and the key · 2:05–2:50 · [NAME] [SHOW] [BREAK of the analogy]

VO: The middle case is the hard one. It's safe only if doing the thing twice has the same effect as doing it
once. That's called idempotent. Reading a payment's status twice is fine. Approving a payment twice is not, unless
the app sends an idempotency key: a unique id for this payment. The bank stores the result under it, and a repeat
with the same key gets the first result back. Like giving the restaurant a booking number. A person might
recognise your voice; the bank's program needs the number.

SCREEN: The middle box glows, the others dim. "pay 4.50 key 812" crosses; "key 812: 1 charge"; the answer is lost;
the same card crosses again; "approved (key 812)" comes back; "key 812 again: still 1 charge" in green.

NOTE: Where the phone picture breaks is said out loud: a person deduplicates by voice, a program only by the key.

## Scene 5 · A thousand cafés · 2:50–3:30 · [SHRINK] [PREDICT] [PAUSE]

VO: Now the second question. Picture 1,000 cafés, and the bank's program restarts. For 250 milliseconds, every
payment fails. After that, the bank can answer 100 requests in each 10 milliseconds. Every app tries again, and
waits longer each time: 100 milliseconds, then 200, 400, 800, at most a second, and six tries in all. That's
called exponential backoff. How many of the 1,000 cafés get an answer? Pause and guess. (three seconds)

SCREEN: The boxes fold into one line: "never sent: retry · maybe arrived: only if idempotent · an answer: don't
retry". The app becomes a stack, "1,000 cafés' apps". The chart's axes, the red "bank down" band, the green
dashed limit "the bank's limit: 100 per 10 ms". Countdown bar.

## Scene 6 · In step · 3:30–4:05 · [SHOW] [BREAK]

VO: Only 400. Look at the arrivals. Every app works out the same waits, so each round of retries lands in the same
10 milliseconds: a thousand requests where a hundred fit. A hundred get through, and the rest fail together and
come back together. After six tries, 600 cafés give up, and the bank saw 5,400 requests.

SCREEN: Six spikes grow at 0, 100, 300, 700, 1,500 and 2,500 ms (1,000, 1,000, 1,000, 900, 800, 700), red with a
green foot of 100 once the bank is back. "400 of 1,000 answered, 5,400 requests".

## Scene 7 · Stop agreeing · 4:05–4:45 · [ANALOGY] [JOKE:is-the-explanation] [NAME] [SHOW]

VO: It's like a radio call-in show where everyone who hears the busy tone redials after exactly ten seconds. The
line is jammed again, every time. Everyone is so punctual. The fix is to stop agreeing. Each app waits a random
time, between zero and its current limit. That's called full jitter. Same bank, same 1,000 cafés. The retries
spread out, never more than 155 in any 10 milliseconds. Every café gets an answer within about 1.1 seconds, with
fewer requests in all.

SCREEN: The spikes pulse red, then fade. The jitter histogram grows: a tall first bar (the 1,000 first tries) and a
low spread of retries, teal under the limit once the bank is back. "1,000 of 1,000 answered by 1.13 s, 4,194
requests".

## Scene 8 · Retries multiply · 4:45–5:20 · [GUARDRAIL]

VO: One more trap: retries multiply. If a request passes through three programs, each calling the next, and each
one tries three times, one request becomes 27 at the bottom, right when the bottom is struggling. So keep a retry
budget: retries may add at most about 10 percent to what you send, and once it's spent, failures go straight
back. And retry at one layer only, the one closest to the user.

SCREEN: "1 request → 3 → 9 → 27", each arrow "× 3". Captions for the budget; the last two steps dim on "retry at
one layer".

## Scene 9 · The moral, and a check · 5:20–5:55 · [MORAL] [RECAP] [PRINCIPLE] [PREDICT] [PAUSE] [LOOP-PAYOFF]

VO: So, should the app try every failed payment again? Only when it's safe: never sent, or idempotent. At a random
time. From one place. One quick check. The app asks the bank for a payment's status, a request that only reads,
and the read times out. Try again or not? Pause and think. (three seconds) Try again. Reading twice changes
nothing, so it's idempotent. Wait a random time first.

SCREEN: The summary line's first two parts pulse. "GET status" crosses, its answer is lost; "read timeout". After
the countdown, the middle part pulses and "random wait, then retry" shows under the app as the request goes again.

---

### Beat check

- Opens with FAMILIAR (the second tap) and the QUESTION, split into two questions that the video answers in order.
- PAIN + WISH (scene 2), ANALOGY + MAP (scene 3) with every part mapped, its break said in scene 4.
- NAME after the picture: timeout (scene 2), idempotent and idempotency key (scene 4), exponential backoff (scene
  5), full jitter (scene 7), retry budget (scene 8).
- PREDICT with PAUSE: scene 5 and the check in scene 9. BREAK: the double charge (scene 2) and backoff in step
  (scene 6).
- GUARDRAIL (scene 8) and MORAL (scene 9) last. Light moments: "one coffee, two charges", "everyone is so
  punctual", "a person might recognise your voice".

### Accuracy notes for the producer

- The storm is the lesson's `Jitter.java`: 1,000 clients, the bank down until 250 ms, then 100 answers per 10 ms;
  waits of min(1 s, 100 ms × 2^n), six attempts. Without jitter: 400 answered, 5,400 requests, rounds of 1,000 in
  one 10 ms slot. With full jitter: 1,000 answered, the last at 1,128 ms, 4,194 requests, at most 155 retries in a
  10 ms slot. The chart's per-10 ms bars were printed by the same code (fixed seed 42); the tall first bar with
  jitter is the 1,000 first tries plus 76 early retries.
- "Connection refused, connecting timed out" are the never-sent failures; "a reset, a read timeout" may have
  arrived; 400 and 500 errors come back the same. GET, HEAD, OPTIONS, TRACE, PUT and DELETE are idempotent by RFC
  9110; POST is not without an idempotency key. The video says only "reading" and "approving".
- The idempotency key 812 and the amount 4.50 are made up for the picture.
- The lesson's load-balancer, timeouts and idle-pool sections are left to the lesson; this video stays on its
  section 2.
