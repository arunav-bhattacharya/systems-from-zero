# What did OK mean? Count the clerks who must answer

- Slug / scene: `quorums`, `videos/scenes/quorums.py:Quorums`
- Lesson: `repl-07`, section 1, "Count the copies: why R + W > N makes a read meet the write"
- Audience / level: a complete newcomer. Knows a balance and an app; nothing about replicas, leaders or Cassandra.
- Length: 5:26 (~925 words; Kokoro speaks about 180 a minute, two 3-second pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=213` (the R = 2, W = 2 rule on screen: two read rings over B and C, panel "R + W 4 > N: they meet")
- The learner's real question: the app said OK, so why does the phone still show the old balance? What did OK mean?
- Misconception to steelman and break: "just read from two copies". It works in the café only because the W = 1
  write happened to reach two clerks; with the write on A only, a read of B and C gets two old answers that agree.
- Concept chain: three copies, nobody in charge → wait for all (slow, blocked by one absence) vs wait for one
  (stale reads) → name W, R, N → with W = 2, R = 2 every pair meets the write → R alone is luck → R + W > N, quorum
  → the N = 3 table → what still works with clerks away → Cassandra's consistency level and its low default → the
  limit (two writes at once)
- Analogy family: the lesson's three clerks in three towns, each with a copy of the same account book; you phone each
  entry to all three. Clerk out to lunch = replica down.
- Open loops: "what did OK mean?" planted in scene 1 → answered in scene 4 (for W = 1) and scene 9 (in general).
- Assumptions: amounts are the lesson opening's 100.00 and 70.00 (the lab stores cents: 10000 and 7000); t1 and t2
  as in the stepper. Which clerk is down follows the stepper (C).

## The one picture

Far left: the owner's phone (balance). Left: the coordinator (blue), with grey arrows to the three clerks. Centre
column: clerk A, B, C, each "amount @ time"; a clerk with the newest write has a gold outline and gold value, a stale
value is red, an absent clerk is greyed with a red status. Green rings mark the clerks a read asks. Right: the panel of
counts (N, W gold, R green, R + W and the verdict), which becomes the N = 3 table for one beat. Captions at the bottom.

## Scene 1 · The hook · 0:00–0:25 · [QUESTION] [LOOP-PLANT]

VO: Picture a café owner checking her balance on her phone. A minute ago, she moved 30.00 out of her account, and the
app said OK. So the balance should be 70.00. Her phone still shows 100.00. The app said OK, and the app is showing the
old number. So what did OK actually mean? Hold that question.

SCREEN: A large phone, 100.00. A gold slip "moved out -30.00, the app said: OK"; "should be 70.00" in green; a "?".

## Scene 2 · Three copies, nobody in charge · 0:25–0:50 · [FAMILIAR]

VO: Behind the app, each balance is kept on three computers, so one can break safely. With one computer in charge,
you'd just ask that one. Here, none of the three is in charge. Whichever computer gets a request passes it on to all
three copies. Let's call that computer the coordinator.

SCREEN: The phone shrinks to the corner; three copies, each "100.00 @ t1"; the coordinator and its arrows; dots run
to all three.

## Scene 3 · The clerks · 0:50–1:30 · [ANALOGY] [MAP]

VO: Let's leave computers for a moment. Picture three clerks in three towns, each keeping a copy of the same account
book. You phone each new entry to all three, and each clerk writes down the amount and the time of your call. The
question is: how many must say written before you hang up? Let's map it. Each clerk is a copy, which is called a
replica. You, making the calls, are the coordinator. And every entry carries its time, so when two books disagree, the
newer entry wins.

SCREEN: "copy A" becomes "clerk A"; header "three clerks, three towns, one account book"; captions for each mapping.

## Scene 4 · All, or one · 1:30–2:50 · [PAIN] [JOKE:amplify] [SHOW] [WISH]

VO: First idea: wait for all three. Then every book has every entry, and any clerk you ask later is right. But every
call is as slow as the slowest clerk. And if one clerk is out to lunch, you can't write anything at all. One sandwich,
and the whole account is frozen.

Second idea: wait for just one. Fast, and almost always possible. That's what the café's app did. Clerk C was
restarting when the call came. A and B wrote down 70.00 at time t2, and the app heard OK after the first one answered.
Then C comes back, still holding 100.00 from t1. And the phone's next read asks just one clerk. It happens to be C.

So OK meant: at least one clerk wrote it down, somewhere. Nothing promised that the read would ask that one. What we
want is simple: the clerks a read asks should always include at least one who has the write.

SCREEN: Panel N 3, W 3; C greyed "out to lunch". Then W 1; C "restarting"; gold dots reach A and B (C's stops short);
OK by the phone; C back with a red 100.00; R 1, a green ring on C; the red answer reaches the phone.

NOTE: The sandwich is the light moment, and it is the cost of W = 3 in one image.

## Scene 5 · Count both sides · 2:50–3:45 · [SHRINK] [PREDICT] [PAUSE] [SHOW] [NAME: read repair]

VO: Let's give the two sides names. W is how many clerks must confirm a write. R is how many clerks a read asks. N is
the number of copies, three. Try W equals 2 and R equals 2. The write is on A and B. The read asks any two clerks. Can
it pick two who both missed the write? Pause and guess.

(three seconds)

Let's try every pair. A and B: both have it. A and C: A has it. B and C: B has it. Every pair includes a clerk with the
write. Say it asks C and A. C says 100.00 at t1. A says 70.00 at t2. The newer one wins, so the read returns 70.00.
And on its way out, the coordinator tells C the new entry, so C catches up too. That's called read repair.

SCREEN: Countdown bar. Green rings on each pair in turn, the gold clerk in each pair glowing. Dots return from C (red)
and A (gold); "returns 70.00"; the phone turns 70.00. A teal arrow carries 70.00 @ t2 to C.

## Scene 6 · Break "just read from two" · 3:45–4:15 · [BREAK] [JOKE:release]

VO: Now, you might be thinking: so the fix is to read from two. Let's be fair to that idea. In the café, R equals 2
would have worked. But only by luck. The write happened to reach two clerks, and W equals 1 promised only one. Run it
again, with the write reaching only A. Now a read of B and C gets 100.00 from both. Both agree, both are old, and
nothing says so. Well... that's two wrong answers in perfect agreement. So it's never R alone, or W alone. It's the two
together.

SCREEN: W back to 1; B and C back to red 100.00; rings on B and C; two red dots; the phone red 100.00.

## Scene 7 · The rule and its name · 4:15–4:50 · [NAME]

VO: Here's the rule. If R plus W is more than N, every read meets every write the client heard OK for. Two plus two is
four, and you can't fit four different clerks into three towns. At least one is in both groups. A group big enough to
overlap every other such group is called a quorum. For three copies, a quorum is two. For three copies, here are the
choices. One and one is fast, but can be stale. Two and two is the common choice. One and three gives fast writes and
slow reads. Three and one gives fast reads, and one absent clerk blocks every write.

SCREEN: Panel "R + W 4, > N: they meet"; rings on B and C, B glows; the panel becomes the table W R meet? (1 1 no,
2 2 yes, 1 3 yes, 3 1 yes), one row per phrase.

## Scene 8 · What still works, and the guardrail · 4:50–5:30 · [GUARDRAIL] [JOKE:soften]

VO: The same count decides what still works while clerks are away. With one of three away, two and two still work. With
two away, both fail, and the coordinator refuses before it even tries. Cassandra, a free database that spreads its data
over many computers, works this way. Each request picks its own count, with a setting called the consistency level.
ONE waits for one copy. QUORUM waits for two of three. ALL waits for every copy. And here's the catch. Out of the box,
Cassandra's shell starts at ONE. So until you choose, you're the café. Write and read at QUORUM, and you're back to two
plus two. One more limit. Counting copies isn't a transaction. If two people write the same balance at the same moment,
the later time wins, and the other write is gone without an error. That's the next lesson.

SCREEN: B then C greyed "away"; a red cross under the coordinator. Caption "ONE = 1   QUORUM = 2 of 3   ALL = 3";
the panel drops to W 1, R 1, "not > N" and the phone turns red 100.00; back to 2 and 2, phone 70.00.

## Scene 9 · Moral and a check · 5:30–5:55 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE] [RECAP]

VO: So, what did OK mean? It meant W copies have the write. Whether your read sees it depends on R. Keep R plus W above
N, and the two groups have to meet. One quick check. Writes wait for one clerk. How many clerks must a read ask, to be
sure it sees the write? Pause and think.

(three seconds)

All three. One plus three is four, more than three. Any fewer, and the read could miss the one clerk who has it.

SCREEN: Panel W 1, R ?, "must be > N"; only A gold. Countdown. Then R 3, rings on all three, A glows; last caption
"R + W > N: the read and the write must meet".

---

### Beat check

- QUESTION first (the phone, "what did OK mean?"); FAMILIAR (one computer in charge) before the analogy.
- ANALOGY + MAP (the clerks, each mapping captioned); PAIN of both obvious choices, WISH said out loud.
- PREDICT + PAUSE twice (any pair missing the write; the check), each followed by SHOW.
- BREAK: "just read from two" steelmanned (it did work in the café) and broken with the write on A only.
- NAME after SHOW: replica (on the map), W/R/N, read repair, R + W > N, quorum, consistency level.
- GUARDRAIL and limit (what works with clerks away; the low default; two writes at once), then MORAL and the check.
- Light moments: the sandwich (1:50), two wrong answers in agreement (4:05), "until you choose, you're the café" (5:10).

### Accuracy notes for the producer

- The lesson stores cents (10000, 7000); the video says 100.00 and 70.00, as the lesson's opening does.
- With W = 1 the coordinator still sends the write to every replica it can reach (the Cassandra docs: writes are
  always sent to all replicas); A and B both store it, and OK comes after the first acknowledgement, as in the stepper.
- "C restarting" stands for the lesson's crashed replica; its hint is not delivered yet (section 2 covers hints).
- Read repair is shown as the stepper's frame 6: the coordinator writes the newer value back to the replica it asked.
  Section 2 covers when Cassandra does this and its limits.
- "Cassandra's shell starts at ONE" is the lesson's `cqlsh` default; the Java driver 4.19 starts at LOCAL_ONE (left out).
- LOCAL_QUORUM, ANY and Dynamo's read-heavy R = 1, W = N services are left to the lesson. Of the lesson's five limits
  the video names only concurrent writes, which the next lesson takes apart.
- SAY rules: "100.00" said as "100", "t1" as "tee 1", ONE/QUORUM/ALL said as words.
