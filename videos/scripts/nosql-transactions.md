# Why didn't my payment wait its turn? DynamoDB says no, and nobody waits

- Slug / scene: `nosql-transactions`, `videos/scenes/nosql_transactions.py:NosqlTransactions`
- Lesson: `txn-08`, section 0, "DynamoDB: two-phase commit with no single coordinator to wait for"
- Audience / level: a complete newcomer who has met two-phase commit in the previous lesson (recapped in plain words
  in scene 2). Knows nothing about DynamoDB, partitions or Amazon.
- Length: 5:27 (~850 words of narration, one pause for a guess, one for the check)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=207`, just after "That line is the commit point" (T1 holds A-1001 and A-2002, `T1: commit` in the ledger, T2 in
  red at coordinator two)
- The learner's real question: why did the second payment come back at once with "try again", instead of waiting
  its turn?
- Misconception to steelman and break: "the second payment should queue, because waiting is fair and safe" (broken
  by last lesson's weak spot: everyone waits on one coordinator; DynamoDB rejects a held item at once instead)
- Concept chain: two-phase commit waits on one coordinator → DynamoDB: items in partitions on storage nodes, one
  all-or-none request → prepare checks three things; a held item says no at once; one no cancels → the decision
  goes in a ledger before anything changes (commit point) → any coordinator can finish a dead one's transaction →
  two writes per item → your code retries with the same idempotency key → limits and busy items (hardest last)
- Analogy family: the lesson's travel agent booking a flight and a hotel. Holds = prepare; a seat already held → "no"
  at once, no waiting list; the file in a shared cabinet = the ledger; a colleague finishing the booking = another
  coordinator. Where it breaks: a hold lasts a day, here milliseconds (said out loud).
- Open loops: "why didn't it wait?" planted in scene 1 → answered in scene 5; "try again" scene 1 → scene 7 (the
  retry); last lesson's dead coordinator scene 2 → scene 6 (another coordinator finishes)
- Assumptions: ids, amounts and order are the lesson's stepper (A-1001 100.00; T1 30.00 to A-2002, T2 50.00 to
  A-3003; T2 prepares A-3003 first, is rejected at A-1001; T1 commits; T2 retried and commits). A-2002's starting
  50.00 and A-3003's 0.00 are the lesson's demo values (`TwoPhaseDemo.kt`). Coordinator names C1, C2, C3 are labels
  for the picture.

## The one picture

Top left: the coordinator fleet, three purple boxes C1, C2, C3, each showing the transaction it runs (T1 blue, T2
gold, T3 purple). Top right: the green ledger, "a table, with copies on several machines", with one decision line.
Below: three storage nodes, A-1001 (the family), A-2002 (the bike shop), A-3003 (the grocer), each with its balance
and "held by" or "free". Dots run between coordinators and nodes: yellow requests, green yes and commit, red no and
forget. Captions at the bottom.

## Scene 1 · The hook · 0:00–0:25 · [QUESTION] [LOOP-PLANT]

VO: Picture a family sharing one account in a payments app, with 100.00 in it. Two of them pay at the same second:
50.00 for groceries, and 30.00 for a bike repair. There's enough for both. The bike repair goes through. The
groceries come back at once, with an error: someone else is busy with this account, try again. Why didn't it just
wait its turn, like a queue at a counter? Waiting feels fair, and safe.

## Scene 2 · Last lesson's weak spot · 0:25–0:55 · [FAMILIAR] [PAIN]

VO: Last lesson, waiting was exactly the weak spot. When one payment touches records on two machines, a coordinator,
the program in charge, asks each machine to promise, writes its decision in its log, and then tells them to commit.
And if the coordinator crashes after the promises, the machines wait, holding their records locked, until that one
program comes back. Everyone in the queue waits with them.

SCREEN: Two "a machine" boxes, one coordinator C1; promises come back, padlocks appear; C1 gets a red cross.

## Scene 3 · DynamoDB · 0:55–1:30 · [FAMILIAR] [SHRINK]

VO: Today's database is DynamoDB, Amazon's database service. You store items, records you look up by a key, and
Amazon spreads them over many machines. Each slice of the data is called a partition, and lives on its own machine,
a storage node. The family's account is item A-1001. The bike shop is A-2002, and the grocer is A-3003. Three items,
three machines. DynamoDB takes a list of changes in one request, and applies all of them, or none.

## Scene 4 · The travel agent · 1:30–2:25 · [ANALOGY] [MAP] [BREAK of the analogy]

VO: So how does it avoid the waiting? Picture a travel agent booking a flight and a hotel for one trip. She asks
each to hold a booking, and a held seat can't go to anyone else. When both are held, she writes confirmed in the
file, and tells both. Here's the twist. If the seat is already held for another trip, the airline says no at once. No
waiting list. And the file sits in a shared cabinet, so if she goes home sick, any colleague can finish the booking.
Let's map it. The hold is a prepare. The file is DynamoDB's ledger. And the colleague is another coordinator,
because Amazon runs a whole fleet of them, and any one can take any transaction. The picture breaks on time. A hold
lasts a day. Here, the whole thing takes milliseconds.

SCREEN: Captions carry the story; the ledger and coordinators C2 and C3 appear as each is mapped.

## Scene 5 · Two payments collide · 2:25–3:35 · [SHOW] [PREDICT] [PAUSE] [BREAK] [LOOP-PAYOFF]

VO: Now the two payments. T1, the bike repair, goes to coordinator one. T2, the groceries, goes to coordinator two.
Phase one is prepare. Coordinator one asks the family's node to check three things. Is the balance at least 30? Is
this transaction newer than the item's last write? And is nobody else busy with it? All three hold, so the node
says yes, and notes T1 next to the item. Nothing has changed yet, but the account is now spoken for. T2 happens to
reach the grocer first, and that node says yes. Then it reaches the family's account, which T1 holds. Does T2 wait
in line? Pause and guess.

(three seconds)

No. The node rejects it at once. DynamoDB never makes one transaction wait for another's item. And one no cancels
the whole thing. Coordinator two tells the grocer's node to forget T2. Your code gets an error called
TransactionConflict. That's the family's try again.

SCREEN: The three checks listed under the nodes, each pulsing green; "held by T1" on A-1001; "held by T2" on A-3003;
a red dot back from A-1001, T2 turns red, A-3003 back to "free".

## Scene 6 · The ledger, and a dead coordinator · 3:35–4:30 · [SHOW] [NAME] [LOOP-PAYOFF]

VO: Meanwhile the bike shop's node says yes to T1. Everyone has promised, so coordinator one writes T1 commit in the
ledger, before anything changes. That line is the commit point. Now suppose coordinator one crashes, right here.
Last lesson, everything would wait for it. Here, a recovery program reads the ledger, and hands T1 to coordinator
three. Coordinator three sends the commits. Each node applies its change and lets go of the item. The family has
70.00, the bike shop 80.00. Two rounds, with a write on each item in each round. So every item in a transaction costs
two writes.

## Scene 7 · The retry · 4:30–5:05 · [SHOW] [LOOP-PAYOFF]

VO: And T2? DynamoDB's library doesn't retry it for you. Your code waits a few random milliseconds, and sends T2
again, with the same idempotency key, a unique id that makes a repeat do nothing. The new try checks the balance
again: 70 is at least 50. Everyone says yes, and it commits. The family has 20.00 left, and the grocer 50.00.

## Scene 8 · The rule · 5:05–5:30 · [NAME] [MORAL] [PRINCIPLE]

VO: So here's the rule across machines. Everyone promises first. One decision is written where a crash can't erase
it. Only then does anything change. DynamoDB adds two things. A busy item says no, instead of making you wait. And
any coordinator can finish the job.

## Scene 9 · Limits · 5:30–6:00 · [GUARDRAIL] [JOKE:reward]

VO: It has limits. One transaction holds up to 100 changes, in one Region, one of Amazon's areas of data centres.
And a busy account means more rejections and more retries, each paying for its writes. So keep transactions small,
and few on the same item. Think of it as an airline that never keeps a waiting list. A bit rude, but nobody is ever
stuck in it.

## Scene 10 · A check · 6:00–6:20 · [PREDICT] [PAUSE] [RECAP]

VO: One quick check. T3 wants to take money from the bike shop's account while T1 holds it, prepared but not yet
committed. What does the bike shop's node say? Pause and think.

(three seconds)

No, at once. T3 is cancelled, and its code tries again after T1 lets go.

---

### Beat check

- QUESTION (scene 1), FAMILIAR + PAIN (scene 2: last lesson's waiting), SHRINK (scene 3: three items, one request).
- ANALOGY + MAP and its breaking point (scene 4); SHOW, PREDICT + PAUSE, BREAK of the "wait in line" model (scene 5).
- NAME: partition and storage node (scene 3, after the picture), prepare and ledger (scene 4), commit point (scene 6),
  TransactionConflict (scene 5).
- GUARDRAIL (scene 9) and MORAL (scene 8), then the check. Light moments: "that's the family's try again" (3:30),
  the rude airline (5:55).

### Accuracy notes for the producer

- The protocol follows the lesson's account of the 2023 USENIX ATC paper: any coordinator in a fleet takes any
  transaction and stamps it with a timestamp; a node accepts a prepare only if the condition holds, the timestamp is
  newer than the item's last write, and no other transaction is in flight; a rejection cancels the transaction; the
  decision goes in the ledger before any commit; a recovery manager scanning the ledger hands a stalled transaction to
  another coordinator. The video shows that hand-over happening ("suppose coordinator one crashes"); the lesson's
  stepper states it as what would happen.
- The caller sees `TransactionCanceledException` with the reason `TransactionConflict`; the video says only
  "an error called TransactionConflict".
- Limits said: up to 100 changes in one Region. Left to the lesson: the 4 MB total, one account, Query/Scan seeing
  part of a transaction, the 10-minute client token, and the one-partition shortcut.
- Timestamps are not shown as numbers (the stepper gives T1's as 100 only).
- A-2002 starts at 50.00 and A-3003 at 0.00 as in the lesson's demo, so the totals are 150.00 before and after.
