# An armful at a time: sorting more than fits in memory

- Slug / scene: `external-sort`, `videos/scenes/external_sort.py:ExternalSort`
- Lesson: `batch-02`, section 3, "Sorting more than fits in memory: external merge sort"
- Audience / level: a complete newcomer. Has counted votes on a tally sheet; met the hash map count in the previous
  section and saw it run out of memory; knows nothing about runs, merges, fan-in or GNU sort.
- Length: about 4:10 (~700 words of narration, two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=144`, merge pass 2 done: the twelve codes in order on the output row, with "after pass 2: 1 run"
- The learner's real question: the tally ran out of memory. Doesn't sorting have the same problem: to put keys in
  order, surely you need them all in memory at once?
- Misconception to steelman and break: "sorting needs every key in memory", broken by sorting twelve keys with room
  for four, and 46 MB with 4 MB in the Try it.
- Concept chain: a pile too big for the table → sort an armful at a time into runs → merge the runs by looking only
  at the top of each → equal keys end up side by side, so one counter counts them → fan-in and passes decide how many
  trips over the disk (hardest last)
- Analogy family: the lesson's ballot table. A pile of ballots too big for the table; an armful sorted and set aside
  as a stack; merging by looking at the top ballot of each stack; counting equal names as they pass.
- Open loops: "surely you need them all in memory?" planted in scene 1 → scene 6 ("never more than 4 keys");
  "how many passes?" planted in scene 4 → scene 5.
- Assumptions: all values are the lesson's stepper (twelve status codes 201 200 201 402 500 201 200 404 201 402 200
  201; memory for 4; fan-in 2; runs 1 to 3; run 4 of 8 keys; counts 200: 3, 201: 5, 402: 2, 404: 1, 500: 1), its
  numbers at scale (100 GB, 1 GB, 100 runs, fan-in 16: 100 → 7 → 1; fan-in 128: one pass) and the Try it (46 MB,
  `-S 4M`, 73 runs, 77 temporary files, under 7 MB; default buffer 300 MB, no temporary files, faster).

## The one picture

Top: the input, twelve key chips in a row. Below it, a gold box: the memory, with room for four. Below that, the
runs on disk, one row each, labelled run 1 to run 3 (later run 4). On the right, a teal merge box holding the head of
each open run. At the bottom, the output row. In the analogy the same places are the ballot pile, the table and the
sorted stacks. Counters for runs and passes sit at the far right; captions at the bottom.

## Scene 1 · The tally ran out · 0:00–0:30 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: In the last section, the tally ran out of memory: a hash map keeps one line per different key, and there were too
many keys. Sorting looks like it has the same problem. To put keys in order, surely you need them all in memory at
once? A sort done in memory does, and it would fail exactly like the hash map. Hold that thought.

SCREEN: Title card. A gold memory box overflowing with key chips, a red "out of memory". Caption "sorting needs every
key in memory?" in purple.

## Scene 2 · Too big for the table · 0:30–1:15 · [ANALOGY] [MAP]

VO: Back at the ballot table, picture a pile too big for the table. Take an armful, sort it by name, and set the
sorted stack aside. Take the next armful, and the next, until the pile is gone. Then merge the stacks: look at the top
ballot of each, take the one that comes first in the alphabet, and repeat. Equal names come out side by side, and you
count them as they pass. Map it out. The table is the memory. An armful is what fits in it. Each sorted stack is a
file on disk. And the merge only ever looks at the top of each stack.

SCREEN: Gold ballots in a pile at the top; an armful of four moves onto the table, shuffles into order, drops below as
a stack; three stacks. A yellow outline on the top ballot of each stack. Captions map each part.

## Scene 3 · Making runs · 1:15–2:00 · [SHRINK] [SHOW] [NAME] [JOKE:release]

VO: Let's shrink it. A web server's log records a status code for every request, a number like 200 for OK or 404 for
not found. Here are twelve of them, and a memory that holds only 4. Read the first 4, sort them in memory, and write
them to a temporary file. A sorted file like this is called a run. Two more batches give runs 2 and 3. The input has
been read once, and every key sits in a sorted run. The memory never held more than 4. It's a very short table, and
it never complained.

SCREEN: The twelve chips; four drop into memory, reorder to 200 201 201 402, and drop to "run 1". Then 200 201 404
500 to run 2, 200 201 201 402 to run 3. Counter "runs on disk: 3".

## Scene 4 · How many passes? · 2:00–2:20 · [PREDICT] [PAUSE]

VO: Now the merge. Our merge reads only 2 runs at once. We have 3 runs. How many rounds of merging until one sorted file
is left? Pause and guess.

SCREEN: The merge box "reads 2 runs at once"; countdown.

## Scene 5 · Merging · 2:20–3:25 · [SHOW] [NAME] [LOOP-PAYOFF]

VO: Two. Pass 1 opens runs 1 and 2. It keeps the first key of each in a small priority queue, a structure that always
hands back its smallest item first. Write the smaller one, refill from the run it came from, and repeat. 200, 200,
201, and on. Memory holds one key per open run, however long the runs are. Runs 1 and 2 become run 4, with 8 keys.
Run 3 had no partner, so it waits. 3 runs became 2. Pass 2 merges run 4 with run 3, and writes the final sorted
file. Each pass read and wrote every key once, from the start of each file to its end, the way disks read fastest.

SCREEN: Heads of runs 1 and 2 sit in the merge box; the smaller moves to a new row; three keys come out, then the
rest; run 4 has 8 keys, runs 1 and 2 vanish; "after pass 1: 2 runs". Pass 2 fills the output row with the twelve keys
in order; "after pass 2: 1 run".

## Scene 6 · Counting, and the name · 3:25–3:55 · [SHOW] [NAME] [LOOP-PAYOFF]

VO: Equal keys are now neighbours, so uniq, a small program that collapses repeated lines, counts them with a single
counter: 200 comes three times, 201 five times, 402 twice, 404 and 500 once each. At no step did the sort hold more than 4
keys. This is called an external merge sort: external because the runs live outside memory, on disk.

SCREEN: Brackets under each group of equal keys with counts "3", "5", "2", "1", "1". Caption "never more than 4 keys
in memory", then the name.

## Scene 7 · At scale · 3:55–4:35 · [GUARDRAIL] [NAME]

VO: Now the real numbers. 100 GB of keys and a 1 GB buffer give 100 runs. The number of runs one merge reads at once
is the fan-in. With a fan-in of 16, the first pass leaves 7 runs and the second leaves 1: two passes. With 128, one.
Every pass reads and writes all 100 GB. So a sort costs more processor work and extra trips over the disk, and in
exchange it never runs out of memory. It only gets slower as the input grows. GNU sort, the sort program on Linux,
does all this on its own: with a 4 MB buffer, 46 MB of keys made 73 runs, and it never held more than about 7 MB.

SCREEN: The chips dim; three boxes "100 runs → 7 → 1" for fan-in 16 and "100 → 1" for fan-in 128. Caption "every pass
reads and writes all 100 GB". Then `sort -S 4M` with "46 MB: 73 runs, under 7 MB of memory".

## Scene 8 · The moral, and a check · 4:35–5:05 · [MORAL] [PREDICT] [PAUSE]

VO: So the moral of the story: when the keys don't fit, sort an armful at a time, and merge by looking only at the top
of each run. The tally falls off a cliff. The sort just walks a little slower. One quick check. With a fan-in of 2,
how many merge passes do 5 runs need? Pause and think.

(three seconds)

Three. 5 runs become 3, then 2, then 1.

SCREEN: Moral in yellow. Five run chips; countdown; "5 → 3 → 2 → 1: 3 passes".

---

### Beat check

- QUESTION and FAMILIAR (scene 1) with the wrong model planted. ANALOGY and MAP (scene 2) before any name.
- SHRINK, SHOW and NAME "run" (scene 3); PREDICT with PAUSE (scenes 4 and 8); SHOW and NAME "priority queue" (scene 5).
- BREAK: the "needs everything in memory" model is broken by 12 keys in 4 slots (scene 6) and 46 MB in 7 MB (scene 7).
- GUARDRAIL: more disk and processor work, slower as input grows (scene 7). MORAL and check (scene 8).
- Light moments: the short table that never complained (scene 3), the cliff and the walk (scene 8).

### Accuracy notes for the producer

- Passes follow the lesson's rule: each pass turns r runs into r / F, rounded up.
- The Try it's 77 temporary files at fan-in 16 (73 runs plus 4 intermediate merges) are left out; GNU sort merges
  smarter than whole passes.
- The default buffer took 300 MB, wrote no temporary files and finished sooner; the video says only "with a 4 MB
  buffer".
- `LC_ALL=C` and the other options in the lesson's table are left to the lesson.
