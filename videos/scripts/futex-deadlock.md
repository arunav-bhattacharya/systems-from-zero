# The lock that rarely calls the kernel: a futex, from a café bathroom

- Slug / scene: `futex-deadlock`, `videos/scenes/futex_deadlock.py:FutexDeadlock`
- Lesson: `os-05`, section 1, "A futex keeps the kernel out until someone has to wait"
- Audience / level: a complete newcomer. Has met threads, the scheduler and compare-and-swap in the lesson's first
  section; knows nothing about system calls beyond "a request to the kernel".
- Length: 5:33 (~915 words of narration; Kokoro speaks about 175 words a minute, plus two pauses and builds)
- Poster: `POSTER=157` (T2 asleep in the wait queue, the note on the door, one system call so far)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: only the kernel can put a thread to sleep, so doesn't every lock have to ask the kernel?
  And then how can a lock nobody else wants be nearly free?
- Misconception to steelman and break: (1) "a lock must go through the kernel every time", priced at 8 ms against
  about 308 ms for a million pairs; (2) "futex wait could just put you to sleep", broken by the lost wake-up.
- Concept chain: a lock word taken with one compare-and-swap → the loser must sleep, and only the kernel can do that →
  asking the kernel every time is nearly 40 times slower → ask only when the door is locked, and leave a note (the
  value 2) → futex wait must check the word, or a wake-up gets lost (hardest last)
- Analogy family: the café's one bathroom (from the lesson): the door's Vacant sign, the counter, the barista's list of
  names, a note on the door that someone is waiting, the barista glancing at the door before writing a name.
- Open loops: "how many system calls for a million locks?" planted in scene 1 → paid off in scene 8; the frozen card
  reader (the lesson's opening) teased in the last line → section 2 of the lesson.
- Assumptions: T1 is the refund and T2 the payment, as in the lesson's stepper. Numbers are the lesson's (150 ns a
  system call, 8 ms for a million pairs, nearly 40 times slower; strace counts 1 and 2,749 with 1,042 EAGAIN).

## The one picture

Centre: the lock word, drawn as the bathroom door (blue), its value on the plate (0 green free, 1 red taken, 2 red
taken with a gold "someone waits" note on the door), its meaning under the door. Left: T1, the refund (teal), and T2,
the payment (purple), each with a state line. A dashed line splits the program's memory (above) from the kernel
(below). In the kernel: the wait queue, "the barista's list" (white), where T2 sleeps as a purple chip. Right column:
the system-call counter (gold) and the calls made. Yellow dots are compare-and-swaps; arrows into the kernel are
system calls. Same places and colours from start to end.

## Scene 1 · The question · 0:00–0:27 · [QUESTION] [LOOP-PLANT]

VO: The café's payments program takes a lock every time it changes a balance. Picture one thread doing that a million
times, while no other thread ever wants the lock. Only the kernel, the core of the operating system, can put a thread
to sleep or wake it. A request from a program to the kernel is called a system call. So how many system calls does
this loop make? Make a guess, and hold on to it.

SCREEN: Title card. "one thread: lock, change the balance, release", a counter ticking to "× 1,000,000", "no other
thread ever wants the lock". "only the kernel can put a thread to sleep, or wake it" (teal), "system calls: ?" (gold).

## Scene 2 · The lock word, and the loser · 0:27–0:59 · [FAMILIAR]

VO: The lock is one number in the program's memory, the lock word. 0 is free, and 1 is taken. T1, a refund, and T2, a
payment, both want it. A thread takes it with compare and swap, one instruction: if this holds 0, put 1 in it, and tell
me whether you did. T1 goes first, and gets it. T2 finds 1, and fails. Trying again in a loop would burn its turn on
the CPU, while T1 isn't even running. It should sleep instead, and only the kernel can do that.

SCREEN: The door-shaped lock word draws in with 0 (free); it flips to 1 and back. T1 and T2 appear. A dot runs from T1
to the word ("0 to 1?"), the word turns 1, T1 "has the lock". T2's dot runs, red cross, "trying, and trying again"
with red dots; T1 dims "has the lock, not running". The dashed line and "the kernel" draw in; T2 "should sleep".

## Scene 3 · Ask the kernel every time · 0:59–1:31 · [PAIN] [WISH] [JOKE:amplify]

VO: The obvious design asks the kernel every time: once to take the lock, and once to release it. A system call costs
about 150 nanoseconds. A million free locks, taken and released inside the program, take 8 milliseconds. Two system
calls a pair add about 300 more. Nearly 40 times slower, for a wait that never happens. It's
like asking the barista's permission to use an empty bathroom. Wouldn't it be nice if the kernel stayed out of it,
until someone really had to wait?

SCREEN: An arrow from T1 into the kernel; two dots, the counter goes 1, 2. Right column: "a million pairs, inside the
program: 8 ms" (a tiny green bar) and "plus two system calls each: about 308 ms" (a long red bar, dots streaming).
Captions with the costs; the wish in yellow.

NOTE: The barista's-permission line is the light moment and it opens the analogy.

## Scene 4 · The café bathroom · 1:31–2:07 · [ANALOGY] [MAP]

VO: In a café, you see Vacant on the bathroom door, go in and lock it, and later you come out.
Nobody asks anyone. Only when the door is already locked do you go to the counter, and ask the barista to call you
when it's free. And you leave a note on the door, so whoever comes out knows someone is waiting.

Let's map it. The door's sign is the lock word, in the program's own memory. Each customer is a thread. The barista is
the kernel, and the list of names at the counter is its wait queue. And the note is a third value. 2 means taken, and
someone is waiting.

SCREEN: A knob appears: the word is a door, "the bathroom door". T1 goes in (1) and out (0). T1 in again; T2's dot hits
the locked door; "the barista's list" appears in the kernel, "empty"; T2 "waiting to be called". The note "someone
waits" lands on the door (2). Mapping: the title becomes "the lock word", the memory label pulses, the thread cards
pulse, "the kernel" pulses, the list becomes "the kernel's wait queue", the 2 pulses.

## Scene 5 · One round, counting system calls · 2:07–3:01 · [SHRINK] [SHOW]

VO: Now one round, counting system calls. T1 wants the lock. The word is 0, so one compare and swap makes it 1. T1 is
in, and the kernel never heard about it. T2's compare and swap expects 0, finds 1, and fails. So T2 sets the word to 2,
the note, and makes the first system call: futex wait. Put me to sleep, but only if the word still holds 2. The kernel
checks, and puts T2 on the wait queue. T2 sleeps, and uses no CPU at all. T1 finishes. It sets the word to 0, and looks
at the old value. It was 2, so T1 makes the second call: futex wake, wake one sleeper. The kernel takes T2 off the
queue. T2 tries again and gets the lock. It writes 2, to be safe: others may still be asleep.
One wait cost two system calls. With nobody waiting, it would have cost none.

SCREEN: Counter "system calls: 0". T1's dot: "got it", word 1, counter still 0. T2's dot: "found 1", cross. Word 2 with
the note; a purple arrow into the kernel, `FUTEX_WAIT(word, 2)` in the log, counter 1. A purple T2 chip moves down into
the queue; T2 dims, "asleep in the kernel". T1's dot back, word 0, "old value: 2"; a teal arrow into the kernel,
`FUTEX_WAKE(word, 1)`, counter 2. T2's chip rises; T2's dot; word 2. Caption "one wait: two system calls. nobody
waiting: none".

NOTE: Clean walkthrough, no jokes.

## Scene 6 · The name · 3:01–3:12 · [NAME]

VO: This is called a futex, short for fast user space mutex. Mutex is another name for a lock. User space is where
ordinary programs run, outside the kernel.

SCREEN: Captions "futex: fast user-space mutex", "mutex: another name for a lock", "user space: ..."; the memory
label pulses.

## Scene 7 · The lost wake-up · 3:12–4:06 · [BREAK] [PREDICT] [PAUSE] [NAME] [JOKE:release]

VO: Why does futex wait check the word before it sleeps? Let's be fair to a version that doesn't. T1 holds the lock, and
T2 sets the word to 2. But before T2's call reaches the kernel, T1 finishes. It sets 0, sees the old 2, and calls wake.
The queue is empty, so nobody wakes up. Now T2's call arrives. What happens to T2? Pause and guess.

(three seconds)

T2 falls asleep, and nobody will ever wake it. The lock is free, and T2 waits outside an empty bathroom, forever.
That's called a lost wake-up. With the check, the kernel sees 0 instead of the 2 that T2 expected, and won't put it to
sleep. The call fails at once with an error called EAGAIN, try again, and T2 takes the lock. It's the barista glancing
at the door once more, before writing your name down.

SCREEN: Caption "a futex wait with no check: just sleep". Word 1, then 2. A purple dot crawls along T2's arrow and stops
partway. Word 0; a teal wake arrow, counter 1, the empty queue flashes red, log "FUTEX_WAKE: woke nobody". The purple
dot reaches the kernel, counter 2. Countdown. The T2 chip sinks into the queue, "asleep, forever" (red), "free" pulses
under the door, caption "a lost wake-up". Then with the check: the chip stops at the queue's edge, the 0 pulses, it
bounces back, log "FUTEX_WAIT: EAGAIN", T2 takes the lock (2).

NOTE: Waiting outside an empty bathroom forever is the light moment, said right after the failure, and the next line
cashes it back into the check.

## Scene 8 · Count the calls · 4:06–4:38 · [SHOW] [LOOP-PAYOFF] [GUARDRAIL]

VO: Now, your guess from the start. strace is a tool that counts every system call a program makes. One thread, a
million locks nobody else wanted: 1 futex call. And that one isn't even the lock: it's the main thread, waiting for the
worker to finish. Four threads, all fighting over one lock: 2,749 calls. And 1,042 of them failed with EAGAIN: the
check, catching the same race, over and over. A lock is only free while nobody else wants it.

SCREEN: Right column: "1 thread, a million locks / futex calls: 1 / (the main thread waiting for the worker)", then
"4 threads, one lock / futex calls: 2,749 / 1,042 failed with EAGAIN".

## Scene 9 · Where the café breaks · 4:38–4:53 · [GUARDRAIL] [JOKE:is-the-explanation]

VO: Where the café picture breaks: fairness. A barista calls names in order. A woken thread has to race any newcomer for
the compare and swap, and the newcomer, already running, often wins. The kernel wakes you up. It doesn't save your
place.

SCREEN: T2's chip rises from the queue; a green "T3: a newcomer" arrives from the right and its dot takes the door
first (1); T2's chip sinks back, "back to sleep". Caption: "the kernel wakes you up; it doesn't save your place".

## Scene 10 · The moral, and a check · 4:53–5:33 · [MORAL] [PRINCIPLE] [PREDICT] [PAUSE] [LOOP-PLANT]

VO: So the moral of the story: ask the barista only when the door is locked. A free lock costs one instruction, and only
waiting reaches the kernel. One quick check. T1 releases the lock, and the old value was 1, not 2. Does T1 call the
kernel? Pause and think.

(three seconds)

No. 1 means no note on the door, so nobody is waiting. Releasing the lock is one instruction. And when waiting is this
cheap, a thread that waits forever costs nothing either. That's how the café's card reader froze, and it's next.

SCREEN: The moral in yellow; T1 takes the word (1). Counter 0; T1 releases, "old value: 1"; countdown; "done, no system
call", a tick by the counter. Both threads dim, "waiting for T2" and "waiting for T1"; the moral returns.

---

### Beat check

- Opens with QUESTION (scene 1): a million locks, how many system calls? Planted, paid off in scene 8.
- FAMILIAR (scene 2): the lock word and compare-and-swap from the lesson's first section.
- PAIN and WISH (scene 3) before the analogy; ANALOGY and MAP (scene 4) said out loud, part by part.
- SHOW (scene 5), counting calls; NAME after it (scene 6: futex, mutex, user space; scene 7: lost wake-up, EAGAIN).
- BREAK with PREDICT and PAUSE (scene 7): the check-free futex wait loses a wake-up.
- GUARDRAIL: the cost under contention (end of scene 8), where the analogy breaks (scene 9, fairness). MORAL and a
  check (scene 10).
- Light moments: the barista's permission for an empty bathroom (1:25), outside an empty bathroom forever (3:40), the
  kernel doesn't save your place (4:50).

### Accuracy notes for the producer

- "About 308 ms" is the lesson's arithmetic made explicit: 8 ms for a million uncontended pairs plus 2 × 150 ns × a
  million = 300 ms, 38.5 times slower ("nearly 40 times"). It is not a measured run.
- The word values and steps follow glibc's mutex as the lesson describes it (Drepper, "Futexes Are Tricky"): CAS 0 to 1;
  on failure swap in 2 and `FUTEX_WAIT(addr, 2)`; release swaps in 0 and calls `FUTEX_WAKE(addr, 1)` only if the old
  value was 2. A woken thread swaps in 2 and owns the lock if the old value was 0.
- The check-free futex wait is a thought experiment; the real call always compares the word and sleeps in one atomic
  step.
- strace counts are the lesson's (`strace -f -c -e trace=futex`, C counter): 1 call for one thread (from
  `pthread_join`), 2,749 calls with 1,042 errors for four threads (four million locks in all). Counts change between
  runs.
- The newcomer T3 in scene 9 is invented for the picture of unfairness; the lesson says a woken thread races "any
  newcomer". Spinning before sleeping (adaptive mutexes), Java's `ReentrantLock` and `synchronized` (the same CAS-then-
  futex path) and the JVM's own startup futex calls are left to the lesson.
- The deadlock (refund and payment each holding one account lock) is the lesson's next section; the last frame only
  teases it.
