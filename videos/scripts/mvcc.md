# Counting while people pay: keep the old row, and nobody has to wait

- Slug / scene: `mvcc`, `videos/scenes/mvcc.py:Mvcc`
- Lesson: `txn-04`, section 0, "Counting while people pay: keep the old row"
- Audience / level: a complete newcomer. Knows a table holds rows; doesn't know what a lock, a version, a snapshot or a
  tuple is.
- Length: 5:34 (~900 words of narration at Kokoro's ~180 words a minute, plus three pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=224` (the two versions of wallet 7 joined by t_ctid, the report reading slot 1 and a later query
  reading slot 2)
- The learner's real question: a report reads 2 million rows while payments change them. How can the total be exact
  when nobody waited?
- Misconception to steelman and break: "a table holds one copy of each row, which an update overwrites like a
  variable". Broken twice: with one copy you must either queue 9,000 transfers or count 250.00 twice; and an UPDATE
  of one row leaves four tuples for three rows.
- Concept chain: one copy per row forces wait-or-wrong → never overwrite: keep old versions, stamped (the notebook) →
  in PostgreSQL, tuples with t_xmin and t_xmax → a snapshot picks one version per row → MVCC, and an UPDATE is a
  delete plus an insert → the costs, and where the notebook breaks (hardest last: how the snapshot picks, left to the
  next section)
- Analogy family: the lesson's notebook where nothing is ever rubbed out: cross out the old line, write the new one,
  sign both; a reader who started at 18:00 skips later changes.
- Open loops: "how?" planted in scene 1 → answered in scene 4 ("that's why the report's total is exact"); the
  notebook's clock planted in scene 3 → broken in scene 6.
- Assumptions: numbers are the lesson's (2 million balances, 30 seconds, 300 a second, about 9,000 transfers; 250.00
  from wallet 7 to wallet 1,800,000; the figure's wallet 7 versions 500.00 and 250.00 with ids 850 and 860; the Try
  it's three wallets of 50000 cents, ids 857 and 858, 47500). The notebook's times 17:50 and 18:05 and the wallet
  strip (wallets 1, 2, 7, ..., 1,800,000, 2,000,000) are made up for the picture.

## The one picture

First a strip of wallets across the top (blue cells) with the report as a yellow frame moving along it and gold dots
for transfers. Then the notebook (blue) with two signed lines. Then the heart of it: heap page 0 with wallet 7's two
versions side by side, slot 1 (white, 500.00) and slot 2 (gold, 250.00), joined by a `t_ctid` arrow, each with its
`t_xmin` and `t_xmax`; below them the readers, the report (yellow) and a later query (green), with arrows to the
version each one reads. Red marks wrong or rolled back; captions at the bottom.

## Scene 1 · The question · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: Picture the coffee-shop payments app at the end of the month. A report adds up all 2 million customers'
balances. That takes 30 seconds. Meanwhile, 300 times a second, a payment moves money from one balance to another.
No payment creates or destroys money, so the total must come out exact. It does. And not one payment waited for the
report. Yet the report read rows that were changing under it. How?

SCREEN: Title card. The wallet strip; the report's yellow frame; "report: 2 million balances, 30 seconds",
"payments: 300 transfers a second" with gold dots hopping between wallets while the frame sweeps along.

## Scene 2 · One copy per row · 0:30–1:55 · [FAMILIAR] [PAIN] [PREDICT] [PAUSE] [SHOW] [BREAK] [JOKE:release] [WISH]

VO: Let's start where most of us start. The balances sit in a table called wallets, one row per customer. And we
picture each row as one copy, which an update overwrites, like a variable. With one copy, there are two choices.
Choice one: the report locks the table, a mark that says wait until I'm done. The total is right, and about 9,000
transfers queue for up to 30 seconds. Card readers give up long before that. Choice two: no lock. The report reads
whatever each row holds when it gets there. Watch wallet 7. The report has already counted its 500.00. Halfway
through, a transfer moves 250.00 from wallet 7 to wallet 1,800,000. Then the report reaches wallet 1,800,000. What
goes wrong? Pause and guess.

(three seconds)

That 250.00 is counted twice. Once in wallet 7, before it left, and once in wallet 1,800,000, after it arrived. And
the next run is wrong by a different amount. Well... the report just invented 250.00. The auditors won't be
impressed. So, wait and be right, or don't wait and be wrong. Neither is great. What we want is both: the report
sees one moment, and nobody waits.

SCREEN: Wallet 7 shows 500.00, flips to 250.00 and back (overwrite). A big padlock and a queue of gold dots turning
red, "about 9,000 transfers waiting, up to 30 seconds". Then no lock: the frame on wallet 7, "counted: wallet 7,
500.00"; a gold 250.00 chip arcs to wallet 1,800,000 (+250.00); the frame moves on; countdown; "counted: wallet
1,800,000, with the 250.00", "250.00 counted twice"; the wish in green.

## Scene 3 · The notebook · 1:55–2:35 · [ANALOGY] [MAP] [NAME]

VO: Picture a notebook where nothing is ever rubbed out. To change a balance, you cross out the old line, write the
new balance on a fresh line, and sign both. Someone who started reading at 18:00 can skip every change made after
18:00. They read the notebook as it stood when they began, while you keep writing. Map it. Each line is a version of
the row. The signatures are transaction numbers. And the reader's 18:00 is called a snapshot: a note of which
transactions had finished when it started.

SCREEN: The strip dims. The notebook: "17:50 wallet 7: 500.00 signed 850", struck through, "crossed out by 860";
"18:05 wallet 7: 250.00 signed 860". A chip "reader started at 18:00"; the later line fades while the reader reads,
then returns. Captions for each mapping.

## Scene 4 · The real thing · 2:35–3:45 · [SHOW] [PREDICT] [PAUSE] [LOOP-PAYOFF]

VO: Now the real thing. PostgreSQL, a free database program, keeps a table in pages of 8 KB, and each page holds
stored row versions, called tuples, in numbered slots. Every tuple has a header with two numbers. x-min is the
transaction that created this version. x-max is the one that replaced it, or zero while nobody has. Wallet 7 sits in
slot 1: 500.00, created by transaction 850. Then transaction 860 moves the 250.00. It doesn't touch the 500. It
stamps slot 1 with x-max 860, and writes a whole new version in slot 2: 250.00, x-min 860. A pointer joins the two,
oldest first. The report's snapshot was taken while 860 was still running. Which version does it read? Pause and
guess.

(three seconds)

Slot 1: 500.00. To its snapshot, 860 hasn't finished, so its stamp doesn't count yet. A query that starts after 860
commits reads slot 2: 250.00. Same row, two readers, two answers, and nobody waited. That's why the report's total is
exact. Every wallet is read as it stood at one moment.

SCREEN: The lesson's figure, built step by step: "heap page 0 of the wallets table"; slot 1 (t_xmin 850, t_xmax 0 →
860, in gold); slot 2 slides in (t_xmin 860, t_xmax 0); the `t_ctid` arrow. The report box ("snapshot taken while
860 was running"); countdown; an arrow up to slot 1; the query box ("started after 860 committed") and its arrow to
slot 2.

## Scene 5 · The name, and an update isn't an overwrite · 3:45–4:30 · [NAME] [PREDICT] [PAUSE] [BREAK]

VO: This design is called multi-version concurrency control, MVCC for short: keep several versions of each row, so
readers and writers can work at the same time. MySQL and Oracle's database do it too, and keep their old versions in
different places. So an update isn't an overwrite. It's a delete plus an insert. Try it on a small table: three
wallets, then update wallet 2. How many tuples does the page hold now? Pause and guess.

(three seconds)

Four tuples for three rows. Slot 2 is still there, stamped with x-max 858, and wallet 2's new balance sits in slot 4.

SCREEN: "MVCC: multi-version concurrency control"; both versions and both readers pulse. The Try it in two lines
(3 rows of 50000 cents; UPDATE wallet 2: balance - 2500); countdown; page 0 with four slots: wallet 1 (857, 0),
wallet 2 (857, 858, grey), wallet 3 (857, 0), wallet 2 (858, 0, gold, 47500). "page 0: four tuples for three rows".

## Scene 6 · What it costs, and where the notebook breaks · 4:30–5:05 · [GUARDRAIL]

VO: Of course, nothing is free. Old versions pile up, so a cleanup called VACUUM throws away the ones no reader can
see any more. And one forgotten open transaction can hold that cleanup back for the whole database. Two writers on
the same row still take turns. Versions free the readers, not the writers. And here the notebook breaks. Its reader
goes by the clock: skip anything after 18:00. A database can't simply go by the clock. How it picks the right
version is the next part of the lesson.

SCREEN: Slot 2 pulses and fades ("no reader needs it: VACUUM throws it away"), comes back; a red chip "one
transaction, open since the morning"; "an old snapshot might still need the old versions". Captions "versions free
the readers, not the writers", then the clock and "a database can't simply go by the clock: next, the snapshot's
rule".

## Scene 7 · The moral, and a check · 5:05–5:34 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So the moral: an update leaves the old version behind and stamps it. Each reader picks the one version its
snapshot can see. Keep the old row, and nobody has to wait. One quick check. Say 860 rolled back instead of
committing. A query starts afterwards. Which version of wallet 7 does it read? Pause and think.

(three seconds)

Slot 1: 500.00. 860's stamp only counts if 860 committed, so slot 2 never counts for anyone.

SCREEN: The two versions and both readers again; "keep the old row, and nobody has to wait". Then only the query,
"started after 860 rolled back", "860: rolled back"; countdown; a red cross on slot 2, which dims; a green arrow to
slot 1; "a stamp counts only if its transaction committed". The moral stays on the last frame.

---

### Beat check

- Opens with QUESTION (scene 1), from a felt puzzle (exact, and nobody waited).
- FAMILIAR (scene 2): one copy per row, overwritten like a variable. PAIN in both versions; WISH said out loud.
- PREDICT with PAUSE three times (scenes 2, 4, 5) and the check (scene 7); SHOW right after each.
- BREAK: the one-copy model (scenes 2 and 5); the analogy's limit (scene 6).
- ANALOGY + MAP (scene 3) before any database term; NAME after the SHOW: snapshot (scene 3, after the reader),
  tuple, t_xmin/t_xmax (scene 4), MVCC (scene 5).
- GUARDRAIL (scene 6) and MORAL (scene 7) last. Light moment: the invented 250.00 and the auditors (~1:40).

### Accuracy notes for the producer

- "Its stamp doesn't count yet" simplifies the visibility rule (section 1): a version is visible if the snapshot sees
  its creator and its deleter is 0 or not seen. For the report, 850 is seen and 860 isn't, so slot 1 is visible and
  slot 2 isn't.
- The rollback check uses section 1: an aborted transaction's versions fail the rule for every snapshot (its commit
  log bits say aborted). The video says "860's stamp only counts if 860 committed".
- "A whole new version in slot 2" and "four tuples for three rows" are the lesson's figure and Try it. The Try it's
  `t_ctid` and `heap_page_items` output are shown in simplified form (xmin/xmax per slot).
- "Two writers on the same row still take turns" previews section 2; VACUUM, the horizon and the stuck open
  transaction preview section 3; "MySQL and Oracle keep their old versions in different places" previews section 4
  (in the table, or in an undo log).
- Simplified: the report runs as one statement with one snapshot; section 1 explains when each isolation level takes
  its snapshot. A database "can't simply go by the clock" because ids don't come in commit order (section 1).
- `x-min`/`x-max` are spoken "ex min"/"ex max"; 18:00 is spoken "six p m"; amounts are spoken without ".00".
