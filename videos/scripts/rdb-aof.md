# A photo of memory, without stopping: fork and copy-on-write

- Slug / scene: `rdb-aof`, `videos/scenes/rdb_aof.py:RdbAof`
- Lesson: `cache-09`, section 1, "Saving in the background: fork and copy-on-write"
- Audience / level: a complete newcomer. Knows Redis keeps data in memory and a restart wipes it (the lesson's
  opening); doesn't know processes, fork, pages or copy-on-write.
- Length: 5:13 (~830 words of narration plus two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=196.9` (dump.rdb written, the child gone, page B freed, B' held by the parent)
- The learner's real question: Redis runs every command on one thread. How can it copy gigabytes to disk without
  making every client wait?
- Misconception to steelman and break: "a helper can just copy memory while writes go on" (the copy mixes moments);
  and "fork copies all the memory" (it copies only the page table).
- Concept chain: SAVE stops the one thread (2,065 ms) → a helper must copy, and the copy must show one moment → fork
  makes a child that shares every page → copy-on-write copies a page only when the parent changes it → rename makes
  the file appear in one step → the costs (page table, copied pages) and what a crash still loses (hardest last)
- Analogy family: the lesson's café whiteboard of orders and its photo; refined into a board of panels, where a
  waiter about to write on a panel swaps in a fresh copy and the photographer keeps the old one.
- Open loops: "how can it copy without making clients wait?" planted in scene 1 → paid off in scene 9.
- Assumptions: all numbers are the lesson's (83 MB and 2,065 ms for SAVE, a GET waiting 1,761 ms; 4 KB pages; 8 bytes
  per page, 48 MB of table for 24 GB, 10 to 25 ms per GB; 6 to 31 ms to fork 83 MB; 3 to 5 MB copied by a few hundred
  updates; up to twice the memory; about a minute lost on a busy server; `temp-41.rdb`, `dump.rdb`, payment 5). Three
  pages stand for the million payments, as in the stepper.

## The one picture

Top left: the parent, "Redis (the parent)", with its page table (A B C) and a status line. Top right: the child, which
appears at the fork with its copy of the table. Middle: memory pages A, B and C, joined to the parent by solid lines
and to the child by dashed ones. Below page A, B' (gold) appears when the parent changes payment 5. Bottom right: the
disk, holding `dump.rdb` or `temp-41.rdb`. Red is a stop or a loss, teal the child, gold the copied page.

## Scene 1 · The question · [QUESTION] [LOOP-PLANT]

VO: Redis keeps all its data in memory, and memory is wiped when a program stops. So now and then, Redis writes a copy
of everything to a file on disk: a snapshot. But Redis runs every command on one thread, one path of work. So how can
it copy gigabytes to disk without making every client wait?

SCREEN: The parent and its three pages; the pages flicker on "wiped"; the disk with `dump.rdb`.

## Scene 2 · SAVE · [FAMILIAR] [PAIN]

VO: The plain way is the command SAVE: the main thread writes the file itself. In the lab, a million payments, 83
megabytes, took 2,065 milliseconds to save. A client that asked for one key 200 milliseconds in waited 1,761
milliseconds for its answer. Nothing else ran, because the only thread that runs commands was busy writing a file.
With 25 gigabytes, that pause would last minutes.

SCREEN: "busy: writing a file" in red, dots from the pages to the disk; a client chip "a client: GET" waits; captions
with the lab's numbers.

## Scene 3 · The café · [ANALOGY] [BREAK] [WISH]

VO: Think of a café that keeps today's orders on a whiteboard. Wipe the board and they're gone, so now and then you
take a photo of it. SAVE is a photographer who makes the staff stop writing until he has copied the whole board by
hand. So let a helper copy the board while the staff keep writing? Then the copy mixes moments: payment 5 from ten
o'clock, payment 900,000 from two seconds later. A refund could land in the file without the payment it refunds. We
need both: someone else does the copying, and the copy still shows one moment.

SCREEN: Captions over the picture; page A flickers on "mixes moments".

## Scene 4 · Fork · [NAME] [PREDICT] [PAUSE] [SHOW] [MAP]

VO: Redis's answer is BGSAVE, a background save. The main thread calls fork: a request to the kernel, the core of the
operating system, to copy the running program. The original is the parent, and the copy is the child. The child will
write the file, and the parent goes on serving clients. But copying 25 gigabytes of memory would take seconds too. So
what does fork actually copy? Pause and guess. Almost nothing. Memory is handed out in pages, blocks of 4 kilobytes,
and each program has a page table, the kernel's map from its addresses to pages. Fork copies only the map. Parent and
child point at the same pages. In the café, the photographer gets a list of the board's panels; no panel moves. The
child writes every key to a temporary file, and the parent serves clients at full speed.

SCREEN: The child appears; countdown; the page table appears in the parent and a copy flies to the child; dashed lines
from the child to the same pages, "shared" under each; the child writes `temp-41.rdb`.

## Scene 5 · Copy-on-write · [SHOW] [NAME] [JOKE:release]

VO: Now a client changes payment 5 to refunded. It lives on page B, which the child still needs. So the kernel first
copies page B, and gives the copy to the parent. The parent writes refunded on its copy. The child still sees page B
as it was, with payment 5 settled. Its picture stays frozen at the moment of the fork. That's copy-on-write: a page is
copied only when someone is about to change it. In the café, a waiter about to write on a panel first swaps in a fresh
copy, and the photographer keeps the old one. Everyone's happy, except the memory chips, which now hold one page
twice.

SCREEN: "SET payment:5 refunded"; page B glows; a copy of B slides to B' under page A; the parent's line moves to B';
B' reads "p:5 refunded"; page B "child only", still "p:5 settled".

## Scene 6 · Finish, and the costs · [SHOW] [GUARDRAIL]

VO: When the child finishes, it renames its file to dump.rdb. A rename happens in one step, so a crash halfway leaves
the old snapshot, never half of a new one. Then the child exits, and the old page B, which only the child used, is
freed. In the lab, forking 83 megabytes took 6 to 31 milliseconds, instead of a two-second stop. Two costs remain, and
both fall on the parent. The fork still copies the page table: 8 bytes for every 4 kilobyte page. A 24 gigabyte Redis
copies 48 megabytes of table, at about 10 to 25 milliseconds per gigabyte on most machines. And every page the parent
changes during the save gets copied. In the lab, a few hundred updates copied 3 to 5 megabytes. On a server that
writes heavily, it can come close to twice the memory. So keep Redis's memory limit well below the machine's memory.

SCREEN: The disk shows `dump.rdb` ("the data at the moment of the fork"); the child and its lines go; page B dims,
"freed". Captions with the costs; "keep maxmemory well below the machine's RAM".

## Scene 7 · What a crash loses · [GUARDRAIL]

VO: And a snapshot is only as new as its fork. With the default rules, a busy server saves about once a minute, so a
crash loses about a minute of writes. Kill Redis now, and the restart loads dump.rdb. Payment 5 is settled again; the
refund after the fork is gone. For a cache, that's fine: it refills from the database. For the café's payment notes,
it isn't.

SCREEN: "killed: kill -9"; B' and its line go; dots run from the disk back to the pages; page B's "p:5 settled" pulses
red.

## Scene 8 · The code, in Java and Kotlin · [SHOW]

VO: In Java and Kotlin, BGSAVE is one command, and Redis answers as soon as it has forked. Its stats then tell you how
long the fork took, and how much the kernel copied.

SCREEN: The lesson's `SnapshotDemo` lines side by side: `BGSAVE` through `executeCommand`, then `latest_fork_usec` and
`rdb_last_cow_size` from `INFO`.

## Scene 9 · The moral, and a check · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, how does Redis photograph its memory without stopping? It forks. The child gets the picture, the parent keeps
working, and the kernel copies a page only when the parent is about to change it. One quick check. During a save, the
parent changes payment 5 three times. How many copies of page B does the kernel make? Pause and think. One. After the
first copy, page B prime belongs to the parent alone, so the next writes go straight to it. Next, to lose less than a
minute, the café's notebook: a log of every change.

SCREEN: Page B pulses three times; countdown; B' appears once and glows.

---

### Beat check

- QUESTION (scene 1), FAMILIAR and PAIN (scene 2), ANALOGY, BREAK and WISH (scene 3).
- PREDICT with PAUSE (scene 4, the check in scene 9).
- NAME after the idea: BGSAVE and fork (scene 4), copy-on-write (scene 5).
- GUARDRAIL (scenes 6 and 7), MORAL and the check (scene 9). Light moments: the photographer who stops the café
  (1:20), the memory chips holding one page twice (3:10).

### Accuracy notes for the producer

- SAVE figures (83 MB, 2,065 ms, a GET 200 ms in waiting 1,761 ms) are section 0's; fork 6 to 31 ms and 3 to 5 MB
  copied are section 1's body and stepper. The Try it's runs print other ranges (fork 1.2 to 8.4 ms, 3.1 to 16.8 MB);
  the video uses the body's.
- "Payment 5 from ten o'clock, payment 900,000 from two seconds later" is the lesson's example of a mixed copy.
- B' is drawn under page A only to keep the lines clear; in memory it is just another 4 KB page.
- "About a minute" is the busy-server case of the default `save` rules (`60 10000`); a quiet server can lose up to an
  hour, which the video leaves to the lesson.
- The check's answer is copy-on-write's rule: after the first write, the parent's copy is private, so later writes
  copy nothing.
- The append-only file is only named as the next step ("a log of every change"); the slug keeps its old name.
