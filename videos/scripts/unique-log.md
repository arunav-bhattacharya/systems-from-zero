# Who gets @ana? One decider per handle

- Slug / scene: `unique-log`, `videos/scenes/unique_log.py:UniqueLog`
- Lesson: `derive-04`, section 0, "Two people ask for @ana at once: a rule needs one decider"
- Audience / level: a complete newcomer. Can read a little code; knows nothing about servers, databases, logs,
  partitions or hashes.
- Length: 5:49 (~820 words of narration as rendered; Kokoro speaks about 160 words a minute here, plus three pauses
  and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=216` (both @ana claims in partition 0; processor 0 "taken: ana (u-17)", u-17 granted, u-43 refused)
- The learner's real question: the sign-up code checks whether a handle is taken before saving it. How can two people
  both be told yes?
- Misconception to steelman and break: (1) "check, then save" enforces the rule, broken by two servers that each
  check a row that doesn't exist yet; (2) "any split of the log will do, say by user ID so each user's requests stay
  together", broken by the two @ana claims landing in partitions 2 and 3 and both being granted (937 extra owners).
- Concept chain: two deciders each say yes → one decider, one after the other (a clerk with the seating chart) →
  one log and one processor is correct but slow → split by handle into partitions, each with its own processor →
  the partition key is the rule → a crashed processor replays its partition (hardest last)
- Analogy family: a theatre box office. One clerk holds Friday's seating chart and handles requests in order (the
  processor, its table of taken handles, the queue as the log); the box office grows by nights, not by seats (the
  partitions); two clerks with a copy of the same chart (the wrong key); a clerk who faints keeps her chart, a
  processor doesn't (the breaking point).
- Open loops: "how can two people both be told yes?" planted in scene 1 → answered in scene 9; "one clerk for every
  show is slow" planted in scene 4 → paid off by splitting by night in scene 5.
- Assumptions: all numbers are the lesson's (u-17 and u-43, r-1 and r-2, "ana" hashes to 96,724, remainder 0 with 4
  partitions; 2,000 claims, p99 wait 5,785 steps with one log and 2,274 with 8 partitions; 937 extra owners when
  keyed by user ID; 31 duplicates for check-then-insert). @bob and @leo hash to partitions 1 and 2 (Kotlin
  `hashCode()`, checked); the requests r-3, r-5, r-6 and their users are made up for the picture. Seat F12 is the
  lesson's.

## The one picture

Left: the two users' phones (u-17 top, u-43 bottom, white boxes). Middle: first two app servers and a database (the
broken design), then the box office queue, which becomes the claims log: one row, then four partitions P0 to P3
with offset slots. Right: the clerk's booth, which becomes processor 0, then processors 0 to 3 (teal), each with its
table of taken handles. Claims are gold chips; green means granted, red means refused or wrong. One caption line at
the bottom. At most about six things on screen.

## Scene 1 · Friday evening · 0:00–0:30 · [QUESTION] [JOKE:pivot] [LOOP-PLANT]

VO: Picture a Friday evening. A payments app has added wallets, so friends can send each other money by a short
name, called a handle. Two people named Ana sign up in the same millisecond. Both ask for the handle @ana, and both
are told it's theirs. On Saturday a friend sends 20.00 to @ana for concert tickets, and it lands with the wrong Ana.
Somewhere, the other Ana is having a very nice Saturday. So how can two people both be told yes? Hold that question.

SCREEN: Title card. Two phone boxes, u-17 and u-43, "wants @ana", then both "got @ana" in gold. A chip "20.00 to
@ana, concert tickets" flies from the top to u-43, which turns red: "the wrong Ana". A yellow "?" on "both be told
yes".

## Scene 2 · The code that looks right · 0:30–1:30 · [FAMILIAR] [PAIN] [BREAK] [JOKE:release] [WISH]

VO: The sign-up code looks right. Check whether @ana is taken, and if it isn't, save it. It reads exactly like the
rule, and it passes every test that sends one sign-up at a time.

Now slow Friday down. The app runs on many app servers: computers that each run a copy of the program. Handles live
in a database, a program that keeps records as rows in a table.

The two sign-ups reach two different servers. Each one asks the database: is there a row for ana? Each finds none.
So each one saves a row. Two rows now say @ana.

Why didn't the database stop it? It does make a second writer wait when two of them change the same row. But each
check looked for a row that didn't exist yet, so there was nothing to wait on.

Tests are polite. They take turns. Users don't. So the point is this: two servers each said yes without hearing from
the other. What we want is one place that hears both requests, one after the other.

SCREEN: The code line `if (!taken("ana")) save("ana", me)` at the top. Two blue app servers and a grey database with
"no row for ana". Blue dots run to the database (the checks), both servers say "no row", gold dots run (the saves),
two red rows appear: "ana  u-17", "ana  u-43". Caption "check, then save: @ana given out twice". The servers pulse
red on "without hearing from the other".

NOTE: Be fair first: the code reads like the rule and passes its tests.

## Scene 3 · The box office · 1:30–2:05 · [ANALOGY] [MAP]

VO: A theatre box office has this problem every night, and an old answer. Every request for Friday's show goes to the
one clerk who holds Friday's seating chart. She handles them one at a time. The first request for seat F12 gets it.
The second is told: sorry, sold.

Let's map it. The clerk is a processor: a program that reads requests in order and decides each one. Her seating
chart is its table of taken handles. And the queue at her window is a log: a list of records that only ever grows
at the end.

SCREEN: The servers and the database leave; the phones dim. A teal booth on the right ("the clerk", "Friday's
chart: F12 free"). Three little people queue at the window, holding F12, C4, F12. The first is served (chart "F12:
sold"), then C4, then the last is told "sorry, sold" in red. Labels appear one at a time on the map: "processor",
"table of taken handles", "the log". The people turn into claim chips in a log row; the booth becomes "processor".

## Scene 4 · One line for everyone · 2:05–2:40 · [SHRINK] [SHOW] [JOKE:amplify] [LOOP-PLANT]

VO: So the simplest version is one log, and one processor that does one thing at a time. The first claim for @ana in
the log wins, and every later one is rejected. That's correct.

But now every claim in the whole app waits in one queue. That's one clerk selling seats for every show in the city.
Very fair, and very slow. In the lesson's simulation, 2,000 claims went through one log, and one claim in a hundred
waited 5,785 steps or longer.

SCREEN: One log row with chips r-1 @ana, r-7 @bob, r-8 @leo and "...", one processor "first claim wins". A dot runs
along the arrow. Caption "every claim in the app waits in this one queue", then "one log, 2,000 claims: 1 in 100
waited 5,785 steps or longer" in red.

## Scene 5 · Split by night · 2:40–3:45 · [ANALOGY] [SHOW] [PREDICT] [PAUSE] [LOOP-PAYOFF]

VO: The box office grows by nights, not by seats. Friday's seats never clash with Saturday's. And claims for @bob
never clash with claims for @ana.

So split the log into partitions: separate logs, each with its own processor. Here, four. Which partition does a
claim go to? A hash of its handle picks it. A hash is a number worked out from the text, always the same for the
same text.

The hash of ana is 96,724. Divide by four, and the remainder is 0. So user 17's claim goes to partition 0, at offset
0, its first place. User 43's claim names the same handle, so it lands in the same partition, right behind it, at
offset 1. Whatever the two phones' clocks say, the log has now fixed the order.

Processor 0 reads them in order. What does it say to each? Pause and guess.

(three seconds)

Offset 0: ana is free, so it's noted as user 17's, and the claim is granted. Offset 1: ana is taken, so user 43 is
told no. Nothing else can change processor 0's table.

Meanwhile a claim for @bob hashes to partition 1, and processor 1 decides it at the same moment. With eight
partitions, the simulation's slow tail fell from 5,785 steps to 2,274, and no handle was given out twice.

SCREEN: The one row splits into P0 to P3, one processor each; header "claims log, 4 partitions". Caption
'partition = hash(handle) ÷ 4, the remainder', then 'hash("ana") = 96,724; 96,724 ÷ 4 leaves 0'. P0 glows. Chips r-1
and r-2 slide from the phones into P0, offsets 0 and 1. Countdown bar. Dots run to processor 0: "taken: ana → u-17",
u-17 "granted @ana" (green), then u-43 "refused" (red). r-3 @bob slides into P1, processor 1 "taken: bob". Caption
"8 partitions: 1 in 100 waited 2,274 steps or longer; handles given twice: 0".

## Scene 6 · The wrong key · 3:45–4:35 · [BREAK] [PREDICT] [PAUSE] [JOKE:is-the-explanation] [NAME]

VO: Now let's break it on purpose. Say someone routes claims by user ID instead, so each user's requests stay
together. It sounds tidy. Where do the two claims for @ana go now? Pause and guess.

(three seconds)

User 17 hashes to partition 2, and user 43 to partition 3. Two processors, two empty tables, and both say yes.
Nothing failed, and nothing was logged. And @ana has two owners again.

That's two clerks, each with a copy of Friday's chart, both politely selling seat F12. The simulation counted 937
extra owners that way. The plain check, then save, gave 31.

So the value that picks the partition is called the partition key. And for a rule like this one, the partition key
is the rule. Every claim for one handle must meet one decider, one after the other.

SCREEN: The partitions empty. Caption in red 'partition = hash(user ID) ÷ 4, the remainder'. Countdown. r-1 slides
to P2, r-2 to P3; processors 2 and 3 both "taken: ana" in red, both phones "granted @ana" in red. Caption
"by user ID: 937 extra owners   check, then save: 31". Then the caption turns green: "partition key = handle: one
decider per handle", and the chips slide back into P0.

## Scene 7 · When the clerk faints · 4:35–5:10 · [GUARDRAIL] [BREAK of the analogy]

VO: The box office picture breaks at a crash. A clerk who faints still has her decisions on the chart. A crashed
processor loses its memory. It gets it back by reading its partition again from offset 0, deciding the same way, in
the same order. So ana goes to user 17 again.

And each claim carries a request ID, one per tap. If user 43's claim arrives again, the processor finds that ID
among its answers and gives the same answer: no.

SCREEN: Processor 0 turns grey: "crashed: table lost". A yellow cursor steps over offsets 0 and 1; dots run;
"taken: ana → u-17" comes back. A chip "r-2 @ana, again" lands at offset 2; processor 0 "r-2: same answer, no".

## Scene 8 · The moral, and a check · 5:10–5:45 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, how were two people both told yes? There were two deciders, each sure it was alone. The fix is one decider
per handle: a partition keyed by the handle, where one processor says yes or no, in order.

One quick check. Two people ask for @leo at the same moment. Which processor decides, and who gets it? Pause and
think.

(three seconds)

Leo hashes to partition 2. Processor 2 decides both claims, and the one that landed first in the log gets @leo.

SCREEN: Caption "one decider per handle, one after the other". Two @leo chips (r-5, r-6) wait on the left. Countdown.
They slide into P2 at offsets 0 and 1; processor 2 "taken: leo"; r-5 green, r-6 red.

---

### Beat check

- Opens with QUESTION (scene 1), from a felt symptom (money sent to the wrong Ana).
- FAMILIAR (the code that reads like the rule) and PAIN with the first BREAK (scene 2), then WISH.
- ANALOGY + MAP (scene 3) before any of the words processor, log, partition.
- SHRINK to one log (scene 4); PREDICT with PAUSE three times (scenes 5, 6, 8), each followed by SHOW.
- BREAK on purpose: the user-ID key (scene 6); the analogy's limit at a crash (scene 7).
- NAME after SHOW: processor and log (scene 3, after the box office), partition and hash (scene 5), partition key
  (scene 6, after the viewer has watched the wrong one fail).
- GUARDRAIL (scene 7: crash and replay, request IDs; the cost of waiting in scene 4) and MORAL (scene 8) come last.
- Light moments: the other Ana's nice Saturday, polite tests, one clerk for every show in the city, two clerks
  politely selling F12.

### Accuracy notes for the producer

- The lesson's stepper uses 4 partitions and Kotlin's `"ana".hashCode()` = 96,724, remainder 0; u-17 hashes to
  partition 2 and u-43 to 3. The video shows exactly that. "bob" (97,717) and "leo" (107,030) were computed the same
  way: remainders 1 and 2.
- The simulation numbers (2,000 claims for 200 handles, p99 5,785 steps with one partition, 2,274 with eight, 31
  duplicates for check-then-insert on 64 servers, 937 extra owners keyed by user ID) come from the lesson's demo
  output. "One claim in a hundred waited this long or longer" is the plain reading of p99; steps are the simulation
  scheduler's, not milliseconds.
- "Nothing to wait on" simplifies the lesson's paragraph on read committed: each check looked for a row that didn't
  exist, so there was no row to lock. The lesson's fix inside one database (a unique index) is left to the text.
- The many-leader replication case and the link to consensus are left to the lesson.
- The request ID retry: the lesson says a processor that sees `r-2` again after a crash finds its ID among its
  answers and repeats the answer. The video shows the retry as a new record at offset 2.
- `@ana` is said "at Anna" and a bare "ana" "Anna" through `SAY` rules (a bare "ana" was heard as "honor"); on-screen
  text keeps "@ana". The rendered narration is slightly trimmed from the lines above; the scene file has the exact text.
