# One waiter, a bell on every table

- Slug / scene: `epoll`, `videos/scenes/epoll.py:Epoll`
- Lesson: `os-11`, section 1, "Waiting for many connections: non-blocking reads and epoll"
- Audience / level: a complete newcomer. Knows the lesson's opening (2,000 card readers connected all day, a quiet
  Sunday, 200 MB); knows nothing about threads, sockets or system calls.
- Length: 4:30 (~680 words of narration, plus three guesses and silent builds)
- Poster: `POSTER=175` (level-triggered: c4 on the ready list with 6 KB left, the bell ringing)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: the program is doing nothing, so why does waiting cost 200 MB, and how could one
  worker wait on 2,000 connections at once?
- Misconceptions to steelman and break: (1) "one thread can just keep checking every connection" (broken by the
  lesson's spin test: a full second of CPU and 1,335,566 failed reads for 8 bytes); (2) "epoll tells me whenever a
  connection has data" (true in level-triggered mode, broken in edge-triggered mode: a partial read strands 6 KB)
- Concept chain: a thread per connection sleeps for free but costs memory → a read that never waits spins → select
  and poll check the whole list every call → epoll: sign up once (interest list), the kernel fills a ready list,
  epoll_wait returns only that → the event loop → level- versus edge-triggered (hardest last) → read until EAGAIN
- Analogy family: a restaurant. A waiter standing by each table (a thread per connection, a blocking read); one
  waiter running from table to table asking "ready yet?" (non-blocking reads); asking every table from a chair
  (select and poll); a bell on every table (epoll); a bell that keeps ringing until the table has ordered everything
  (level-triggered) or rings once (edge-triggered). Where it breaks: a bell is free and a waiter is expensive; for a
  kernel, every registered socket costs a little memory, and threads are cheap until there are thousands.
- Open loops: "why does waiting cost so much?" planted in scene 1 → answered in scene 9
- Assumptions: every number is the lesson's (2,000 readers, 2,028 threads, about 200 MB; the spin test's 1,335,566
  failed reads and full second of CPU for 8 bytes; 2,000 connections with 3 active; the stepper's 10 bytes on c3 and
  10 KB on c4, read 4 KB at a time). Four rows stand for the 2,000 connections.

## The one picture

Left: the program, a column of threads, later one event-loop thread with its state written in it. Middle: the
epoll instance (interest list on top, ready list below), inside a dashed box labelled "kernel". Right, also in the
kernel: four connections c1 to c4, each with a bell and a receive queue where bytes (gold cells) land from the
network on the right; "and 1,996 more" under them. Yellow is a bell ringing or a lookup; red is a failed read or
stranded bytes; green is a request handled. The numbers line sits at the top.

## Scene 1 · A quiet Sunday · 0:00–0:22 · [FAMILIAR] [QUESTION] [LOOP-PLANT]

VO: A quiet Sunday morning. Card readers in 2,000 coffee shops stay connected to the payments program all day, ready
to send a payment. At 7 a.m., hardly anyone buys coffee. The program has almost nothing to do, yet it holds about
200 MB of memory. Why does waiting cost so much?

SCREEN: Title card. The kernel box and four connection rows (c1 to c4, empty queues) with "and 1,996 more"; the
numbers line "2,000 card readers · about 200 MB".

## Scene 2 · A waiter for every table · 0:22–0:55 · [ANALOGY] [MAP]

VO: The simple way is a restaurant where every table has its own waiter, standing by until the guests decide. The
waiter is a thread, one line of work the operating system runs. The table is a connection. Standing there is a
blocking read: the kernel, the core of the operating system, puts the thread to sleep until bytes arrive. Asleep, it
uses no CPU, but each thread is a task with memory set aside. 2,000 card readers meant 2,028 threads and about
200 MB.

SCREEN: Four thread boxes T1 to T4 ("asleep in read()") on the left, each joined to its connection. Captions map the
restaurant: waiter = thread, table = connection, standing by = a blocking read. The numbers line becomes "2,000
connections · 2,028 threads · about 200 MB".

## Scene 3 · Ready yet? · 0:55–1:35 · [PAIN] [PREDICT] [PAUSE] [SHOW] [BREAK] [JOKE:amplify]

VO: So try one waiter for every table. A read can be told never to wait: on an empty connection it fails at once,
with an error called EAGAIN, try again. The waiter runs from table to table: ready yet? Ready yet? Here's a test
with one connection that answers after one second. How much CPU does the waiter burn? Pause and guess. (three
seconds) All of it. A full second, and 1,335,566 failed reads, for 8 bytes the sleeping read got for free. Ready yet
is a fine question once. Not a million times a second.

SCREEN: T2 to T4 leave; T1 becomes "one thread". A yellow dot shuttles to the rows and back; each trip ends in a red
"EAGAIN". For the test, the dot shuttles only to c1; countdown bar. Then a counter in the thread runs to
"failed reads: 1,335,566" and "CPU: 1.0 s of 1.0 s"; 8 bytes land in c1 and fly to the thread. Caption: "the
sleeping read: 8 bytes, 0.00 s of CPU".

## Scene 4 · Asking from a chair · 1:35–1:55 · [WISH] [PAIN] [JOKE:is-the-explanation]

VO: We want a call that sleeps until any connection in a set has data. The first answers, select and poll, take the
whole list every time, and the kernel checks every connection. With 2,000 connections and 3 active, every wake-up
checks 2,000. Still asking every table, just from a chair.

SCREEN: A chip "c1 c2 c3 c4 … 2,000" flies from the thread into the kernel; a yellow sweep runs down every row and
"and 1,996 more"; caption "every call checks all 2,000".

## Scene 5 · A bell on every table · 1:55–2:25 · [ANALOGY] [MAP] [NAME]

VO: Now put a bell on every table. The waiter registers each bell once, sits down, and walks only to the tables that
rang. That's epoll, on Linux. epoll_ctl registers each connection once, in the kernel's interest list. When bytes
arrive, the kernel itself puts that connection on the ready list. And epoll_wait sleeps until the ready list has
something, then returns only that.

SCREEN: A bell appears on each row. The epoll instance draws in the middle; chips c1 to c4 (and "+1,996") fly from the
thread into the interest list. The empty ready list. The thread: "event loop", "asleep in epoll_wait".

## Scene 6 · Watch one request · 2:25–2:50 · [SHOW] [NAME]

VO: Watch. 10 bytes arrive for c3. The kernel puts c3 on the ready list and wakes the thread. epoll_wait returns
c3. The thread reads the 10 bytes, reads again, gets EAGAIN, and goes back to sleep. It never touched c1, c2 or c4.
A thread living in this wait-and-handle cycle is called an event loop.

SCREEN: A "10 bytes" cell slides into c3's queue; c3's bell rings; a "c3" chip drops into the ready list; the thread
lights up and takes the chip; the cell flies to the thread ("read 10 bytes"), then "read again: EAGAIN", then
"asleep in epoll_wait". The other rows stay grey.

## Scene 7 · Two ways to ring · 2:50–4:00 · [BREAK] [PREDICT] [PAUSE] [SHOW] [NAME] [GUARDRAIL] [JOKE:release]

VO: The bell can ring in two ways, and the difference bites. 10 KB arrive on c4, and the loop reads only 4 KB. By
default, epoll is level-triggered: the bell keeps ringing while the table has anything left to order. So the next
epoll_wait returns c4 again, and the loop reads the rest. Edge-triggered rings once, each time new data arrives.
Same 10 KB, same 4 KB read, and the loop waits again. What happens to the other 6 KB? Pause and guess. (three
seconds) They sit there. They aren't new, so epoll_wait sleeps. And the client sent its whole request and waits for
an answer, so nothing new will come. The waiter took half the order and sat down. Edge-triggered wakes the loop less
often, which some servers want. The rule for that code: on every event, read until EAGAIN.

SCREEN: Ten cells slide into c4; its bell rings; c4 to the ready list; four cells fly to the thread, six stay. Level:
the bell keeps wiggling and c4 stays on the ready list; the next wait returns it and the six cells go. Edge: ten
cells again, one ring, c4 leaves the ready list after the first wait, four cells go, and the thread falls asleep
with six cells left; countdown bar. Then the six cells turn red, "stranded", and the caption "the client waits for
an answer: nothing new will come". The fix replays: reads of 4, 4 and 2 KB, then "EAGAIN", queue empty. Rule caption:
"edge-triggered: on every event, read until EAGAIN".

## Scene 8 · Where the restaurant breaks · 4:00–4:18 · [GUARDRAIL]

VO: Here the restaurant picture breaks. A bell is free, but every connection in the interest list costs the kernel a
little memory. And waiters are expensive, while threads are cheap until there are thousands. Ten card readers can
have a thread each. Thousands of quiet ones want an event loop.

SCREEN: The interest list glows ("each entry: a little kernel memory"). Captions: "threads: cheap until there are
thousands", then "10 readers: a thread each is fine · thousands: an event loop".

## Scene 9 · The moral, and a check · 4:18–4:45 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So why did a quiet Sunday cost 200 MB? Every connection had its own sleeping waiter. epoll is one waiter and a
bell on every table: sign up once, sleep, and walk only to the tables that rang. One quick check. 2,000
connections, and 3 have data. How many does poll check, and how many does epoll_wait return? Pause and think.
(three seconds) poll checks all 2,000. epoll_wait returns just the 3.

SCREEN: Captions for the moral. Cells land on c1, c2 and c4; countdown bar. Then a yellow sweep runs down all rows
("poll: checks 2,000") and three chips drop into the ready list ("epoll_wait: returns 3").

---

### Beat check

- Opens with FAMILIAR and the QUESTION (scene 1), from the lesson's quiet Sunday.
- ANALOGY and MAP (scene 2) before the cure; the analogy carried through every scene and broken in scene 8.
- PREDICT with PAUSE: the spin test (scene 3), the edge-triggered partial read (scene 7), and the check (scene 9).
- BREAK: spinning (scene 3), polling from a chair (scene 4), the stranded 6 KB (scene 7).
- NAME after the picture: blocking read (2), EAGAIN (3), epoll, interest list and ready list (5), event loop (6),
  level- and edge-triggered (7).
- GUARDRAIL: read until EAGAIN (7) and the analogy's limits (8). MORAL last (9). Light moments: "not a million
  times a second" (1:30), "just from a chair" (1:52), "took half the order and sat down" (3:45).

### Accuracy notes for the producer

- The spin test is the lesson's `wait.c spin` (one socket, the reply after one second): 1,335,566 `EAGAIN`s and a
  full second of CPU on one run; the count depends on the CPU. The blocking and epoll versions used 0.00 s.
- 2,028 threads and about 200 MB (189 to 228 MB) are the lesson's `EchoServers threads` mode with 2,000 idle
  clients.
- `select` also caps descriptor numbers at 1,024; `poll` drops the cap and keeps the cost. The video says only that
  both check every connection on every call.
- On arm64 the system call is `epoll_pwait`; the video says `epoll_wait`, as the section's prose does. BSD and macOS
  have `kqueue`; left to the lesson.
- The c3 (10 bytes) and c4 (10 KB, a 4 KB buffer, 6 KB left) cases are the lesson's stepper. The fixed edge-triggered
  loop's reads of 4, 4 and 2 KB follow from the 4 KB buffer.
- "A little memory" per registered socket is the section's own wording.
- Left to the lesson: the blocking read up close, Java's `Selector` and virtual threads, and io_uring.
