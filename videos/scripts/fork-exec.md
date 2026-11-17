# How a shell starts ls and sends its output to a file: fork, exec and wait

- Slug / scene: `fork-exec`, `videos/scenes/fork_exec.py:ForkExec`
- Lesson: `os-02`, section 1, "Starting a program: fork makes a copy, exec swaps the program"
- Audience / level: a complete newcomer. Has met the kernel and the process (a running program plus the kernel's
  notes about it, with a PID) in the lesson's first section. Has typed a command in a terminal, maybe.
- Length: 4:43 (~765 words of narration at the Kokoro voice's ~175 wpm, plus two pauses and silent builds)
- Poster: `POSTER=190` (ls in the child, descriptor 1 on listing.txt, the parent asleep in wait)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: `ls os > /tmp/listing.txt` puts the list in a file, and `ls` knows nothing about
  files. How does the shell do that?
- Misconception to steelman and break: "starting a program should be one call, spawn this program". Broken by the
  form that grows a new setting for every kind of setup. A second wrong model, "exec starts a new process", is
  broken by the prediction: after exec, the PID, the parent and the open files are all still there.
- Concept chain: one spawn call needs a setting for everything → split it in two, with your own code between →
  fork copies the process (two answers from one call; memory shared until written) → in the gap the child points
  descriptor 1 at the file → exec swaps the program and keeps the PID, parent and open files → wait collects the
  exit status → rules: exec returns only on failure, a parent waits (hardest last)
- Analogy family: the lesson's family words. The shell is the parent, the new process is its child; fork is a birth
  where the child arrives as an exact copy (the picture breaks here: no real child is born with its parent's
  memories); wait is the parent waiting up to hear how it went. The grim word for a dead child nobody has asked
  about is left to the next section.
- Open loops: "how does the shell do that?" planted in scene 1 → answered in scene 10; "the dead child has a grim
  name" planted in scene 8 → paid off in the lesson's next section.
- Assumptions: the lesson's stepper run: tinysh is PID 43, the child is PID 45, the command is
  `ls os > /tmp/listing.txt`, `ls` exits with status 0, tinysh prints `[pid 45 exited with status 0]`; a page is
  4 KB; a failed exec exits with 127.

## The one picture

The tinysh prompt at the top. The parent box on the left (tinysh, PID 43) and, from scene 3, the child box on the
right (PID 45, parent 43), joined by a dashed family line. Each box holds its name, its PID line and a row of four
memory pages. Under each box, three numbered slots: the file descriptors 0, 1 and 2. At the bottom, the terminal
on the left and the file listing.txt on the right. An arrow from each slot 1 shows where that process's output goes.
Yellow means "look here" or a change, green means done and correct, red means a failure or a wrong idea, purple is
`ls`'s own code and memory. Same places from start to end.

## Scene 1 · The hook · 0:00–0:25 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: You type ls into a shell, the program that reads your commands, and a moment later ls is running, listing files.
Now add a greater-than sign and a file name. The same ls runs, but its list lands in the file instead of on the
screen. And ls never knows. How does the shell do that?

SCREEN: The prompt `tinysh$ ls os`, then `> /tmp/listing.txt` added. The terminal box and the file box at the
bottom; three file names drop into the file. Caption "how does the shell do that?".

## Scene 2 · One call for everything · 0:25–1:05 · [PAIN] [JOKE:amplify] [WISH]

VO: The simplest design is one request to the kernel: spawn this program. It works for plain ls. Now you want the
output in a file, so spawn needs a setting for where output goes. Then one for input. One for a pipe that feeds one
program into another. One for the folder to start in, for the settings it inherits, for the user, for the limits.
Every new kind of setup becomes one more setting, and the form only ever gets longer. Unix took another route in the
1970s, and Linux kept it. Split the job into two calls, and let your own code run in between.

SCREEN: A card `spawn(program,` grows one line per setting: output to, input from, pipe, folder, settings, user,
limits. Then it is crossed out and fades. Caption "two calls, with your own code in between".

## Scene 3 · The parent, and fork · 1:05–1:45 · [ANALOGY] [MAP] [SHOW] [NAME] [JOKE:is-the-explanation]

VO: Unix used family words for this, and they fit. Every process has a number, its PID, and a parent: the process
that started it. Here, the parent is the shell, tinysh, with PID 43. The first call is fork. It makes a copy of the
process that calls it. The child gets a new PID, 45. Everything else starts as a copy of the parent: the code, the
memory and the open files. Here the family picture breaks. No real child is born with their parent's memories. This
one is, down to the line it was in the middle of.

SCREEN: The parent box draws in (tinysh, PID 43, four memory pages; slots 0, 1, 2; slot 1's arrow to the terminal).
On fork, a copy slides out to the right and becomes the child (PID 45, parent 43), with its own slots and slot 1's
arrow to the terminal. A dashed family line joins them.

## Scene 4 · Two answers from one call · 1:45–2:10 · [SHOW] [JOKE:skeptic]

VO: Both of them come back from the same fork call. The parent gets the child's PID, 45. The child gets 0. That's
how each one knows which it is. I know what you're thinking: copying a whole process sounds slow. The kernel doesn't
copy at first. Parent and child share the memory, and the kernel copies a page, a 4 KB piece, only when one of them
writes to it.

SCREEN: Tags "fork() returned 45" over the parent and "fork() returned 0" over the child. The child's pages turn
dashed with "shared"; one page turns solid yellow, "copied on write: 4 KB".

## Scene 5 · The gap · 2:10–2:50 · [SHOW]

VO: Now the gap, which is the whole point. The child still runs the shell's code, so it can change things about
itself before it becomes ls. A process names its open files with small numbers, file descriptors. 0 is where input
comes from, 1 is where output goes, and 2 is for errors. Right now, the child's 1 points at the terminal. So the
child opens listing.txt, and points descriptor 1 at it, with a call named dup2. Meanwhile the parent goes to sleep
in wait.

SCREEN: The slots glow in turn, with "0 in", "1 out", "2 errors". The child's slot 1 arrow swings from the terminal
to listing.txt. The parent dims, tag "asleep in wait".

## Scene 6 · exec, and a prediction · 2:50–3:35 · [PREDICT] [PAUSE] [BREAK] [SHOW] [NAME]

VO: Then the child calls exec. The kernel throws away the shell's code and memory inside the child, and loads ls from
the disk. Before we look: what did ls keep? The PID, the parent, the open files, or none of them? Pause and guess.

(three seconds)

All three. It's still PID 45, its parent is still 43, and descriptor 1 still points at listing.txt. exec doesn't
start a new process. It swaps the program inside the same one. ls writes its list to descriptor 1, as it always
does. The lines land in the file, and ls never knew.

SCREEN: The child's name becomes "ls" and its pages turn purple. Countdown. The PID line, the family line and slot
1's arrow glow green in turn. Dots run down slot 1's arrow; three names appear in listing.txt. Caption "fork makes a
copy, exec swaps the program".

## Scene 7 · Waiting up · 3:35–4:10 · [SHOW] [MAP] [LOOP-PLANT] [JOKE:release]

VO: The third call closes the loop. ls ends with exit status 0, which means success. The kernel frees its memory, but
keeps a small record: who it was, and how it ended. It wakes the parent, like a parent waiting up to hear how the
evening went. wait hands the parent two numbers, 45 and status 0, and only then does the kernel delete the record.
Between those two moments, the dead child has a grim name. That's the next section.

SCREEN: The child's pages go; the child greys out to a small record "PID 45, status 0". A dot runs along the family
line to the parent, which wakes: "wait: 45, status 0". The record goes. The prompt prints `[pid 45 exited with
status 0]`.

## Scene 8 · Two rules · 4:10–4:40 · [GUARDRAIL]

VO: Two rules come with this. A successful exec never returns, because the code that called it is gone. So the line
after exec runs only if exec failed, and it should exit at once. tinysh exits with 127, the number real shells use
for command not found. And a parent should always wait for its children. That's where the shell's dollar question
mark, and Java's Process.waitFor, get their number.

SCREEN: The heart of `tinysh.c` (fork, the setup, execvp, `_exit(127)`, waitpid), short, with the lines that match
each step highlighted. Caption "exec returns only when it fails".

## Scene 9 · The moral, and a check · 4:40–5:15 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So how did the shell put ls's list in a file, without ls knowing? It copied itself, set up the copy, swapped in
ls, and waited for the news. The gap between fork and exec is where all the setup lives, so no call ever needs a
setting for it. One quick check. Suppose the child called exec first, and pointed descriptor 1 at the file after
it. Where would the list go? Pause and think.

(three seconds)

To the terminal. After a successful exec, the shell's code is gone, so that setup never runs. Setup goes in the gap.

SCREEN: The picture rebuilt: the child as tinysh again with slot 1 on the terminal. Captions "copy, set up, swap,
wait". For the check, "exec first, setup after?"; countdown; slot 1's arrow stays on the terminal, red cross on the
late setup; final caption "setup goes in the gap".

---

### Beat check

- QUESTION from a felt mystery (scene 1); PAIN with the growing form and the WISH (scene 2).
- ANALOGY + MAP with the family words, and its breaking point used as a light moment (scene 3); NAME (fork) after
  the copy is shown.
- PREDICT with PAUSE breaks the "exec starts a new process" model (scene 6); NAME exec after the SHOW.
- GUARDRAIL (scene 8), MORAL and a check answerable from the code (scene 9). Light moments: the form that only gets
  longer (0:55), born with its parent's memories (1:40), the skeptic on copying (2:00), the grim name (4:05).

### Accuracy notes for the producer

- PIDs 43 and 45 and the command come from the lesson's stepper, taken from a real trace. Run again, the PIDs differ.
- The video says "exec" for `execve` (tinysh calls `execvp`, which tries the folders on PATH and ends in `execve`).
  It says "wait" for `waitpid`, whose system call on Linux is `wait4`.
- arm64 has no `dup2` system call; glibc uses `dup3`. The video names `dup2`, as tinysh's code does. Likewise there
  is no `fork` system call on arm64; glibc makes it from `clone`. Both are left to the lesson.
- Copy-on-write is shown as one 4 KB page; the lesson leaves the details to lesson 7.
- After exit the kernel keeps a small record with the status until wait collects it; the name (zombie) and the
  SIGCHLD notice are left to section 3 and section 4.
- 127 is tinysh's `_exit(127)` after a failed `execvp`, and real shells' "command not found".
- Java's `ProcessBuilder` path through `jspawnhelper` is left to the lesson.
- Spoken forms via `SAY`: ls as "L S", tinysh as "tiny shell", PID as "P I D", dup2 as "dup two", listing.txt as
  "listing dot text", Process.waitFor as "Process dot wait for".
