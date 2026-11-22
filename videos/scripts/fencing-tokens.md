# A ticket the late holder can't use: fencing tokens

- Slug / scene: `fencing-tokens`, `videos/scenes/fencing_tokens.py:FencingTokens`
- Lesson: `dist-05`, section 3, "Fencing tokens let the thing being written refuse a late holder"
- Audience / level: a complete newcomer. Has pulled a ticket at a deli counter; has met the frozen worker in the
  previous video; knows nothing about Redis, fencing or etcd.
- Length: 5:08 (~840 words of narration, plus two pauses and silent builds)
- Poster: `POSTER=173`, just after the refusal: token 33 on A, token 34 on B, the counter at 34, the store showing
  "highest fence: 34" and B's file, "33 < 34: refused"
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: if a lock can run out while its holder is frozen, how do we stop the frozen holder's
  write from doing damage?
- Misconception to steelman and break: (1) "a lock keeps them apart", broken by the night the lock expires during a
  15-second freeze and A's out-of-date file lands; (2) the deli picture itself, where the counter always knows the
  current number, broken by the store learning of 34 only when B writes.
- Concept chain: the payout job must run once → a lock shared by servers must run out → a frozen holder writes late →
  no check in the holder can catch it → the store, which sees every write, must refuse → a number that grows with each
  holder (fencing token) → the store keeps the highest and refuses lower ones (hardest last) → where the counter must
  live, and when you need this at all
- Analogy family: the lesson's deli counter with ticket numbers (ticket = token, counter = the store).
- Open loops: "who can refuse the late write?" (the previous video's ending) → answered in scene 3; "run it twice and
  every shop is paid twice" planted in scene 1 → the efficiency-or-correctness question in scene 6.
- Assumptions: the numbers are the lesson's stepper and Try it (10-second lease, a 15-second freeze, tokens 33 and 34,
  the counter and store starting at 32, B's file "4,210 payouts", A's "4,198 payouts", 12 shops missing). Server C is
  drawn idle. The SQL line is the lesson's.

## The one picture

Left: servers C (idle, grey), A (blue) and B (green), with their tokens above them. Top centre: the lock in Redis
(gold) with its holder and a 10-second deadline bar. Top right: the fence counter (purple). Right: the payout store
(teal) with "highest fence" and the file it holds. Writes travel as chips from a server to the store; refused ones get a
red cross. A frozen server is greyed with a stopwatch.

## Scene 1 · The payout job · 0:00–0:55 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: Every night, the payments company pays each shop what it took that day. One job builds the payout file, the list
that tells the bank how much to send to each shop. It must run exactly once. Run it twice, and every shop is paid
twice. The job runs on three servers, so that one dying on the night doesn't stop the payouts. So, the tempting fix: a
lock. Before it starts, a server takes a lock that only one may hold, and the others wait. We keep it in Redis, a fast
store that all three servers can reach. Inside one program, nobody can take a lock away from you. But a lock shared by
three servers has to run out, or a dead holder would block the payouts forever. So this one is a lease, with a
deadline: ten seconds.

## Scene 2 · The late write · 0:55–2:00 · [PAIN] [WISH] [JOKE:release]

VO: Watch one night. Server A takes the lock. Server B tries, and is refused. Then A's program freezes, for fifteen
seconds, while it cleans up its memory. Every part of it stops, including the part that would renew the lock. After ten
seconds, Redis deletes the lock, exactly as asked. B takes it. B builds the payout file, and writes it. Then A wakes up.
It carries on from where it stopped, and writes its file: built before B's run, and missing 12 shops. From A's side, it
blinked. And no check inside A can catch this. We saw that the freeze can land after any check. So if A can't know it's
late, someone else has to refuse its write. Who sees every write? Only the thing being written: the store.

## Scene 3 · The deli counter · 2:00–2:25 · [ANALOGY] [MAP]

VO: Picture the deli counter at a supermarket. You pull a ticket: 33. The next person pulls 34. Once the counter has
served 34, someone who turns up late holding 33 is sent away, however sure they are that it's their turn. Map it. The
ticket is a number the lock hands out with each new holder. The counter is the store.

SCREEN: Two gold deli tickets, 33 and 34, appear between the servers and the store; a green tick under 34 ("served"),
a red cross under 33 ("sent away"). They clear when the night is replayed with numbers.

## Scene 4 · Tokens · 2:25–3:40 · [SHRINK] [SHOW] [PREDICT] [PAUSE] [NAME] [BREAK of the analogy]

VO: Let's play the night again, with numbers. Next to the lock sits a counter. It's at 32. The store remembers the
highest number it has accepted: also 32. Server A takes the lock, and in the same step the counter goes up by one. It
holds token 33. B's attempt is refused, and uses up no number. Server A freezes. Ten seconds later the lock is gone,
and B takes it, with token 34. B writes its file with fence 34. The store compares. 34 is at least the 32 it has seen,
so it accepts, and now remembers 34. Now A wakes up and writes its file, with fence 33. What does the store do? Pause
and guess.

(three seconds)

It refuses. 33 is below the 34 it already accepted. B's file stays. However sure A is that it's its turn. That number
is called a fencing token: it fences out every holder older than the newest writer. Here the deli picture breaks. The
deli calls each number itself, so it knows when 34 is being served. The store learns about 34 only when B writes. Had A
woken up before that, its 33 would have been accepted. And that's fine. Fencing only refuses a holder once a newer one
has written, which is exactly the case that does harm.

## Scene 5 · How it's built · 3:40–4:10 · [SHOW]

VO: How is it built? In Redis, the counter is one command, increment, run in the same small script that takes the
lock. So a number is handed out exactly when a lock is. The store's side is the half people miss, because it isn't
lock code at all. In a database table, the write gets one extra condition: change the row only if its stored fence is
no larger than mine. Zero rows changed means: you're a late holder.

SCREEN: Caption `INCR fence:{settle}, in the same script as the lock`; then the lesson's SQL, the condition in yellow:
`UPDATE payout_files SET content = :c, fence = :t` / `WHERE batch = :b AND fence <= :t`.

## Scene 6 · Guardrails · 4:10–4:50 · [GUARDRAIL] [LOOP-PAYOFF]

VO: Now the fine print. The counter must never go backwards, so it gets no deadline, and it must live where it can't be
thrown away when memory fills up. And it's only as safe as that one Redis server. If the server dies before its last
increments were copied to its spare, a new holder can get a number that was already handed out. That's why the numbers
are safer in etcd or ZooKeeper, two systems built so a group of servers agrees on every change, and both already keep
a number like this. And ask one question about any lock. Is it for efficiency, so two servers don't waste the same
work? A single Redis key will do. Or is it for correctness, where a double run pays the shops twice? Then the store
itself has to check.

## Scene 7 · The moral, and a check · 4:50–5:15 · [MORAL] [PREDICT] [PAUSE]

VO: So, the moral. A lock keeps holders apart only while every lease is alive. The token keeps them apart at the one
place that sees every write. One quick check. The store has accepted 34. A server shows up with token 35. Accept, or
refuse? Pause and think.

(three seconds)

Accept. 35 is newer than anything the store has seen. It's the next holder, and the store now remembers 35.

---

### Beat check

- Opens with QUESTION and the felt cost (every shop paid twice); FAMILIAR is the lock everyone trusts.
- PAIN and WISH (scene 2) before the ANALOGY; MAP said out loud (scene 3).
- PREDICT with PAUSE: what the store does with 33 (scene 4) and the check (scene 7).
- BREAK: the lock alone (scene 2) and the deli picture's limit (scene 4).
- NAME after the SHOW (fencing token, scene 4). GUARDRAIL and MORAL last. Light moment: "from A's side, it blinked".

### Accuracy notes for the producer

- The freeze is a garbage collection in the lesson's stepper; the video says "while it cleans up its memory".
- B's refused attempt returns 0 and uses no number, as in the lesson's acquire script (`SET ... NX PX`, then `INCR`).
- The store "accepts 34 because it is at least 32": the rule is "refuse any fence lower than the highest accepted",
  so an equal fence is accepted (the SQL's `fence <= :t`).
- Left to the lesson: releasing only your own lock, renewing the lease, etcd revisions and ZooKeeper zxids in detail,
  Redlock, and the unique-constraint alternative beyond one caption.
