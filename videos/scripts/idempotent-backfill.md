# Every job said fine, and the total doubled: retries that replace the day

- Slug / scene: `idempotent-backfill`, `videos/scenes/idempotent_backfill.py:IdempotentBackfill`
- Lesson: `batch-13`, section 1, "A retry is safe only if running twice leaves what running once does"
- Audience / level: a complete newcomer. Knows a program can crash; doesn't know what an orchestrator, a retry, a
  partition, idempotent or a backfill is.
- Length: 5:49 (~880 words of narration at Kokoro's ~175 words a minute, plus two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=274`, the backfill moment (both tables side by side, three gold rows and a red 17,923,971 on the left, one row and
  a green 5,974,657 on the right)
- The learner's real question: every job in the night said it finished fine, so how can the report show twice the
  money?
- Misconception to steelman and break: (1) "the program in charge undoes a failed attempt before it retries" (the
  lesson's warm-up trap), broken because it can't see inside the warehouse, only whether "done" arrived; (2) "then
  turn retries off", broken by the missing day and the rerun by hand, which is the same second run.
- Concept chain: a night of three jobs and a program in charge → a retry after a crash that came after the write →
  appending leaves two rows → the kitchen: add to the plate or replace it → replace the day's partition →
  idempotent, three rules → a backfill is one more rerun (hardest last: why the input must be the run's own day too)
- Analogy family: the lesson's kitchen. A cook plates a steak and is called away before saying "done"; the expediter
  calls the steak again; the second cook adds a steak to the same plate, or replaces the plate.
- Open loops: "how does a job that succeeded double the money?" planted in scene 1 → answered in scene 10;
  "turn retries off?" raised in scene 4 → answered in scene 9 ("make it safe first, then turn retries on").
- Assumptions: every number is the lesson's (235 payments; minute 5, 15, 20, 30, 35; 5,974,657 and 11,949,314 cents;
  a backfill a week later adds a third row; 90 nights, one in five, 21 nights hit, 28% too high). 17,923,971 is three
  times 5,974,657, the report a third row would give.

## The one picture

Top: the night's three tasks (extract, load, report) as boxes joined by arrows, grey while waiting, blue while
running, green when done, red when an attempt failed. Top left the caption "orchestrator: the run for 6 November",
top right a gold clock ("minute 15"). Bottom left: the gold table "daily_totals, load appends a row". Bottom right:
first the kitchen (a plate, steaks, two cooks, the expediter), then the blue table "daily_totals, load replaces the
day". Yellow dots carry each write from load down to a table. One caption line at the bottom.

## Scene 1 · The doubled total · 0:00–0:25 · [QUESTION] [LOOP-PLANT]

VO: Picture the payments company's night shift, run by programs instead of people. After the shops close, three
jobs run, one after another. One morning, the accountants open the report for 6 November. The total is twice what
the shops took. And every job says it finished fine. How does a job that succeeded double the money? Hold that
question.

SCREEN: Title card. The three task boxes grow in with arrows. A red "report: 2 × what the shops took" caption and
three green "done" states, then a yellow "?".

## Scene 2 · The night, and the program in charge · 0:25–1:00 · [FAMILIAR] [NAME]

VO: Here's the night. Extract copies the day's card payments into a work table. Load adds them up and writes one
total into a table called daily totals. Report reads that total. A program is in charge of the night. It starts
each job when the one before it is done, and if a job fails, it runs it again. That program is called an
orchestrator, and running a job again is called a retry. A retry feels careful. Something went wrong, so try again.

SCREEN: Tasks reset to grey. Each task glows as it's named; the gold table appears under load's arrow. The caption
"orchestrator: the run for 6 November" fades in top left; caption "retry: run a failed task again".

## Scene 3 · One night, one crash · 1:00–1:45 · [SHRINK] [SHOW]

VO: At minute 5, extract copies 235 payments for 6 November. At minute 15, load's first attempt adds them up and
writes the total: 5,974,657 cents. And then its machine dies, before it can tell the orchestrator it's done. The
total is already saved. The orchestrator only
knows one thing: this attempt never said done. So it marks it failed, waits five minutes, and runs load again. At
minute 30, the second attempt writes its total too, and this time it says done.

SCREEN: Clock "minute 5", a teal chip "staging: 235 payments"; extract goes green. "minute 15": load "attempt 1", a
dot runs down, the first row lands. A red cross on load, caption "the write is saved; the 'done' never arrives". Load
turns red "failed: retry", "minute 20", then "attempt 2", "minute 30". A second dot runs down. (The second row is
held back for the prediction.)

## Scene 4 · Guess, then the break · 1:45–2:40 · [PREDICT] [PAUSE] [SHOW] [JOKE:release] [BREAK]

VO: So what does daily totals hold for 6 November now? Pause and guess.

(three seconds)

Two rows. The first attempt's row never went away, and the retry added another. At minute 35, report adds up the
day: 11,949,314 cents. Twice the truth. And look at the tasks. Every one is green. The dashboard is happy. The
accountants are not. A green night only says each task said done in the end. It doesn't say how many times it
wrote.

You might be thinking: surely the orchestrator cleans up a failed attempt before it retries. Let's be fair to it. It
started the job, and it watched for done. That's all. The row went into the warehouse, a database built
for questions over years of data. The orchestrator can't see in there, so it can't undo anything. It can only run the
job again. Then turn retries off? Then a network hiccup at three in the morning leaves the day missing, and someone
reruns it by hand. That's the same second run, with the same second row.

SCREEN: Countdown bar. The second gold row drops in; red "report: 11,949,314 cents"; all three tasks green and
pulsing. Captions "green means each task said done, in the end". Then a purple caption "undo the failed attempt?"; a
dashed outline around the table labelled "the warehouse: the orchestrator can't see in"; caption "retries off? a
missing day, and a rerun by hand: the same second row".

NOTE: The dashboard line comes right after the reveal and is cashed back at once.

## Scene 5 · The kitchen · 2:40–3:25 · [ANALOGY] [MAP]

VO: Picture a restaurant kitchen. A cook puts a steak on a plate, and gets called away before shouting done. The
person calling out the orders, the expediter, hears nothing, so she calls the steak again. A second cook adds
another steak to the same plate. The table gets two steaks. Map it. The expediter is the orchestrator. Each cook is
one attempt. Shouting done is the success report. And the plate is the day's row in daily totals. Now the fix is
easy to see. The second cook shouldn't add to the plate. She should replace it. One plate, one steak, however many
cooks.

SCREEN: On the right, a kitchen: "expediter" at the top, a plate, "cook 1" puts a steak on it and leaves with a red
"no 'done!'"; "steak, again!"; "cook 2" adds a second steak, red "two steaks". The mapping as captions, each with the
matching part of the diagram glowing: orchestrator caption, load box, the "done" state, the gold rows. Then cook 2
lifts the plate away and sets down a fresh plate with one steak; "one plate, one steak".

## Scene 6 · Replace the day · 3:25–4:00 · [SHOW] [NAME]

VO: In the warehouse, that means giving the table one slice per day, called a partition, and letting load replace
its day's slice instead of adding a row. Run the same night again, crash and all. Attempt 1 writes the day. The
machine dies. Attempt 2 replaces the day with the same total. One row. Report says 5,974,657 cents, which is right.
Same tasks, same crash, same retry. Only the write changed: add became replace.

SCREEN: The kitchen goes; the blue table "daily_totals, load replaces the day" takes its place, with a "2026-11-06"
slice. Replay with clock and states: row lands, red cross, retry, the row is swapped for an identical one, green
"report: 5,974,657 cents".

## Scene 7 · The name and three rules · 4:00–4:30 · [NAME]

VO: A task like that is called idempotent. Running it twice leaves the same result as running it once. Three rules
get you there. One: read a fixed input, the run's own day. Never the latest data, and never the current time,
because a rerun next month would read something else. Two: write by replacing that day, never by adding. Three: make
the new result appear in one step, old day or new, never half.

SCREEN: Green chip "idempotent: twice = once". Captions for the three rules, the staging chip glowing for rule one,
the blue table for rule two.

## Scene 8 · A backfill is one more rerun · 4:30–4:55 · [SHOW] [NAME]

VO: Rerunning past days, to fix a bug or fill a gap, is called a backfill. A week later, a
backfill reruns 6 November. The appending table gains a third row: 17,923,971 cents. The replacing table doesn't
change. A retry and a backfill are the same thing: running a task again.

SCREEN: Caption top left becomes "a backfill reruns 6 November"; all tasks blue "rerun"; dots to both tables; third
gold row, red 17,923,971; the blue row swaps for itself, green.

## Scene 9 · How bad, and the limit · 4:55–5:30 · [GUARDRAIL] [LOOP-PAYOFF]

VO: How bad does this get? A demo runs 90 nights, where each load has a one in five chance of crashing
right after its write. 21 nights are hit. The appending table ends 28 percent too high, and every run shows success.
So turning retries on, by itself, made the numbers worse. Make the task safe first, then turn retries on. One limit.
Some things can't be replaced, like an email to a shop. Once it's sent, it's sent. Put a step like that in its own
task, and keep a note of what it already did.

SCREEN: Reports become "90 nights: 28% too high, 21 wrong days" (red) and "90 nights: 0 wrong days" (green).
Captions "make the task safe first, then turn retries on" and "an email can't be replaced: its own task, with a note
of what it sent".

## Scene 10 · The moral, and a check · 5:30–6:00 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, how did a job that succeeded double the money? It succeeded twice, and it added both times. A task that runs
twice must leave what one run leaves. Replace the day; never add to it.

One quick check. A load reads the newest payments, whatever day they're from, and replaces the run's own day. You
backfill 6 November. Is that safe? Pause and think.

(three seconds)

No. It replaces the right day, but with the wrong payments: today's. The input has to be the run's own day too.

SCREEN: Caption "replace the day; never add to it" (yellow). For the check, the blue row turns red "2026-11-06  today's
total"; then caption "fixed input + replaced output".

---

### Beat check

- Opens with QUESTION (scene 1) from a felt symptom; FAMILIAR (scene 2) before any mechanism.
- SHOW then PREDICT with PAUSE (scene 4, and the check in scene 10).
- BREAK: the "undo the failed attempt" model and "turn retries off" (scene 4).
- ANALOGY + MAP (scene 5), said part by part; the fix is found inside the analogy before the warehouse version.
- NAME after the idea: orchestrator and retry (plain sentence first), partition and idempotent (scenes 6 to 7),
  backfill (scene 8).
- GUARDRAIL (scene 9) and MORAL (scene 10) last. Light moments: "the dashboard is happy, the accountants are not"
  (about 2:05), "one plate, one steak, however many cooks" (about 3:20).

### Accuracy notes for the producer

- The night, its minutes and its totals are the lesson's Try it output (RetryDemo): extract 235 payments at minute 5,
  load attempt 1 writes at minute 15 and its worker dies, the retry after 5 minutes, attempt 2 writes at minute 30,
  report at minute 35 reads 11,949,314 (append) or 5,974,657 (overwrite).
- 17,923,971 is three times 5,974,657; the stepper only says the appending copy gains a third row.
- 90 nights with a one-in-five chance of a crash after the write, some nights twice: 21 nights hit, +28.0% and 21 wrong
  days for append, 0 wrong days for overwrite (RetryDemo with seed 7).
- "Replace" covers the lesson's options: overwrite the partition, delete and insert inside one transaction, MERGE, or
  one Iceberg commit. The video shows only the partition overwrite.
- The check question is the lesson's lab case where `latestDailyTotal` copies today's total into every backfilled day.
- Left to the lesson: Airflow's and Prefect's wording, MapReduce's renames, speculative execution, backfill caps.
