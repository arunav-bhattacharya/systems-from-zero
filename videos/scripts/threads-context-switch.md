# Ten thousand waits, a few baristas: virtual threads

- Slug / scene: `threads-context-switch`, `videos/scenes/threads_context_switch.py:ThreadsContextSwitch`
- Lesson: `os-03`, section 4, "Virtual threads: many waits on a few OS threads"
- Audience / level: a complete newcomer. Has met threads and tasks in the lesson's first sections (a thread is one
  line of work; the kernel runs each as a task), and the limit of 64 tasks in section 4.
- Length: 4:39 (~730 words of narration at the Kokoro voice's ~175 wpm, plus two pauses and silent builds)
- Poster: `POSTER=187` (the 37 tasks lit under the café: 25 helpers and 12 carriers, 10,000 slips on the rail)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: 10,000 payments each wait 120 ms for the bank. How can one program wait on all of
  them without 10,000 threads falling over?
- Misconception to steelman and break: "a Java thread is always a kernel task, so 10,000 waits need 10,000 tasks".
  Broken by the prediction: 10,000 virtual threads under the same limit of 64, and the kernel sees 37 tasks.
- Concept chain: one thread per payment works for a dozen → at 10,000 the waiting costs tasks, stacks and the limit
  (fails at 42) → callbacks avoid waiting but lose plain code → a few baristas and a rail of slips → virtual threads
  mount on carriers, unmount on a wait, remount anywhere → the kernel sees only the carriers (37 tasks) → limits:
  the whole stack moves, pinning, not faster, one per job (hardest last: pinning in the check)
- Analogy family: the lesson's café. A barista is a platform thread (a real OS thread); one barista per customer is
  one platform thread per payment; a few baristas are the carriers; order slips on a rail are virtual threads; the
  steaming milk is the wait for the bank. It breaks on what gets put aside (a slip is a few words, a stack is much
  more) and on waits that keep the barista (pinning).
- Open loops: "the error blames memory, but memory was nearly empty" planted in scene 2 → answered at once (the
  kernel refused a task); "how many tasks does the kernel see?" planted in scene 6 → paid off in scene 6 and the
  moral.
- Assumptions: the lesson's numbers: about 120 ms per bank answer; about 2 MB of stack per platform thread and about
  20 GB for 10,000; a container limit of 64 tasks; 42 platform threads before the failure, the JVM's own threads
  using most of the other 22 slots (drawn as 21) and the shell one; 10,000 virtual threads on 37 OS threads, 12
  carriers in a 12-processor box; the stepper's worker-1 (TID 66) and worker-2 (TID 67) and V1 to V3.

## The one picture

Top left, the rail: order slips (virtual threads) hang from a line, waiting their turn. Middle left, two baristas
(carriers worker-1, TID 66, and worker-2, TID 67); a slip sitting in a barista's box is mounted. Right, the card's bank
(the wait) and, above it, the heap, where a waiting slip's stack is parked. Bottom, the kernel's view: 64 cells, one
per task the container may have. Grey cells are the JVM's own threads and the shell, blue are payment threads, teal
are carriers, red is the task that couldn't start. Same places from start to end.

## Scene 1 · The barista who watches the milk · 0:00–0:30 · [QUESTION] [FAMILIAR]

VO: Picture a café at the morning rush, with one barista. She takes an order, starts the milk, then stands and
watches it. The line grows, and the only thing working is the machine. The café's payments program does the same.
Each payment waits about 120 milliseconds for the card's bank to say yes. A thread that waits does nothing else.

SCREEN: One barista box with an order slip; a milk timer counts to 120 ms; a line of slips grows on the rail.

## Scene 2 · One barista per customer · 0:30–1:25 · [PAIN] [JOKE:amplify] [SHOW]

VO: The easy fix is one barista per customer: one thread per payment. In Java that's a platform thread. Each one is a
task the kernel counts, with about 2 megabytes of stack set aside. Now 10,000 payments wait at once. That's 10,000
tasks and about 20 gigabytes of stack addresses, mostly to watch milk steam. In the lab, the program ran in a
container that allows 64 tasks. Watch the count. The shell and the JVM's own threads take about 22. The payments get
42. The next one fails, with an error that blames memory. But memory sat nearly empty. The kernel had refused a new
task.

SCREEN: The kernel's 64 cells draw in. Grey cells fill (shell, JVM), then blue cells count up to 42, then a red cell:
"unable to create native thread: possibly out of memory". A heap gauge beside it, nearly empty.

## Scene 3 · Never wait? · 1:25–1:50 · [BREAK] [WISH]

VO: One way out is never to wait: hand over a function to run when the answer comes, and move on. It works, but the
code turns into chains of callbacks, and when something fails, the error no longer shows the path that led there.
What we want is plain code that waits, top to bottom, without a kernel task for every wait.

SCREEN: A short callback chain, `askBank(p).thenCompose(...).thenAccept(...)`, with a red "where did it fail?".
Caption "the wish: plain code that waits, without a task per wait".

## Scene 4 · A few baristas and a rail · 1:50–2:30 · [ANALOGY] [MAP]

VO: Back to the café. Keep two baristas, and give them a rail of order slips. A barista takes a slip and starts the
milk. Then, instead of watching it, she pins the slip up by the machine, and takes the next one. When the milk is
ready, that slip goes back in line, and whichever barista is free picks it up. Map it. The baristas are a few real
threads, the kind the kernel runs. The slips are the payments. And the steaming milk is the wait for the bank.

SCREEN: The rail with slips; two barista boxes; the bank on the right. A slip moves into a barista, to the bank, back
to a spot by the machine (the heap box), back to the rail, and into the other barista. Map tags appear one by
one.

## Scene 5 · Mount, unmount, mount again · 2:30–3:20 · [NAME] [SHOW]

VO: Java has worked this way since JDK 21. The slips are called virtual threads. A virtual thread is a Java object,
not a kernel task. To run, it mounts on a carrier: an ordinary platform thread from a small pool the JVM keeps, by
default one per processor. Watch V2. It asks the bank, and waits. The JVM unmounts it: it saves V2's stack, its place
in the code, on the heap, and frees the carrier. worker-2 picks up V3 at once. The kernel noticed nothing: task 67
never stopped running. When the bank answers, V2 goes back on the rail, and mounts on whichever carrier is free
first. This time, that's worker-1.

SCREEN: Labels become "carrier worker-1, TID 66" and "carrier worker-2, TID 67"; V1 and V2 mounted, V3 on the rail.
V2 moves to the bank; its stack frames go to the heap box ("parked"); V3 mounts on worker-2. The kernel cells for 66
and 67 stay lit. The bank answers; V2 returns to the rail; V1 finishes; V2 mounts on worker-1.

## Scene 6 · The same limit, 10,000 waits · 3:20–4:00 · [PREDICT] [PAUSE] [BREAK] [SHOW] [JOKE:release]

VO: Now the lab again: the same container, the same limit of 64 tasks, and 10,000 payments, each on its own virtual
thread. How many tasks does the kernel see? Pause and guess.

(three seconds)

37. All 10,000 started and waited at once. The kernel saw the JVM's usual helpers, plus one carrier per processor,
12 in the lab box. It had no idea it was running a café. The waiting lived on the heap.

SCREEN: The rail shows "10,000 slips". Countdown. The kernel cells reset and fill: 25 grey and 12 teal, 37 in all,
with 27 empty. Caption "10,000 virtual threads, 37 tasks".

## Scene 7 · Where the café breaks: pinning · 4:00–4:35 · [GUARDRAIL]

VO: Here the café picture breaks. An order slip is a few words. A virtual thread's slip is its whole stack, copied to
the heap and back. And a few waits still hold on to the carrier. That's called pinning. In JDK 25, waiting inside a
class's static initializer, code that runs once when a class is first used, still pins. If every carrier gets
pinned, no other virtual thread in the JVM can run, like baristas each stuck holding one cup.

SCREEN: V2's stack frames drawn as a stack of blocks moving to the heap and back. Then V1 sits in worker-1 with a
red pin, "waiting inside static {}"; the same on worker-2; the rail's slips dim.

## Scene 8 · Not faster · 4:35–5:00 · [GUARDRAIL]

VO: And virtual threads aren't faster. Java's own proposal says it plainly: Virtual threads are not faster threads. They let far more tasks wait at once. So they suit a program that spends its time waiting, on a bank or a
database. A thread that's busy computing gains nothing. And make a new one per job; don't keep them in a pool.

SCREEN: Captions; the quote; "waiting: yes", "busy computing: no", "one per job, no pool".

## Scene 9 · The moral, and a check · 5:00–5:30 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So how does one program wait on 10,000 payments? It stops giving every wait its own barista. The waits sit on the
rail, a few baristas do the work, and your code still reads top to bottom. One quick check. The lab box has 12
carriers. Twelve virtual threads each wait inside a static initializer. What happens to the next virtual thread
that wants to run? Pause and think.

(three seconds)

It waits. Every carrier is pinned, so nothing else can mount until one frees up.

SCREEN: The pins go; slips flow through the two baristas. "12 carriers, 12 pinned"; countdown; the next slip stays
on the rail with a red mark; final caption "a wait should free the barista".

---

### Beat check

- QUESTION and FAMILIAR from the lesson's barista (scene 1); PAIN with real numbers and a failure (scene 2).
- The obvious fix (callbacks) and its cost, then the WISH (scene 3).
- ANALOGY + MAP (scene 4) before the NAME (scene 5), which comes with the SHOW.
- PREDICT with PAUSE breaks "one thread, one task" (scene 6).
- GUARDRAIL: the analogy's breaking points and pinning (scene 7), not faster (scene 8); MORAL and a check answerable
  from the pinned carriers (scene 9). Light moments: watching milk steam (0:55), the kernel running a café without
  knowing (3:55), baristas each stuck holding one cup (4:30).

### Accuracy notes for the producer

- The pain numbers are the lesson's ThreadFlood run under `--pids-limit 64`: 42 platform threads, then
  `pthread_create failed (EAGAIN)` and an `OutOfMemoryError` ("unable to create native thread: possibly out of
  memory or process/resource limits reached"); 63 OS threads in the JVM; the container's shell used one slot. The
  video draws 21 JVM threads and 1 shell. The exact count varies between runs (42 and 50 in the lesson).
- The virtual run is the lesson's `ThreadFlood virtual 10000`: "OS threads in this JVM: 37" (26 in another run). The
  video draws 12 carriers and 25 other JVM threads; it doesn't show the shell's slot in this run.
- About 2 MB of stack per platform thread is the lab box's `stacksize: 2040k`; 20 GB for 10,000 is the lesson's
  figure for reserved addresses, not memory used.
- The video calls the carriers' pool "a small pool the JVM keeps"; the lesson names it `ForkJoinPool`.
- The stepper's names and TIDs (worker-1 TID 66, worker-2 TID 67, V1 to V3) are from the lesson's demo. Which
  carrier V2 mounts on next is up to the scheduler; the video shows worker-1, as the stepper does.
- Pinning in JDK 25: a wait in a class initializer, waiting for another thread to initialize a class, and waiting in
  native code. The video names the first. `synchronized` pinned until JEP 491 fixed it in JDK 24; the video leaves it
  to the lesson.
- The quote is from JEP 444. The `Semaphore` advice and `jcmd` thread dumps are left to the lesson.
- Spoken forms via `SAY`: JDK as "J D K", TID numbers as "task 67", V2 as "V two", worker-2 as "worker two".
