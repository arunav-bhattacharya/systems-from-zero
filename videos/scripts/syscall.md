# One door into the kernel: what happens inside one print

- Slug / scene: `syscall`, `videos/scenes/syscall.py:Syscall`
- Lesson: `os-01`, section 2, "Following one request into the kernel and back"
- Audience / level: a complete newcomer. Can read a little code; has heard the words kernel, user mode and
  system call once, in the lesson's first section, and nothing else about processors.
- Length: 5:09 (~800 words of narration at the Kokoro voice's ~170 wpm, plus two pauses and silent builds)
- Poster: `POSTER=229` (just after the return: the whole trip on screen, x0 = 3, "ok" on the terminal)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: no program may touch the screen, yet `println` prints and returns at once. What
  happens inside that one line?
- Misconception to steelman and break: "asking the kernel is an ordinary function call into the kernel's code".
  Broken by a jump that lands past the permission check (the customer who climbs over the counter). A second wrong
  model, "the kernel does what the slip says", is broken by the prediction about what a sneaky program could put
  in x1.
- Concept chain: no program can touch hardware → a plain call into the kernel would skip the check → one
  instruction that switches mode, saves the place and jumps to a door the kernel chose (a trap) → which service,
  and with what, travels in registers → the kernel checks every address → the answer comes back in x0, and errors
  are negative numbers (left to the lesson) → each trip is fast but not free (hardest last: the guardrail on cost)
- Analogy family: the lesson's bank. The customer is the program, the vault is the hardware, the teller is the
  kernel, the glass is user mode, the slip is the system call, and the form number printed on the slip is the
  system call number. It breaks on speed and on who does the work (no queue, no teller of its own).
- Open loops: "what happens inside that one line?" planted in scene 1 → answered in scene 10; "the program must
  never choose where it lands" planted in scene 3 → paid off by the trap in scene 4 and by the check question.
- Assumptions: the lesson's arm64 numbers (write is 64, read is 63, readv is 65; x8 holds the number, x0 to x2 the
  inputs; `svc #0` and `eret`); about 150 ns per `getpid` in the lab box; the million-call figure is arithmetic
  (150 ns × 1,000,000 = 150 ms), labelled as such by "about".

## The one picture

After a short hook, one diagram for the whole video. Top band, blue: user mode, with the program box on the left
and the registers (the slip) on the right. Bottom band, gold: kernel mode, with the entry point (the door) under the
program, the system call table in the middle and the code for write on the right. Below both, a grey hardware strip:
network card, disk, terminal. The trap arrow (yellow, `svc #0`) goes down through the gap from the program to the
entry point; the return arrow (green, `eret`) comes back up beside it. Yellow means "on its way" or "look here",
green means done and correct, red means refused, wrong or an error. Same places from start to end.

## Scene 1 · The hook · 0:00–0:30 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: In Java, System.out.println looks like any other method call. It returns almost at once. But no program on your
laptop can touch the screen, the disk or the network. Not even this one. So what happens inside that one
line? It ends up asking the kernel, the one program that may touch the hardware. Let's follow that request in, and back out.

SCREEN: The program box with `System.out.println("ok")`, top left. The hardware strip at the bottom (network card,
disk, terminal). A direct arrow from the program to the terminal turns red and is crossed out. Caption "what happens
inside that one line?".

## Scene 2 · The bank, mapped · 0:30–1:05 · [ANALOGY] [MAP]

VO: First, a picture from earlier in this lesson: a bank. Customers can't walk into the vault. They fill in a slip,
push it under the glass, and a teller checks it, does the work and slides back the result. Map it. Your program is
the customer. The vault is the hardware. The teller is the kernel, working in kernel mode, where the processor runs
every instruction. The glass is user mode. In user mode, the processor refuses the instructions that talk to
devices. And the slip is a system call: a request with a number that names the service.

SCREEN: The two bands draw in. Tags appear one by one: "the customer" over the program, "the vault" by the
hardware, "the teller" in the kernel band, "the glass" in the gap between the bands. Caption "the slip: a system
call, a request with a number that names the service".

## Scene 3 · The obvious idea, broken · 1:05–1:40 · [PAIN] [BREAK] [JOKE:release] [LOOP-PLANT]

VO: So how does the slip get under the glass? The obvious idea is an ordinary function call. The kernel is code.
Jump to its write function and run it. But look at what that allows. The kernel's code checks permissions first,
then does the work. If a program may jump to any address, it can land right past the check, and run the rest with
full power. That's a customer who climbs over the counter. Banks have a word for that customer, and it isn't
customer. So the program must never choose where it lands.

SCREEN: A temporary block in the kernel band, "kernel code for write": 1 check: is this allowed? 2 do the work. 3
hand back the result. A grey arrow from the program to line 1, then a red arrow to line 2, skipping line 1; the
check line dims; a red cross. Caption "the program must never choose where it lands".

NOTE: The joke comes after the break is shown, and is cashed back at once.

## Scene 4 · One door: the trap · 1:40–2:15 · [WISH] [SHOW] [NAME]

VO: What we want is one door, and the kernel decides where it leads. The processor has exactly that: one special
instruction that does three things at once. It switches to kernel mode. It saves where the program was. And it jumps
to an entry point the kernel picked when the computer started. The program can't choose where it lands. This switch
is called a trap. On arm64, the chip family in an Apple Silicon Mac, the instruction is svc.

SCREEN: The entry point box appears under the program. Captions one per step: "1. switch to kernel mode" (the
kernel band brightens, the user band dims), "2. save where the program was" ("place saved" appears beside the
program), "3. jump to the entry point the kernel chose" (a dashed arrow to the entry point). Then "a trap" and
"arm64: svc   (x86-64: syscall)".

## Scene 5 · The slip, in registers · 2:15–2:55 · [SHRINK] [MAP]

VO: One door for everything means the slip must say which service, and with what. Let's shrink it to the smallest
request: write 3 bytes, o, k and a newline, to file descriptor 1. A file descriptor is a small number a program uses
to name something it has open. 1 is standard output, usually your terminal window. The C library's write function,
still in user mode, fills in the slip, in registers: the few dozen small storage slots inside the processor. The service number goes in x8. Like the form number printed on
a bank slip, 64 means write. The three inputs go in x0, x1 and x2. x1 holds the address of the bytes, called the
buffer.

SCREEN: The program's code becomes `write(1, "ok\n", 3)`. The registers panel ("registers", tag "the slip")
fills: x8 = 64, then x0 = 1, x1 = buf, x2 = 3.

## Scene 6 · Through the door · 2:55–3:10 · [SHOW]

VO: Then it runs svc. The processor saves its place, switches to kernel mode and lands at the entry point. The
kernel reads x8, finds entry 64 in its system call table, and runs the code for write.

SCREEN: The yellow trap arrow with `svc #0`; "place saved"; band fills switch. The table appears (63 read, 64 write,
65 readv); x8 pulses; row 64 is boxed; an arrow to "the code for write".

## Scene 7 · What could x1 hold? · 3:10–3:40 · [PREDICT] [PAUSE] [BREAK] [SHOW]

VO: Before it copies anything, look at x1 again. It's an address, and the program wrote it. What could a sneaky
program put there? Pause and guess.

(three seconds)

The address of the kernel's own memory. Then the kernel would write out its own secrets. So the code for write checks first. Is descriptor 1 open for writing? Is the buffer really the program's own
memory? An address from user mode could point anywhere. The kernel checks every one.

SCREEN: x1 glows; countdown. x1 turns red, with "x1: the kernel's own memory" beside it, then back to blue. Two checks with green
ticks under the code for write. Caption "an address from user mode could point anywhere: the kernel checks every
one".

## Scene 8 · Back out · 3:40–4:00 · [SHOW]

VO: Only then does it copy the 3 bytes out to the terminal. It puts the result in x0: 3 bytes written. Then it runs
eret, short for exception return. The processor drops back to user mode, at the instruction right after svc. The C
library returns 3, and your program carries on. It never touched the hardware.

SCREEN: The checks fade; an arrow to the terminal and "ok" appears there. x0 becomes 3 (green). The green `eret`
arrow up; band fills switch back; "place saved" goes; the program glows green.

## Scene 9 · Where the bank breaks, and the cost · 4:00–4:35 · [GUARDRAIL] [JOKE:pivot]

VO: Here the bank picture breaks. A teller takes minutes, and serves other people while you wait. There's no queue
here, and no pen on a little chain. The kernel does the work on your program's own processor,
and it's quick. In the lab box, one tiny call, getpid, which asks for the program's own process
number, takes about 150 nanoseconds. A nanosecond is a billionth of a second. Once, that's nothing. A million times,
it's about 150 milliseconds spent going in and out. So a program that writes each line of its notes straight to a file
pays the trip for every line. Gather small writes into bigger ones, and cross less
often.

SCREEN: Caption "a teller: minutes, and a queue" then "a system call: your own processor, about 150 ns". The trap
and return arrows pulse in turn. Under the code for write: "one trip in and out: about 150 ns", then "a million
trips: about 150 ms". Caption "gather small writes, cross less often".

## Scene 10 · The moral, and a check · 4:35–5:09 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So what happens inside that one print? The library fills in a slip in the registers, svc takes it through the
one door, and the kernel checks everything before it answers in x0. One door, one slip, and every
address checked. One quick check. Suppose the slip says 63 in x8, instead of 64. Which service does the kernel run?
Pause and look at the table.

(three seconds)

Read. Entry 63 is read. The number on the slip picks the service, and the program never picks the address.

SCREEN: The registers, the trap arrow, the table row and x0 glow in turn. Caption "one door, one slip, every address
checked". x8 becomes 63 (yellow); countdown; row 63 boxed in green; final caption.

---

### Beat check

- QUESTION from a familiar line of code (scene 1); ANALOGY + MAP (scene 2) before anything is named.
- The obvious fix and its BREAK (scene 3); WISH, SHOW, then NAME (trap, scene 4).
- SHRINK to one tiny request (scene 5); PREDICT with PAUSE and a second wrong model broken (scene 7).
- GUARDRAIL with the analogy's breaking point and the cost (scene 9); MORAL, RECAP and a check question answerable
  from the table (scene 10). Light moments: the customer who climbs over the counter (1:35), no pen on a little
  chain (4:05). Whisper hears "Banks" as "It does" in the full video but correctly in isolation, so it was kept.

### Accuracy notes for the producer

- Numbers are arm64 Linux's (the lab box): `write` 64, `read` 63, `readv` 65; the number in `x8`, inputs in `x0`
  to `x2`, the result in `x0`; `svc #0` traps from EL0 to EL1 and `eret` returns to the instruction after it. The
  video says "user mode" and "kernel mode" and leaves EL0 and EL1 to the stepper.
- "The entry point the kernel picked when the computer started" is the exception vector, named in the lesson.
- The video's `println("ok")` stands for the lesson's "Java code ends up calling the C library's write"; the JVM's
  own path to `write` is not shown.
- The kernel's checks are shown as two: the descriptor is open for writing and the buffer is the program's own
  memory, as in the lesson's stepper. The error a bad address gets is left out.
- Errors (negative numbers in `x0`: -2 for a missing file, -1 and `errno` = `ENOENT` from the C library) were cut for
  length and are left to the lesson and its Try it.
- About 150 ns is one `getpid` round trip in the lab box; real costs vary by machine. 150 ms for a million is
  arithmetic on that figure.
- "Gather small writes" is the lesson's point about a logger (said as "a program that writes each line of its notes") that writes each line straight to its file; the
  buffering itself is not shown.
- Spoken forms via `SAY`: x8 as "ex eight", svc as "S V C", eret as "E ret", errno as "air no", ENOENT as "E no
  ent", getpid as "get pid", arm64 and x86-64 in words.
