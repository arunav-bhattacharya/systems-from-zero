# Less, never none: how nice values share a CPU

- Slug / scene: `cpu-scheduling`, `videos/scenes/cpu_scheduling.py:CpuScheduling`
- Lesson: `os-04`, section 1, "Nice values become weights, and a CPU is shared by weight"
- Audience / level: a complete newcomer. Has met tasks (the kernel's word for a thread), the scheduler and round
  robin with a time slice in the lesson's first section, through the game console and the kitchen timer.
- Length: 4:42 (~685 words of narration at the Kokoro voice's ~165 wpm, plus two pauses and silent builds)
- Poster: `POSTER=194` (both score bars at 57 and 55.9, the strip of 21 turns, the weight table and the lab result)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: one of two busy programs matters less. How do you tell the kernel that, without
  the less important one stopping altogether?
- Misconception to steelman and break: "priority means the important one always goes first". Broken by following
  strict priority to its end: the totals job never runs. A second wrong idea, "a nice task always runs slower", is
  broken in the guardrail: alone on an idle CPU, nice 19 still gets all of it.
- Concept chain: round robin treats both the same → strict priority starves → nice values → weights and shares by
  weight → how: a score (virtual runtime) whose clock runs faster for lighter tasks, and the smallest score runs →
  the lab agrees (90/10) → limits: late arrivals, only the ratio matters, weights only divide contested time
  (hardest last: the score rule)
- Analogy family: the lesson's game console at home. Children are tasks, the console is a CPU, whoever decides is
  the scheduler, the kitchen timer is the time slice, the score sheet of minutes is virtual runtime, and minutes
  that count nine times over are a light weight. It breaks when a child turns up late with a score of zero.
- Open loops: "less CPU, never none" planted in scene 2 → paid off in scene 4 (9.7%) and the moral.
- Assumptions: the lesson's numbers: round robin 4.99 s each in 10 s; the weight table (nice -5: 3121, 0: 1024, 1:
  820, 5: 335, 10: 110, 19: 15); 90.3% against 9.7%; 9.3 times faster (1024 / 110); 3 ms slices; the lab run 9.01 s
  against 0.98 s; nice 5 gives 7.53 s against 2.47 s. The task names Taps and Totals are made up for the picture.

## The one picture

Left: the console (CPU 0), with a slot where the task that's playing sits, and the two tasks as chips below it:
Taps (blue, the loop that answers card taps) and Totals (gold, the nightly totals job). Right, top: the score sheet,
one bar per task for its virtual runtime. Right, middle: the weight table. Bottom: a strip of turns, one block per
3 ms slice in the task's colour, which also shows a split bar for shares. Green means the share works out; red means
starved or wrong. Same places from start to end.

## Scene 1 · One console, two children · 0:00–0:40 · [QUESTION] [FAMILIAR]

VO: Picture one game console at home, and two children who both want to play. Somebody has to decide whose turn it
is. In a computer, the children are tasks, the console is a CPU, and the one deciding is the kernel's scheduler. Our
two tasks are loops that never stop to wait. One answers taps at the café's card readers. The other adds up the
night's payments. With a kitchen timer, each plays 3 milliseconds, then passes the controller. In the lab box, that
split one CPU evenly: about 5 seconds each, out of 10.

SCREEN: The console and two chips (Taps, Totals). Each slice, a chip moves into the console and a block drops into
the strip of turns: blue, gold, blue, gold. Caption "round robin: 4.99 s each, out of 10".

## Scene 2 · Strict priority, followed to its end · 0:40–1:10 · [PAIN] [BREAK] [JOKE:release] [WISH] [LOOP-PLANT]

VO: But the totals job can wait till morning, and the card readers can't. We'd like it to step aside. The obvious
rule is strict priority: always run the important one first. Let's follow it. The tap loop never stops, so the
totals job never gets a turn. Ask any younger sibling how that feels. Linux wants a less important task to get less
CPU, never none.

SCREEN: The strip fills with blue blocks only; Totals waits with "0%" in red. Caption "less CPU, never none".

## Scene 3 · nice · 1:10–1:35 · [NAME] [JOKE:vehicle]

VO: To say that a task matters less, Linux gives it a nice value, a number from minus 20 to 19. Higher means nicer to
the others. Every process starts at 0, and the command nice can start one at 10. Anyone may make their own program
nicer. Making one less nice needs administrator rights. Kindness is free; cutting in line takes permission.

SCREEN: Chips gain "nice 0" and "nice 10". Captions "nice: -20 to 19, higher is nicer to the others", "nicer:
anyone; less nice: administrator rights".

## Scene 4 · Weights, and a prediction · 1:35–2:15 · [SHOW] [PREDICT] [PAUSE] [LOOP-PAYOFF]

VO: Then the kernel turns each nice value into a weight, from a fixed table in its code. Nice 0 weighs 1024. Nice 10
weighs 110. When tasks compete for one CPU, each gets its weight divided by the total. So, 1024 against 110. What
share does the totals job get? Pause and guess.

(three seconds)

About a tenth: 110 out of 1,134 is 9.7 percent. The tap loop gets 90.3. Less, but never none.

SCREEN: The weight table; the columns for 0 and 10 boxed; chips gain "weight 1024" and "weight 110". Countdown. A
split bar: blue 90.3%, gold 9.7%.

## Scene 5 · The score sheet · 2:15–3:00 · [ANALOGY] [MAP] [NAME]

VO: But how does the kernel hand out time by weight, turn after turn? Back to the console. Keep a score sheet next
to it that adds up each child's minutes, and let whoever has the smallest total play next. Now say one child's
minutes count about nine times over. Their total climbs fast, so their turns come round far less often. Map it. The
score is the task's virtual runtime: the CPU time it has really had, times 1024 divided by its weight. For nice 0, the
clock runs at real speed. For nice 10, it runs 9.3 times faster. And the rule fits in one line: run the task with the
smallest virtual runtime.

SCREEN: The score sheet with two empty bars. Captions "score = virtual runtime = CPU time × 1024 / weight", "nice 0:
× 1", "nice 10: × 9.3", "run the smallest score".

## Scene 6 · Watch the scores · 3:00–3:30 · [SHOW]

VO: Watch it. Taps plays 3 milliseconds: its score goes up by 3. Now Totals has the smallest score, so it plays. Its 3
milliseconds add almost 28. Now Taps is far behind, so it gets picked again, and again, until it passes 28. That's
about nine turns for every one. Run it longer, and the shares settle at 90 and 10.

SCREEN: Slice by slice: the playing chip in the console, its bar growing (3, then 27.9), blocks in the strip. Two
rounds: Taps 19 blocks, Totals 2; the bars end at 57 and 55.9.

## Scene 7 · The lab, and the name · 3:30–3:50 · [SHOW] [NAME]

VO: The lab box agrees with the arithmetic. Two loops on one CPU for 10 seconds, at nice 0 and nice 10: 9.01 seconds
against 0.98. That rule, smallest virtual runtime first, was the heart of the Completely Fair Scheduler, which Linux
used from 2007 until 2023.

SCREEN: "lab box, 10 s: nice 0 got 9.01 s (90%), nice 10 got 0.98 s (10%)". Caption "CFS: the Completely Fair
Scheduler, Linux 2.6.23 (2007) to 6.6 (2023)".

## Scene 8 · Where the console breaks, and two rules · 3:50–4:30 · [GUARDRAIL] [BREAK]

VO: Here the console picture breaks. A child who shows up late starts at zero, and would play for an hour to catch
up. The kernel never allows that. A task that starts late, or wakes from a long sleep, gets a score close to the
others'. Two more things to keep. Only the ratio matters: nice 10 against nice 15 splits a CPU the same way as 0
against 5. And weights only divide time among tasks that want it at the same moment. A nice 19 task alone on an idle
CPU still gets all of it.

SCREEN: A third bar, "late arrival", at zero; a red arrow "would play for ages"; the bar jumps up near the others'.
Then "10 vs 15 = 0 vs 5"; then Totals alone in the console, "nice 19, alone: 100%".

## Scene 9 · The moral, and a check · 4:30–5:00 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So how do you tell the kernel a task matters less, without starving it? Give it a lighter weight. Its clock runs
faster, the smallest score plays next, and shares follow the weights. One quick check. From the table, nice 5 weighs
335. Nice 0 against nice 5: what's the split? Pause and think.

(three seconds)

About 75 against 25: 1024 out of 1,359. The lab box gave 7.53 seconds against 2.47.

SCREEN: The bars, the table and the strip glow in turn; caption "lighter weight, faster clock, smallest score plays".
For the check, the nice 5 column is boxed; countdown; a split bar 75.3% / 24.7%; "lab box: 7.53 s against 2.47 s".

---

### Beat check

- QUESTION and FAMILIAR from the lesson's console and kitchen timer (scene 1).
- PAIN and BREAK: strict priority followed until it starves (scene 2), then the WISH.
- NAME (nice) after the wish; SHOW the weights and PREDICT with PAUSE (scene 4).
- ANALOGY + MAP for the score sheet (scene 5) before NAME (virtual runtime), then SHOW (scenes 6 and 7).
- GUARDRAIL with the analogy's break and two limits (scene 8); MORAL and a check answerable from the table (scene 9).
  Light moments: the younger sibling (1:00), kindness is free (1:30), the late child (3:55).

### Accuracy notes for the producer

- Weights are the kernel's `sched_prio_to_weight` table as the lesson gives it. Shares: 1024 / 1134 = 90.3%, 110 /
  1134 = 9.7%; 1024 / 1359 = 75.3%.
- The slice-by-slice picture (Taps 3, Totals 27.9, Taps about nine turns) follows the rule the lesson states,
  smallest virtual runtime first, with 3 ms slices. The lab box runs Linux 6.12, whose EEVDF scheduler (the next
  section) adds eligibility and deadlines, so its real turns interleave differently (the nice 10 loop ran 364 turns
  of about 2.7 ms). The shares are the same, and that is what the lab numbers show.
- Round robin's 4.99 s each and the 3 ms slice are from the lesson's first section.
- How a late or waking task's virtual runtime is set (near the others') is left to Go deeper, as in the lesson.
- `renice` and `CAP_SYS_NICE` are left to the lesson; the video says "administrator rights".
- Taps and Totals are names for the picture; the lesson calls them the program that answers card taps and the
  nightly totals job.
