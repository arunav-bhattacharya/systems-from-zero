# Rebuilt from the log: what a database does after a crash

- Slug / scene: `wal-recovery`, `videos/scenes/wal_recovery.py:WalRecovery`
- Lesson: `store-06`, section 2, "After a crash: replay the log from the last checkpoint"
- Audience / level: a complete newcomer. Has read that a database writes a log before it changes its pages; doesn't
  know what a checkpoint, an LSN or recovery is.
- Length: 5:06 (~760 words of narration at Kokoro's ~175 words a minute, plus three pauses and silent builds)
- Poster: `POSTER=223` (recovery done: T2's records crossed out, pages 2 and 4 redone, "T2 left no trace")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: the screen said Refunded, yet neither balance was on disk when the power failed. How
  does the database rebuild them, and how does it know what's already done?
- Misconception to steelman and break: (1) "replay the whole log from its first record": it works, but it could take
  hours and the log must be kept forever (the checkpoint fixes it); (2) "every record in the log counts", as every
  line in the café's notebook does: T2's records are on disk but T2 never committed, so they must be dropped.
- Concept chain: the log holds every change → recovery starts at the last checkpoint's redo point → it redoes a change
  only where the page LSN shows it's missing → it drops what never committed → so a second crash gives the same
  result: idempotent (hardest last)
- Analogy family: the lesson's café back room. Stock counts on a whiteboard (pages), a notebook by the door written
  first (the log), a photo of the whiteboard now and then (the checkpoint), the notebook line number next to each
  count (the page LSN). The break: a database log also holds changes that never finished.
- Open loops: "how does it know what's already done?" planted in scene 1 → the page LSN in scene 6; the
  photo (scene 2) → named the checkpoint in scene 5; the refund (scene 1) → answered in scene 10.
- Assumptions: the hook is the lesson's opening (a 25.00 refund, about 200 bytes of log). The mechanism uses the
  lesson's stepper exactly: four pages, T1 moves 300 from page 1 to page 2, records of 29 bytes at LSN 0 to 261, the
  log durable to 116 and then 290, page 1 written by the background writer, T2 never commits, T3 sets page 4 to 42.

## The one picture

Top: the log since the last checkpoint, ten records in a row (BEGIN/UPD/COMMIT), coloured by transaction (T1 blue, T2
purple, T3 teal), the LSN under each; dashed while in the log buffer, solid once on disk; "on disk up to LSN ..." at
the top right. A yellow "redo point" marker at the left end. Middle row: pages 1 to 4 in memory (value and LSN, "dirty"
in gold, "redone" in green, "skipped" in grey). Bottom row: pages 1 to 4 on disk. Under them, one status line that
states each redo check. Dots run from a record down to the page it changes.

## Scene 1 · The refund · 0:00–0:22 · [QUESTION] [LOOP-PLANT]

VO: Picture a café owner pressing Refund. The app takes 25.00 from her shop's balance, adds it to a customer's,
and the screen says Refunded. A second later, the power fails. At that moment, neither balance had changed on disk.
The database had only added about 200 bytes to the end of one file, the log. So how does it rebuild both balances,
and know what's already done?

SCREEN: Title card. "shop's balance -25.00" → "customer's balance +25.00", a green "Refunded" chip. The screen goes
dark for a moment. A blue box "on disk when it said Refunded: both balances unchanged, the log: about 200 bytes added
at the end". A "?".

## Scene 2 · The back room · 0:22–0:58 · [FAMILIAR] [ANALOGY] [MAP] [LOOP-PLANT]

VO: A café's back room has the same problem. The stock counts sit on a whiteboard, quick to rub out. But before
anyone changes a number, they write the change in a notebook by the door. If the whiteboard gets wiped, the notebook
can rebuild it. Nobody wants to replay a notebook from page one. So now and then, someone takes a photo of the
whiteboard. After a wipe, start from the last photo, and replay only the lines after it. Map it: the whiteboard is
the pages in memory, and the notebook is the log on disk.

SCREEN: Row "the whiteboard" (four empty frames); two notebook lines at the top; a dot from a line to the board. The
board flashes red (wiped), dots rebuild it. Row "the last photo" below; dots copy the board down, then back up, then one
newer line replays. Mapping: the labels become "pages in memory", "the log (LSN under each record)", "pages on disk".

## Scene 3 · The lab's model · 0:58–2:00 · [SHRINK] [SHOW] [NAME]

VO: The lab's model has four pages, one number each. At the last photo, page 1 held 1,000. Transaction T1 moves 300
from page 1 to page 2. A transaction is a group of changes that must all happen, or none. It writes four records to
the log: BEGIN, two updates, and COMMIT. Each record's place in the log, counted in bytes, is its LSN, its log
sequence number. COMMIT forces the log to disk up to LSN 116. The pages change in memory only, stamped 116. Later,
the background writer, a process that saves changed pages, writes page 1 to disk, LSN and all. Page 2 is still only
in memory. That's fine: the log has all of T1. Then T2 starts moving 50 from page 2 to page 3, and T3 sets page 4 to
42 and commits. T3's flush writes T2's records to disk too, because the log is one stream.

SCREEN: The stepper's first four frames. Four dashed T1 records turn solid; "on disk up to LSN 116". Pages 1 and 2 in
memory become 700 and 300, "LSN 116, dirty". A gold dot copies page 1 to disk (700, LSN 116). T2's three records
(dashed, purple), T3's three (teal); page 4 = 42 in memory; all turn solid, "on disk up to LSN 290"; T2's records
pulse.

## Scene 4 · The power fails · 2:00–2:15 · [PAIN]

VO: Then the power fails. Memory is gone. Left on disk: the log up to LSN 290, and pages that are partly up to
date. Page 1 lost its 300, and page 2 never got it.

SCREEN: Dark flash; every page in memory reads "gone" in red. The durable mark and the disk pages pulse; status "on
disk: 300 left page 1, and never reached page 2".

## Scene 5 · Where to start · 2:15–2:42 · [BREAK] [NAME] [LOOP-PAYOFF]

VO: Where should recovery start? The log's first record would work, but that could take hours, and the log could
never be thrown away. That's the photo. A checkpoint writes every changed page to disk, forces it there, and then logs
a redo point, where recovery may start. PostgreSQL, a free database program, takes one every 5 minutes, or after
about a gigabyte of log.

SCREEN: Purple caption "start at the very first record of the log?", then "it works, but it could take hours, and the
log must be kept forever". The yellow "redo point" marker draws at the left end of the log. Captions for the checkpoint
and PostgreSQL's schedule.

## Scene 6 · Redo, with the page LSN · 2:42–3:08 · [SHOW] [NAME] [LOOP-PAYOFF]

VO: Recovery reads the log from the redo point. At T1's COMMIT, it redoes T1's changes, but only where a page is
missing them. How can it tell? Page 1 on disk says LSN 116, so it already has every change up to 116: skip. Page 2
says LSN 0: apply the 300, and stamp 116. That stamp is the page LSN. On the whiteboard, it's the notebook line number
written next to each count.

SCREEN: Memory refills from disk ("pages in memory, rebuilt"). T1's records glow. Status lines: "T1's COMMIT ends at LSN
116", "page 1: LSN 116, not below 116: skip", "page 2: LSN 0, below 116: apply 300"; a green dot into page 2, "300,
LSN 116, redone". Caption defines the page LSN.

NOTE: Clean walkthrough, no jokes.

## Scene 7 · The unfinished transaction · 3:08–3:44 · [PREDICT] [PAUSE] [BREAK] [SHOW]

VO: Next come T2's records. They're on disk, written by T3's commit. Does recovery apply them? Pause and guess.

(three seconds)

No. T2 has no COMMIT, so recovery drops its records. Here the whiteboard picture breaks. Every line in the café's
notebook counts. A database log also holds changes that never finished. At T3's COMMIT, page 4 says LSN 0, below 290,
so 42 goes in. After 290, the next record doesn't check out. That's the end of the log.

SCREEN: Countdown. T2's three records dim, with a red cross above each. Caption names where the analogy breaks. "page 4: LSN 0,
below 290: apply 42"; a dashed red line after the last record; "every committed change is back; T2 left no trace".

## Scene 8 · Crash again · 3:44–4:08 · [PREDICT] [PAUSE] [NAME] [JOKE:release]

VO: Now the nasty case. The power fails again, halfway through recovery. What does the next recovery do? Pause and
guess.

(three seconds)

Exactly the same work, with the same result. Doing it twice gives the same as doing it once. That's called
idempotent. Pull the plug on recovery as often as you like; it never holds a grudge.

SCREEN: Dark flash; memory "gone" again; countdown. Memory refills from disk, the same dots run to pages 2 and 4, page 1
"skipped"; "same log, same checks, same pages"; caption defines idempotent.

NOTE: The grudge line is the light moment after the dense redo; it restates the property (a second run changes
nothing).

## Scene 9 · One limit · 4:08–4:22 · [GUARDRAIL]

VO: One limit of the lab: it never lets unfinished changes into pages. Real engines can, so they add a step that
undoes them. PostgreSQL has none: a transaction with no commit record counts as cancelled, and stays invisible.

SCREEN: Captions; T2's records pulse.

## Scene 10 · The refund, the moral, and a check · 4:22–5:06 · [LOOP-PAYOFF] [MORAL] [PREDICT] [PAUSE]

VO: So, the refund was safe all along. About 200 bytes of log, forced at commit, held everything needed to rebuild both
balances, and the page LSNs told recovery what was already there. The moral of the story: start at the last
checkpoint, redo what a page is missing, skip what it has, and drop what never committed. One quick check. T2 also
wanted to put 50 into page 3. After recovery, what does page 3 hold? Pause and think.

(three seconds)

Zero. T2 never committed, so its change was dropped, and page 3 is as the checkpoint left it.

SCREEN: T1's records glow, then the page LSNs. The moral in yellow. "page 3 = ?" in memory; countdown; "page 3 = 0,
LSN 0"; T2's cross on `p3=50` pulses; disk page 3 pulses.

---

### Beat check

- Opens with QUESTION (scene 1), from the lesson's refund.
- FAMILIAR + ANALOGY (scene 2), MAP said out loud; the photo's name deferred and paid off in scene 5.
- BREAK: "replay from the first record" (scene 5); "every record counts" (scene 7, where the analogy breaks).
- PREDICT with PAUSE three times (scenes 7, 8, 10); SHOW right after each.
- NAME after the SHOW: LSN (scene 3, as the records appear), checkpoint and redo point (scene 5), page LSN (scene 6),
  idempotent (scene 8).
- GUARDRAIL (scenes 5 and 9), MORAL and check (scene 10). Light moments: nobody wants to replay a notebook from page
  one (0:42), the grudge (4:05).

### Accuracy notes for the producer

- Everything in the model is the lesson's stepper: 29-byte records, LSNs 0 to 261, durable to 116 then 290, changes
  reaching the pages only at commit (the lab's rule), the background writer writing page 1, T2's records made durable
  by T3's flush (group commit).
- The stepper's recovery rebuilds the pages in memory (page 1 read from disk at LSN 116, page 2 redone to 300, page 4
  to 42); the redone pages are dirty and reach the disk later. The video shows the same.
- "After 290, the next record doesn't check out": the lesson says the log ends at the first record that is short or
  fails its CRC; PostgreSQL logs it as `invalid record length`.
- During the analogy the disk row is labelled "the last photo"; after a crash the real disk can be newer than the
  checkpoint (page 1 was written after it), which the stepper shows.
- ARIES's three passes (analysis, redo, undo) are reduced to "real engines add a step that undoes them"; PostgreSQL's
  aborted row versions, invisible through `t_xmin`, are "its changes stay invisible".
- PostgreSQL's schedule: `checkpoint_timeout` 5 min, `max_wal_size` about 1 GB; it spreads the page writes over the
  interval (left to the lesson).
