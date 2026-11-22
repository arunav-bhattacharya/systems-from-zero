# Where did the 30 go? A batch can't decide, so WATCH checks the decision

- Slug / scene: `watch-multi`, `videos/scenes/watch_multi.py:WatchMulti`
- Lesson: `txn-06`, section 2, "MULTI/EXEC sends a batch, and WATCH checks a decision made in your code"
- Audience / level: a complete newcomer. Can read a little code; knows nothing about Redis, threads, connections or
  transactions.
- Length: 5:47 (~900 words of narration, two pauses for guesses, one for the check)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=257`, the retry done (balance 20 in green with a tick, pod A's six lines, the strip with the green EXEC chip)
- The learner's real question: Redis runs one command at a time, so how can two payments lose money? And how do you
  make "read, decide, write" safe?
- Misconception to steelman and break: (1) "one thread, so my GET then SET is safe" (broken by the lost update:
  80 paid, balance 50); (2) "put it all in a MULTI batch" (broken: the GET inside answers QUEUED, so the batch can't
  decide; and a failing command fails alone, no rollback)
- Concept chain: one command runs alone → two commands are two turns, with others between → a batch runs as one
  step but can't decide → WATCH lets your code decide and refuses a stale decision → retry loop (check-and-set,
  optimistic) → busy keys make retries lose (hardest last), so a script comes next
- Analogy family: the lesson's café with one barista. One slip with all your orders is the batch. "Keep an eye on
  card 7, and throw my slip away if it changes" is WATCH; the barista's list of watchers and the mark by a name are
  Redis's watched keys and the dirty flag. Where it breaks: a real barista notices someone asking about your card
  mid-order; Redis doesn't remember who asked what (said out loud, the lesson's own break).
- Open loops: "where did the 30 go?" planted in scene 1 → paid off in scene 9; "how do we stop it?" scene 1 → scene 6
- Assumptions: numbers are the lesson's (balance:7 holds 100; coffee 30 at pod A, fuel 50 at pod B; lost update
  leaves 50; with WATCH, B writes 50, A's EXEC answers nil, A retries and writes 20; fifty pods on a hot key).

## The one picture

Pod A (blue, left) and pod B (gold, right), each with its command lines; Redis (white, centre) with `balance:7`, its
value, and below a divider the watch list (one row per watching pod: clean in green, dirty in red). Grey links join
each pod to Redis; yellow dots are commands, white dots answers, red dots a nil. Along the bottom, "the thread's
order": one chip per turn on the thread, coloured by pod. Captions under it. Same places and colours throughout.

## Scene 1 · The hook · 0:00–0:25 · [QUESTION] [LOOP-PLANT] [JOKE:pivot]

VO: A prepaid card has 100 on it. At the same moment, it pays 30 for a coffee and 50 for fuel. So 20 should be left.
The card says 50. Somewhere, 30 just walked out the door. And the program that keeps the balance runs one command at
a time, so nothing ever runs at once. How did money go missing? And how do we stop it?

SCREEN: A card with 100; coffee -30 (blue) and fuel -50 (gold) either side; "should be 20" (green), "the card says
50" (red), the card's number turns red 50. Caption "one command at a time"; a yellow "?".

## Scene 2 · One barista, Redis, pods · 0:25–1:05 · [FAMILIAR] [ANALOGY]

VO: Picture a café with one barista. She makes one drink at a time, and never starts the next until it's handed over.
Redis, a program that keeps data in memory and answers short commands, works the same way. One thread, a single line
of work, runs every command to the end before it takes the next. Redis keeps each value under a name, called its
key. The card's balance sits under the key balance:7. Big apps run several copies of their program, so payments keep
flowing if one machine fails. Call each copy a pod. The coffee reaches pod A, and the fuel reaches pod B.

SCREEN: The centre box appears as "one barista / one drink at a time"; three order slips (latte, tea, mocha) enter it
one at a time. The label becomes "Redis / one thread", and three commands (GET, SET, GET) go in the same way. `balance:7` and 100 appear inside. Pod A and pod B draw in,
linked to Redis.

## Scene 3 · The lost update · 1:05–1:55 · [PAIN] [SHOW] [NAME] [BREAK of the analogy]

VO: Each pod does what looks right. GET the balance, check that it's enough, then SET the new one. Pod A reads the
balance: 100. Pod B reads it too: 100. Pod A works out 100 minus 30, and SETs 70. Pod B works out 100 minus 50, and
SETs 50. The card paid 80, and the balance says 50. The last SET won, and it never saw the first. That's called a
lost update.

Notice, every command ran alone. The thread did nothing wrong. A decision took two commands, and between them, the
thread served the other pod. A real barista would notice someone asking about your card in the middle of your order.
Redis doesn't remember who asked what. It serves each command, and moves on.

SCREEN: Dots carry each command; pods' lines fill ("GET balance:7 → 100", "100 - 30 = 70", "SET balance:7 70"). The
strip fills: A: GET, B: GET, A: SET 70, B: SET 50. The value goes 70, then red 50. The A: SET 70 chip dims. The gap
(B: GET between A's two chips) gets a yellow outline.

## Scene 4 · The batch, and its break · 1:55–2:55 · [WISH] [PREDICT] [PAUSE] [BREAK]

VO: Wouldn't it be nice to hand over the whole thing in one go? Redis has a batch for that, like one slip with all
your orders on it. MULTI says: start a slip. Every command after it answers QUEUED instead of running. EXEC then runs
the whole slip as one step. No other pod's command can land in the middle.

So let's put the GET on the slip too. What does it answer? Pause and guess.

(three seconds)

QUEUED. The balance comes back with all the other answers, after EXEC. That's too late to decide what to SET. A batch
runs together, but it can't decide. And one more surprise. If a command on the slip fails while it runs, it fails
alone, and the rest still run. There's no rollback. A batch means nothing can interrupt it. It doesn't mean all or
nothing.

SCREEN: Pod B dims. Pod A: MULTI, SET balance:7 70 → QUEUED, EXEC → 1) OK, inside a yellow slip outline; one chip
"A: MULTI..EXEC"; the value becomes 70. Caption "back to 100, and a new slip" as the value resets. Then MULTI, GET balance:7, "enough for 30?"; countdown; → QUEUED; EXEC → 1) 100; "too late to decide"
(red). Captions for the rollback point.

## Scene 5 · The watch list · 2:55–3:35 · [ANALOGY] [MAP]

VO: So the decision stays in your code. We just need to know if anyone changed the card while we were
thinking. Back to the café. You tell the barista: I'm keeping an eye on card 7. If anyone changes it before
my slip arrives, throw my slip away. She keeps a little list of who is watching which card. Whenever anyone writes
card 7, she puts a mark next to every other name watching it. That's exactly what Redis does. The command is WATCH.
The list lives inside Redis, one entry per connection. And a name with a mark is what Redis calls dirty.

SCREEN: Pod B returns. A divider and "watch list" appear inside Redis. Captions map each part: keep an eye on it =
WATCH; a name with a mark = dirty.

## Scene 6 · The race, replayed · 3:35–4:40 · [SHOW] [PREDICT] [PAUSE] [LOOP-PAYOFF] [JOKE:reward]

VO: Let's replay the race. Both pods WATCH balance:7, then GET it: 100. Each decides in its own code. Pod A plans 70,
pod B plans 50. Pod B is quicker. MULTI, SET 50, EXEC. Its name has no mark, so the slip runs. The balance is 50. And
because the card was written, Redis marks every other watcher. Pod A is now dirty, and pod A doesn't know it yet.

Now pod A sends its slip: MULTI, SET 70, EXEC. Without the watch, this SET would wipe out B's payment. What happens
now? Pause and guess.

(three seconds)

EXEC checks the mark first. It finds it, throws the SET away, and answers nil, Redis's word for no value. Nothing ran,
and B's payment survives. Nil means: you lost the race, start over. Pod A watches again, reads 50, checks that 30
still fits, and writes 20. Nobody touched the card this time, so EXEC runs. 20. Both payments count. And notice,
Redis never made anyone wait. It only refused a decision made from old news.

SCREEN: Watch rows "pod A clean", "pod B clean". B's six lines; EXEC → OK; value 50; B's row goes (EXEC clears its
watches), A's row turns "dirty". A's lines; countdown; A's SET dims, EXEC → nil (red dot back), red chip. Retry: six
lines, EXEC → OK, value 20 in green with a tick, caption "100 - 50 - 30 = 20".

## Scene 7 · The name · 4:40–4:55 · [NAME]

VO: This pattern is called check and set. Read, decide, and write only if nothing changed since the read, inside a
loop that tries again. It's optimistic: it bets that clashes are rare, and pays only when one happens.

## Scene 8 · Guardrails · 4:55–5:30 · [GUARDRAIL] [JOKE:amplify]

VO: Two things keep it honest. First, a watch belongs to a connection, the open line between your program and Redis.
WATCH, MULTI and EXEC must travel on the same one. Second, every retry costs trips there and back. If fifty pods write
the same card all day, it turns into musical chairs. Most attempts lose, and each loss costs another round. For a key
that busy, send the whole decision to Redis as a script, which never needs to retry. That's next.

SCREEN: Pod A's link glows; three dots on the same link. Many dots from both pods. Captions.

## Scene 9 · Moral and a check · 5:30–6:00 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So where did the 30 go? Into the gap between two commands. The thread was never the problem. A batch runs
together, but can't decide. WATCH lets your code decide, and refuses the write if the card changed while you were
thinking.

One quick check. After pod A's WATCH, pod B sets balance:7 to 100, the value it already had. Does pod A's EXEC run?
Pause and think.

(three seconds)

No. It answers nil. Redis doesn't compare values. Any write marks the watchers, even one that changes nothing.

SCREEN: Reset to 100; pod A watches (clean); pod B's SET balance:7 100; pod A's slip; countdown; A turns dirty;
EXEC → nil; caption "any write marks the watchers".

---

### Beat check

- QUESTION (scene 1) from a felt symptom; FAMILIAR + ANALOGY (scene 2) before any command name.
- PAIN + SHOW (scene 3), NAME "lost update" after it is shown; the analogy's limit said out loud.
- WISH, PREDICT + PAUSE, BREAK (scene 4): the obvious fix (a batch) fails to decide.
- ANALOGY + MAP (scene 5); SHOW, PREDICT + PAUSE (scene 6); NAME check-and-set and optimistic (scene 7) after the
  replay; GUARDRAIL (scene 8); MORAL + check question (scene 9).
- Light moments: "30 just walked out the door" (0:12), "refused a decision made from old news" (4:35), "musical
  chairs" (5:15).

### Accuracy notes for the producer

- All numbers and outcomes are the lesson's stepper: both pods WATCH and read 100; B's EXEC runs and writes 50; A's
  EXEC answers `(nil)`; A retries, reads 50, writes 20. EXEC clears the connection's watches whatever the outcome, so
  B's row leaves after its EXEC and A's after its successful retry.
- "Any write, even the same value again" is the lesson's statement (section 2 body and stepper frame 2).
- The batch example uses a SET with a plain number; the lesson's own MULTI example is a DECRBY/INCRBY transfer. The
  GET answering QUEUED, its value arriving with EXEC's results, and the no-rollback behaviour are as in the lesson.
  EXECABORT (a command rejected while queuing) is left to the lesson.
- Jedis `transaction(false)` / Lettuce's shared connection, "watch only what your decision reads", and Redis 8's
  IFEQ and INCREX are left to the lesson.
- The "pod A then pod B" lost update leaves 50, as in the lesson's opening; the reverse order would leave 70.
