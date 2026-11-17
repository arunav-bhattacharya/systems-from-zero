# A container is a process in a very good disguise

- Slug / scene: `namespaces-cgroups`, `videos/scenes/namespaces_cgroups.py:NamespacesCgroups`
- Lesson: `os-12`, section 0, "Looking from outside: a container is a process on a shared kernel"
- Audience / level: a complete newcomer. Has heard the word container; knows nothing about kernels, processes or
  virtual machines.
- Length: 4:28 (~700 words of narration, plus two guesses and silent builds)
- Poster: `POSTER=187` (both containers, the four features and the one kernel with its shared parts)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: if each container is its own boxed-off space, how did a bug in one box break the box
  next door?
- Misconception to steelman and break: "a container is a small computer, with its own name, files and process
  number 1" (broken by looking from both sides: `sleep` is PID 1 inside and 40037 on the host, `NSpid: 40037 1`,
  and `uname -r` prints the same kernel in both places)
- Concept chain: a container from both sides is one process → the problem containers solve → a virtual machine each
  works and costs a kernel each → one kernel plus four features (namespaces, cgroup, capabilities and seccomp,
  overlay) → one of every kernel part underneath → the shared kernel is the limit → the nightly job had no meter
  for tasks (hardest last)
- Analogy family: a block of flats. Walls and a private letterbox (namespaces: your own view; every tenant can number
  their door 1), the meter and a fuse that trips for this flat only (a cgroup), house rules (capabilities and
  seccomp), furniture that belongs to the building while your changes are yours (the overlay). Where it breaks:
  real flats have their own wiring; containers share the one kernel, wiring and all.
- Open loops: "how did a bug in one box break the box next door?" planted in scene 1 → answered in scene 7, and
  checked in scene 8
- Assumptions: PID 40037, `NSpid: 40037 1` and `6.12.76-linuxkit` are the lesson's Try it output. The tasks meter
  in the kernel bar stands for whatever shared limit the job used up; the lesson says only "something they share"
  and names `pids.max` as the fix. The 20-task limit is the lesson's cgroup section (`pids.max` 20).

## The one picture

A dashed outline for the one computer (the host). Along the bottom, one wide blue bar: the one kernel, with a tasks
meter on its right end. Above it, two containers: "payments" on the left (blue threads) and "nightly job" in the
middle (gold copies). On the right, the host's own view (its process list) when we look from outside. The payments
container later carries the four flat features as four small labels around its program. Red is a failure or the
shared kernel's weak spot; green is a meter that worked.

## Scene 1 · The box next door · 0:00–0:35 · [QUESTION] [LOOP-PLANT]

VO: One computer runs two programs for the coffee-shop payments company: the payments program, and a nightly job
that adds up what each shop is owed. Each runs in its own container, a boxed-off space with its own name, files and
list of running programs. One night, a bug makes the job copy itself, over and over. Minutes later, the payments
program fails too, in a container nobody touched. It can't start a thread, a new line of work. How did a bug in one
box break the box next door?

SCREEN: Title card. The host outline, the kernel bar, two containers with their programs. The job's gold dot copies
itself until its box is full, while the tasks meter in the kernel bar fills to red. A new blue dot in the payments
container gets a red cross: "can't start a thread". A yellow "?".

## Scene 2 · Look from both sides · 0:35–1:30 · [FAMILIAR] [PREDICT] [PAUSE] [SHOW] [BREAK] [JOKE:release]

VO: It's easy to think a container is a small computer, with its own name, its own files, even its own process
number 1. Let's look at one from both sides. Here's a container that runs sleep, a program that waits and does
nothing. Inside, ps, the command that lists running programs, shows sleep as process number 1. Now look from the
host, the computer that runs the containers. What number does sleep have there? And does the container have a
kernel of its own, the core of the operating system? Pause and guess. (three seconds) On the host, the same process
is number 40037. Its status file lists both numbers, 40037 and 1. And the kernel version is the same on both sides.
There's no second kernel and no second computer. Just one process in a very good disguise. A container is a process.

SCREEN: The two containers leave. A container "sleep" on the left, with "inside: ps" and "PID 1 sleep". On the right,
"on the host: ps" with "PID ?". Countdown bar. Then "PID 40037 sleep", a line joining it to PID 1 ("the same
process"), "NSpid: 40037 1", and "uname -r: 6.12.76-linuxkit" on both sides, each with an arrow down into the one
kernel bar, which now reads "one kernel · 6.12.76-linuxkit".

## Scene 3 · What containers are for · 1:30–2:05 · [PAIN] [WISH]

VO: So what are containers for? An old problem: run many programs on one computer, and let each act as if it were
alone. The payments program shouldn't see the job's processes or files. A memory leak in one shouldn't get the other
killed. And a program an attacker breaks into shouldn't change the computer's clock. The simplest complete answer is
a virtual machine for each program: a pretend computer with its own kernel. It works, and every program pays for a
kernel, a start-up and a slice of memory.

SCREEN: The two containers return. Captions for the three wishes. Each container gets its own small kernel bar
inside ("its own kernel"), and the costs appear: "per program: a kernel, a start-up, memory set aside".

## Scene 4 · A block of flats · 2:05–3:05 · [ANALOGY] [MAP] [NAME] [JOKE:pivot]

VO: Containers keep one kernel, and use four things it already has. Picture a block of flats. The walls and a
private letterbox: a tenant sees only their own rooms and post, and can number their door 1. Every tenant can be
number 1, which is great for morale. Those are namespaces: each container gets its own view, its own process
numbers, computer name, network and list of disks. The meter: so much power and water, and the fuse trips for this
flat only. That's a cgroup: a cap on how many tasks, how much memory and CPU time. The house rules: hang pictures,
but don't touch the boiler. Those are capabilities and seccomp: what the process may ask the kernel to do. And the
furniture belongs to the building, but what you change is yours until you move out. That's the overlay: the
container's own files, laid over a shared, read-only image.

SCREEN: The small kernels fold into the one kernel bar. On the right, under "a flat's four features", four rows
appear one at a time, each showing the flat word first and the name once it is said: "namespaces / walls,
letterbox: what it sees", "a cgroup / meter, fuse: how much it uses", "capabilities, seccomp / house rules: what it
may ask for", "the overlay / furniture: its own files". A green "1" appears by the payments program on "number their
door 1".

## Scene 5 · One of each part · 3:05–3:18 · [SHOW]

VO: Underneath, there's still one of each part: one scheduler picking what runs, one page cache, one OOM killer, the
part that ends a process when memory runs out.

SCREEN: The kernel bar's right end reads "one scheduler · one page cache · one OOM killer"; arrows from both
containers into it.

## Scene 6 · Where the flats picture breaks · 3:18–3:50 · [GUARDRAIL] [BREAK of the analogy]

VO: And here the flats picture breaks. Real flats share foundations, but each has its own wiring. Containers share
the one kernel, wiring and all. So a kernel bug that one container can reach is a bug in every container on the
machine. That's why Docker's filter blocks dozens of requests a program could make to the kernel. When you need a
hard wall, you need a virtual machine.

SCREEN: A red crack in the kernel bar; red arrows from both containers reach it. Captions: "one kernel: a bug one
container can reach is in every container", "Docker's filter blocks dozens of system calls", "a hard wall: a
virtual machine".

## Scene 7 · Back to the nightly job · 3:50–4:10 · [LOOP-PAYOFF]

VO: Back to the nightly job. Both containers are processes on one kernel. Every copy of the job is a task, and so is
every thread. Nobody put a meter on the job's flat for tasks. So its copies used up something the flats share, and
the payments program couldn't start a thread.

SCREEN: The opening replays: the job's copies fill its box, the tasks meter fills, and the payments thread is
crossed out. Caption: "no meter on the job's flat for tasks".

## Scene 8 · The moral, and a check · 4:10–4:35 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So a container is a process: walls, a meter, house rules and its own furniture, on a kernel it shares with
everyone else. One quick check. Put a meter on the job's flat: at most 20 tasks. The bug strikes again. Who notices:
the job, the payments program, or both? Pause and think. (three seconds) Only the job. Its fuse trips at 20, and its
next copy fails. Next door, the payments program starts its threads and never hears a thing.

SCREEN: Caption for the moral. The job's copies are cleared and the tasks meter drops; a green meter "pids.max: 20"
appears on the job's container. Countdown bar. Then the copies grow to 20 and stop, the next one gets a red cross
("copy 21: EAGAIN"), the tasks meter stays low, and a new payments thread gets a green tick.

---

### Beat check

- Opens with QUESTION (scene 1), from the lesson's nightly job.
- FAMILIAR misconception steelmanned and broken by PREDICT, PAUSE and SHOW (scene 2), before any of the four names.
- PAIN and WISH (scene 3), ANALOGY and MAP with each NAME after its flat feature (scene 4).
- GUARDRAIL and the analogy's break (scene 6); LOOP-PAYOFF (scene 7); MORAL and a PREDICT check last (scene 8).
- Light moments: "one process in a very good disguise" (1:25), "great for morale" (2:20), "never hears a thing"
  (4:33).

### Accuracy notes for the producer

- PID 40037, `NSpid: 40037 1` and `6.12.76-linuxkit` on both sides are the lesson's Try it on a Mac (the host is the
  Docker VM); numbers differ on another machine.
- The lesson doesn't say which shared limit the nightly job exhausted, only that it "used up something they share"
  and that a `pids.max` on the job's cgroup would have contained it. The video shows a generic tasks meter in the
  kernel bar.
- With `pids.max` at 20, the lesson's `forks.c` gets 19 children and its 20th `fork` fails with `EAGAIN` (the
  starting shell is the 20th task). The video draws 20 tasks and fails the next copy.
- "Dozens of requests" is the section's "dozens of system calls" (io_uring among them); "a hard wall: a virtual
  machine" is the lesson's recap.
- Left to the lesson: the eight namespace kinds and `unshare`, cgroup files and the OOM killer in a group, root,
  capabilities and the overlay's copy-up, Java sizing itself from the limits, and why Docker on a Mac needs a VM (the
  section's aside).
