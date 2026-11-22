# One clerk for every window: how Redis runs each command

- Slug / scene: `redis-event-loop`, `videos/scenes/redis_event_loop.py:RedisEventLoop`
- Lesson: `cache-02`, section 1, "One thread runs every command, one after another, to the end"
- Audience / level: a complete newcomer. Can read a little code; knows nothing about servers, threads, connections,
  operating systems or Redis.
- Length: 5:34 (~770 words of narration at Kokoro's ~150 words a minute with its sentence gaps, plus two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=157` (one pass of the loop done: "event loop" named, all four steps lit, the three commands still in the client boxes)
- The learner's real question: thousands of programs talk to one Redis server at once, and it runs every command on
  one thread. Isn't that slow? And how can it be safe?
- Misconceptions to steelman and break: (1) "give every client its own thread" (broken by memory, switching and the
  lost count, 41 read twice, 42 written twice); (2) "one thread is slow" (broken by half a microsecond per GET; the
  real danger is one long command); (3) "one thread, so my read, add and write is safe" (broken by the worked
  example: 1,611 of 8,000).
- Concept chain: a thread per client costs memory and needs locks → one clerk finishes each job before the next →
  the thread asks the operating system which connections have bytes (epoll_wait) → ask, read, run, send: the event
  loop → commands never overlap, so each is atomic → a GET costs half a microsecond, so queues stay invisible → one
  slow command makes everyone wait (hardest last) → atomic covers one command, not three
- Analogy family: the lesson's post office. One clerk, windows round the room, each job finished before the next; the
  customer with four hundred parcels to weigh. Where it breaks: speed (a minute per customer against half a
  microsecond), said out loud.
- Open loops: "slow?" and "risky?" planted in scene 1 → "risky" paid off in scene 5, "slow" in scene 6; the four
  hundred parcels planted in scene 3 → paid off in scene 7
- Assumptions: numbers are the lesson's (41 read twice and 42 written twice; 10,000 connections; the stepper's three
  clients and memory: auths:today 41, card:7 ok, card:9 none, payment:42 approved; t = 0 ms and 0.1 ms; the 1.5-second
  script, B's GET at 300 ms, answered at 1,500 ms, 1,200 ms late; half a microsecond per GET; three million GETs;
  fifty copies; the worked example's 8,000 calls printing 1,611, 1,654 and 1,628, and 8000 with INCR; SLOWLOG's
  10 ms). The two INCRs in scene 5 take the counter from 42 to 44, simple arithmetic on the stepper's state.

## The one picture

Left: three client boxes (blue), A, B and C, each showing the command it sent. Middle, inside a grey "Redis server"
outline: first three grey thread boxes, then one yellow box, the event loop, with its state written in it and a
small clock under it. Right, inside the server: the memory panel, four keys with their values. Dots carry commands
from a client to the loop and replies back; green reply chips sit between clients and loop until they're sent. Gold
marks the post office (windows, the clerk), red a cost, green a delivered reply. Captions along the bottom.

## Scene 1 · Two worries · 0:00–0:27 · [QUESTION] [LOOP-PLANT]

VO: Redis is a program that keeps data in memory and answers requests over the network.

Thousands of programs can talk to one Redis server at once, sending short commands like "add one to this counter".

Redis runs all of them on a single thread, one line of work inside the program.

One thread, for thousands? That sounds slow, and risky. Hold on to both worries.

SCREEN: Title card. The server outline and the memory panel draw in; three client boxes; "and thousands more" under
them. The yellow "one thread" box. Two chips, "slow?" and "risky?", under the server.

## Scene 2 · A thread for every client · 0:27–1:13 · [FAMILIAR] [PAIN] [BREAK] [WISH]

VO: The obvious design gives each client its own thread. A client reaches the server through a connection, an open line
between two programs.

Ten thousand clients need ten thousand threads, each with its own memory, and the computer spends much of its time
switching between them.

Worse, two threads can touch the same key at once. A key is a name for a value, like this counter.

Client A and client B both send INCR, add one. Both threads read 41. Both write 42. Two adds, and the counter went up
by one.

The fix is a lock on every key, a marker that lets one thread in at a time, and every command pays for it.

What we'd like is a design where two commands can never collide, with no locks at all.

SCREEN: The one-thread box gives way to three grey thread boxes, each joined to its client. Caption "10,000 clients:
10,000 threads, each with its own memory". A and B get "INCR auths:today"; two yellow arrows to the counter; both
threads say "reads 41", then "writes 42"; the counter shows 42 in red, "two adds, up by one". Red padlocks beside every
key; caption "a lock on every key: every command pays". Wish caption in yellow.

## Scene 3 · The post office · 1:13–1:56 · [ANALOGY] [MAP] [JOKE:is-the-explanation] [LOOP-PLANT]

VO: Picture a small post office with one clerk and six windows.

The clerk serves the first window, then the second, round the room, finishing each job before starting the next.

There's one pair of hands, so two customers can never grab the same parcel. The clerk never even locks the stamp
drawer. Who would she lock it against?

That's Redis. The clerk is the one thread, the windows are the connections, and each job is a command.

And the clerk never waits at an empty window. Redis's thread asks the operating system, the program that runs the
computer, which connections have bytes waiting.

On Linux, that request is called epoll_wait. If none do, the thread sleeps until one does.

SCREEN: The threads fade. The clients turn gold, "window 1", "window 2", "window 3"; one gold box in the middle, "the
clerk"; three parcels go to the clerk one at a time. On "That's Redis" the labels map back: window → client A, B, C
(connections), clerk → one thread, parcel → a command. The loop box: "asleep in epoll_wait / using no CPU".

NOTE: The stamp drawer is the light moment, and it is the lesson: one pair of hands needs no locks.

## Scene 4 · Ask, read, run, send · 1:56–2:40 · [SHRINK] [SHOW] [NAME]

VO: Let's watch with three clients. Client A sends INCR. B asks for card:7. C stores a value under card:9. The thread is
asleep, using no CPU.

The operating system wakes it: three connections have bytes waiting.

The thread reads A's bytes, cuts out one complete command, and runs it from start to finish: read 41, add one, store
42.

The reply waits in A's outgoing buffer, a holding area. It isn't sent yet.

Then B's GET, then C's SET, each to the end.

Before it sleeps again, it sends every waiting reply.

Ask, read, run, send. This loop is the event loop, and Redis runs it over and over.

SCREEN: Command lines appear in A, B and C ("INCR auths:today", "GET card:7", "SET card:9 blocked"). The loop
"asleep in epoll_wait", clock "t = 0 ms". Then "epoll: A, B, C ready"; a dot from A; "run INCR auths:today"; arrow to
memory; 41 becomes 42; green chip ":42 (not sent)" beside A. Same for B ("ok") and C ("+OK", card:9 becomes blocked).
"send every reply"; the chips travel into the clients; clock "t = 0.1 ms". The four steps written under the loop:
"1 ask  2 read  3 run  4 send". Caption "the event loop".

## Scene 5 · Two adds at once · 2:40–3:18 · [PREDICT] [PAUSE] [SHOW] [NAME] [LOOP-PAYOFF]

VO: Now the race from before. Client A and client B both send INCR at the same moment. The counter says 42. Where does it
end up? Pause and guess.

(three seconds)

44. One INCR runs to the end, 42 to 43, and only then the other, 43 to 44.

Commands never overlap, so every command is atomic: it happens as one step, and no client ever sees it half done.

Fifty programs calling INCR on one key never lose a count, with no lock at all. Nobody else is running. That's the
risky worry.

SCREEN: "INCR auths:today" in A and B together; countdown. A's command runs (42 → 43), then B's (43 → 44), green.
Caption "atomic: one step, never seen half done". The "risky?" chip gets a green tick.

## Scene 6 · Is one thread slow? · 3:18–3:36 · [LOOP-PAYOFF] [ANALOGY breaks]

VO: And the slow worry? On the lab server, a GET costs the thread about half a microsecond.

Here the post office picture breaks, on speed. A clerk needs a minute per customer. So queues that would be hopeless
at a post office stay invisible in Redis.

Until one slow request arrives.

SCREEN: "one GET: about 0.5 microseconds of the thread's time". Caption pair "clerk: a minute per customer" / "Redis:
half a microsecond". The "slow?" chip gets a tick, then a small "until..." in red.

## Scene 7 · Four hundred parcels · 3:36–4:22 · [BREAK] [SHOW] [JOKE:release] [LOOP-PAYOFF]

VO: Then a customer asks for four hundred parcels to be weighed, and every window waits.

In Redis, client A sends a Lua script, a small program that Redis runs as one command. This one spins for 1.5 seconds.

At 300 milliseconds, B sends GET payment:42. The only thread that could read it is busy inside the script. B waits.

At 1,500 milliseconds the script returns, and B finally gets its half a microsecond of work, 1,200 milliseconds late.

One 1.5-second command costs as much as three million GETs.

Somewhere in that queue, a customer with one stamp is learning patience. So the danger is one long command.

SCREEN: A's box: "EVAL busy 1500 ms"; the loop turns red, "inside the script"; the clock runs from 0 to 1,500 ms. At
300 ms B's box gets "GET payment:42" and "waiting"; C gets "waiting" too. At 1,500 the loop turns yellow; a dot from
B; "answered 1,200 ms late". Caption "1 command of 1.5 s = the time of 3 million GETs".

## Scene 8 · Guardrails · 4:22–5:02 · [GUARDRAIL] [SHOW]

VO: Two guardrails. First, watch for commands whose work grows with a key.

KEYS *, which lists every key. HGETALL on a hash with a million fields. Deleting a huge key with DEL.

SLOWLOG GET lists every command over 10 milliseconds.

Second, atomic covers one command, not three.

A program with eight threads counts payments: GET the counter, add one, SET it back.

After 8,000 calls it printed 1,611.

Between one GET and its SET, the loop ran other clients' commands.

Send INCR instead, and the read, the add and the write are one command: 8,000, every run.

SCREEN: Three red chips "KEYS *", "HGETALL (a million fields)", "DEL (a huge key)"; caption "SLOWLOG GET: commands
over 10 ms". Then the diagram steps aside for code, Java left and Kotlin right: the GET, add, SET lines from the worked
example; "printed 1,611, then 1,654, then 1,628 (of 8,000)" in red. The three lines give way to one: `redis.incr(...)`
in both languages; "8000 on every run" in green.

## Scene 9 · The moral, and a check · 5:02–5:34 · [MORAL] [PREDICT] [PAUSE]

VO: So the moral of the story. One thread runs every command to the end.

Each command is atomic, with no locks, and one slow command makes everyone wait.

One quick check. A script runs for two seconds, and C asks for card:9, a key the script never touches. Does C wait?
Pause and think.

(three seconds)

Yes. One job at a time, whatever parcel you came for.

SCREEN: The diagram returns. The moral in yellow. A's box "EVAL (2 s)"; C's box "GET card:9"; countdown; C turns red,
"waiting". Last caption: "one thread, every command to the end".

---

### Beat check

- Opens with QUESTION (scene 1) and two planted worries. FAMILIAR + PAIN + BREAK (scene 2: a thread per client).
- ANALOGY + MAP said out loud (scene 3), the stamp-drawer joke as the explanation of "no locks".
- SHRINK + SHOW (scene 4: three clients); NAME after the show: event loop (scene 4), atomic (scene 5).
- PREDICT with PAUSE twice (scenes 5 and 9).
- The analogy's break said out loud (scene 6: speed). BREAK of "one thread is slow" and the parcels payoff (scene 7).
- GUARDRAIL (scene 8), with a third wrong model broken (read, add, write). Code last, Java and Kotlin side by side.
- MORAL and check (scene 9). Light moments: the stamp drawer (~1:35), the customer with one stamp (~4:15).

### Accuracy notes for the producer

- The section's prose uses `INCR auths:card:7` for the race (41 read twice); the stepper and the worked example use
  `auths:today`, which starts at 41. The video uses `auths:today` throughout so one key stays on screen.
- The stepper shows the reply to `GET card:7` as `ok` and the reply to `SET` as `+OK`; the video shows the same.
- "Half a microsecond per GET" and "three million GETs" are the lesson's lab numbers; they depend on the machine.
- epoll_wait is Linux's call; on macOS Redis uses kqueue. The video says "on Linux".
- The video leaves out I/O threads, background threads and the forked child (section 2): none of them runs commands.
- The 1,200 ms wait is the stepper's (sent at 300 ms, answered at 1,500 ms). The Try it adds that after 5 seconds
  (`busy-reply-threshold`) Redis answers other clients with a BUSY error; the video stops before that.
- The code is the worked example's (Jedis 8 `RedisClient`), trimmed to the three lines inside the task; the runs
  printed 1,611, 1,654 and 1,628, and 8000 with `incr`.
