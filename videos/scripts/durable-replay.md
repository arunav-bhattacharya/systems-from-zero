# The program forgot your order. How does it carry on? Write down every step, then replay

- Slug / scene: `durable-replay`, `videos/scenes/durable_replay.py:DurableReplay`
- Lesson: `enc-05`, section 2, "Durable execution: write down every step, then replay the code"
- Audience / level: a complete newcomer. Can read a few lines of code; doesn't know what a worker, a server, an
  event history or Temporal is.
- Length: 5:14 (~850 words of narration)
- Poster: `POSTER=218` (replay done: eight events, SHIPPED green, "cards charged: 1", the demo's line)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: the program's computer restarted halfway through an order and it forgot everything.
  How can a program carry on from where it stopped, without doing the finished steps again?
- Misconception to steelman and break: "after a crash, run the order again from the top". Broken on screen: the
  bank charges the card a second time. Then replay *also* runs from the top, and the contrast is the lesson: a
  finished step reads its answer from the history instead of doing the work.
- Concept chain: memory dies with the program → run-from-the-top pays twice → write each finished step down
  outside the program → a new worker reads the code from the top with the notes open (replay) → real work starts at
  the first step with no note (hardest last: the gap between doing a step and writing it down)
- Analogy family: the lesson's own. A shop with workers on shifts, an instruction sheet for each order and a
  notebook beside it. The next worker reads the sheet from the top with the notebook open, skips what's written,
  uses the results written there, and starts at the first step with no entry.
- Open loops: "run it from the top" planted and broken in scene 2 → paid off in scene 7 ("from the top? that's the
  fix that charged twice"); the notebook's breaking point named in scene 8.
- Assumptions: order, steps, ids and events are the lesson's stepper (ch_1, res_1, trk_1; events 1 to 8; worker-1,
  worker-2; a 24-hour sleep) and the Try's output (worker-2 ran charge=0 reserve=0 ship=1; cards charged: 1). The
  stepper leaves out the workflow-task events, and so does the video. "10:02" in the notebook is the lesson's.

## The one picture

Left: the workflow code (white), five lines, with a yellow cursor on the current line. Middle: the event history
(blue), the server's notebook, lines added only at the end. Right: worker-1 and worker-2 (teal) and the bank (gold)
with "cards charged". Dots run from a worker to the bank (real work) or from the history to the code (a recorded
answer). Red means lost or charged twice; green means done. Captions at the bottom.

## Scene 1 · Processing, forever · 0:00–0:40 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: Picture ordering a book online. That evening, your banking app shows the money gone. A week later, there's no
parcel, and the order page still says: Processing.

Behind that page, the shop's program had a few jobs. Charge your card. Set a copy of the book aside in the
warehouse. Wait a day, then book a courier. In code, that's a few lines, run one after another.

It charged the card. Then its computer restarted for an update. Everything the program held in memory, including
which line it had reached, was gone. Nothing will ever come back for the other jobs.

So here's the question. After a crash, how does a program carry on from where it stopped?

SCREEN: Title card. An order page "order: Processing". The code box draws in: charge(...), reserve(...), sleep(24 h),
ship(...), return SHIPPED. A worker box "the shop's program, at: charge"; the cursor moves to charge; a dot to the
bank; "cards charged: 1". The cursor moves to reserve, then the worker flashes red, "restarted: memory wiped", and the
cursor vanishes. A "?".

## Scene 2 · Run it from the top? · 0:40–1:15 · [PAIN] [BREAK] [WISH] [JOKE:release]

VO: The tempting fix: when the program starts again, run the order from the top. Each step worked the first time, so
it feels safe. Let's try it. Charge... and the bank charges the card a second time.

Two charges, and still no book. That's a bookshop with a very odd business model.

What we want is the same plain lines of code, and a program that remembers what it already did, even when its
memory is wiped.

SCREEN: Caption "run it again from the top?" in purple. Cursor at charge, a dot to the bank, "cards charged: 2" in red,
"paid twice". Then the counter goes back to 1 and the caption becomes the wish.

## Scene 3 · The shop's notebook · 1:15–2:00 · [ANALOGY] [MAP]

VO: Picture a shop with workers on shifts. Each order has an instruction sheet, and a notebook beside it. The first
worker does a step, then writes it in the notebook: ten oh two, charged the card, here's the receipt. Sets the book
aside, and writes that down too.

At the change of shift, the next worker has never seen this order. So they read the sheet from the top, with the
notebook open. Every step the notebook shows, they skip, and use the result written there. They start work at the
first step with no entry.

SCREEN: The history box appears in the middle, titled "notebook". Role labels: "instruction sheet" under the code,
"notebook" under the history, "workers on shifts" over the workers. Two notebook lines in handwriting style:
"10:02 charged the card: ch_1", "set the book aside: res_1". Worker 2 lights up; the cursor runs down the sheet while
ticks appear beside the two written steps; the cursor stops at the first unwritten step.

## Scene 4 · Name the parts · 2:00–2:40 · [NAME] [MAP]

VO: In software, this idea is called durable execution. Durable means it lasts through a crash. The sheet is your
code, called the workflow: the part that decides what happens next. The steps that touch the outside world, charge,
reserve and ship, are called activities. The notebook is the event history, and each line in it is an event. And the
workers are your programs.

Temporal is one well-known engine that works this way: a free program that keeps the history of every workflow, on a
server, in a database of its own.

SCREEN: The handwritten lines clear. Labels swap: "workflow code", "event history (server)", "worker-1", "worker-2".
The three activity lines glow gold. Caption: "Temporal: a free program that keeps each workflow's history".

## Scene 5 · Worker-1 writes it down · 2:40–3:25 · [SHOW]

VO: Watch worker-1 run the order. At charge, Temporal's library, the part of Temporal inside your program, doesn't
call the bank itself. It asks the server to schedule the charge. The server writes: Charge scheduled. The bank
charges the card, and the server writes: Charge done, with the receipt.

Reserve goes the same way: scheduled, then done. Then the sleep for a day becomes a timer. The server writes: Timer
started. No thread, no path of work in your program, waits a whole day.

Now we kill worker-1. Everything it held in memory about this order is gone. The history is untouched.

SCREEN: Events 1 to 5 appear one by one: "1 Charge scheduled", "2 Charge done: ch_1", "3 Reserve scheduled",
"4 Reserve done: res_1", "5 Timer started: 24 h". Dots: worker-1 to the server, server to the bank, back. "cards
charged: 1". Worker-1 turns red, "killed". The history glows blue.

## Scene 6 · A guess · 3:25–3:45 · [PREDICT] [PAUSE]

VO: A day later, the timer fires, and the server hands the order to worker-2, which has never seen it. So who calls
the bank this time? Pause and guess.

SCREEN: "6 Timer fired". Worker-2 lights up, "gets the task". A "?" by the bank. Countdown.

## Scene 7 · Replay · 3:45–4:40 · [SHOW] [LOOP-PAYOFF] [NAME] [JOKE:reward]

VO: Worker-2 runs the code from the first line. Wait, from the top? That's the fix that charged twice. Here's the
difference. At charge, the library finds Charge done in the history, and hands back the receipt at once. The bank
isn't called. Reserve: its result comes from the history too. And the sleep returns at once, because its timer
already fired.

Then the code reaches ship. There's no event for it. So this time, the library schedules it for real. Ship done.
The order returns: SHIPPED.

The lesson's demo prints the same. Worker-2 ran charge zero times, reserve zero times, ship once. Cards charged: one.

Running the code again against its history is called replay. A colleague who reads the notes before touching
anything. Every shop could use one.

SCREEN: The cursor runs down the code; at each finished line a dot flies from the matching event to the code (event
2 → charge "ch_1", event 4 → reserve "res_1", event 6 → sleep), the bank stays dim. At ship, a dot goes to the bank
side (courier work), "7 Ship scheduled", "8 Ship done: trk_1", "return SHIPPED" turns green. The demo's lines appear:
"worker-2 ran charge=0 reserve=0 ship=1", "cards charged: 1". Caption "replay: run the code again against its
history".

## Scene 8 · Three things to keep in mind · 4:40–5:20 · [GUARDRAIL] [BREAK of the analogy]

VO: Three things to keep in mind. One: the workflow code never touches the outside world itself. It runs again on
every replay, so a bank call written straight into it would run again too.

Two: a healthy worker rarely replays. It keeps recent orders in memory, and the server sends its next task back to
it. Replay is for when a worker dies.

Three: here's where the notebook breaks. A worker who charged the card, and died before writing it down, leaves no
trace. So the next one charges again. That's why each step still needs a key, so the bank can spot a repeat.

SCREEN: Three rule lines appear one by one. For rule 3: the gap between "bank charged" and "Charge done" marked with a
red bracket, "charged, not written down yet".

## Scene 9 · Moral and check · 5:20–6:00 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So how does a program carry on after a crash? It doesn't remember. It writes every step down outside itself.
Then any worker can replay the code against those notes: finished steps hand back their recorded answers, and real
work starts at the first step with no entry.

One quick check. Suppose worker-1 dies right after Reserve done, before the sleep starts. Worker-2 replays. What's
the first thing it does for real? Pause and think.

It starts the timer. Charge and reserve come from the history, and the sleep is the first step with no entry.

SCREEN: Caption "write every step down, then replay". For the check, events 5 to 8 fade; event 4 is the last line;
countdown. The cursor replays charge and reserve with dots from the history and stops at sleep: "Timer started" is
written as new event 5.

---

### Beat check

- QUESTION (scene 1) from the lesson's own felt situation; FAMILIAR: a few lines of code run in order.
- PAIN and BREAK of "run it from the top" (scene 2), then WISH.
- ANALOGY and MAP (scenes 3, 4) before the walk.
- PREDICT with PAUSE (scenes 6 and 9), SHOW right after each.
- NAME after the analogy: durable execution, workflow, activity, event history (scene 4), replay (scene 7, after it was
  seen).
- GUARDRAIL with the analogy's breaking point (scene 8) and MORAL (scene 9) last. Light moments: the odd business
  model, the colleague who reads the notes.

### Accuracy notes for the producer

- The stepper and the video leave out the workflow-task events; the Try's real history has 28 events (worker-2's
  Ship is events 22 to 24 there, not 7 and 8).
- "A bank call written straight into the workflow would run again on replay" follows from the section (the workflow
  never touches the outside world; replay reruns the function from the first line).
- Sticky execution: if the worker is gone, any worker gets the task after a short wait (5 seconds by default in the
  Java library). The Try turns sticky execution off.
- The gap in rule 3 is section 3's: the server retries the activity after its start-to-close timeout; the key is
  `"$workflowId/charge"`.
- In the check, worker-2 sends one new command (start the timer), which becomes the next event.
