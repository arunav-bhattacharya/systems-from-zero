# A copy that never stops recovering: how a PostgreSQL standby follows

- Slug / scene: `pg-replication`, `videos/scenes/pg_replication.py:PgReplication`
- Lesson: `repl-04`, section 0, "Building a standby: a copy that replays the primary's log"
- Audience / level: a complete newcomer. Knows a database keeps records; doesn't know pages, the write-ahead log,
  crash recovery, LSNs or replication slots.
- Length: about 5 minutes (~820 words of narration, two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: the paused-replay test, with written and flushed at the newest byte, replayed behind, counts 1,007 and 7
- The learner's real question: how do you copy a database that never stops changing, while it keeps running? And
  does that copy save you from a mistake?
- Misconception to steelman and break: (1) "the standby has the WAL, so it shows the new rows", broken by the
  paused-replay test (count 7 while the WAL is on its disk); (2) "the primary keeps the log as long as a standby
  needs it", broken by a stopped standby that finds its WAL deleted; then the slot's own danger, a disk filled for
  a standby that's never coming back.
- Concept chain: pages and the WAL → crash recovery replays the WAL after a checkpoint → a copy whose recovery never
  ends, fed the primary's WAL, is a standby → three positions: written, flushed, replayed → a stopped standby needs
  a slot → a slot needs a limit (hardest last)
- Analogy family: the café's notebook of payments, with a photocopy in another town; each new line is read out over
  the phone and written into the copy. The slot is a note by the notebook: "keep every page from line 5; the other
  town still needs them."
- Open loops: "does the copy save you from a mistake?" planted in scene 1 → paid off in scene 8 (it copies the
  2:30 cleanup too; that needs a backup).
- Assumptions: numbers are the lesson's (8 KB pages; refund count 7 then 1,007; 1,000 rows; write and flush lag 2 and
  7 ms; replay 196,512 bytes, about 192 KB, behind; LSNs 0/5111380 and 0/50E13E0; a 10-second idle timeout, wal_status
  lost, idle_timeout). The tape of seven WAL cells and the three page squares are a picture, not real sizes.

## The one picture

Left: the primary (blue): its WAL as a tape of cells filling left to right, three data pages and a refund count.
Right: the standby (teal): its own `pg_wal` tape, the same pages and count, with three markers under the tape:
written, flushed (green), replayed (yellow). Between them, the network arrow. Under the boxes, the process names and
a work area for commands, the positions and errors. Gold cells are the 1,000 new refunds; red is loss or danger.

## Scene 1 · The question · 0:00–0:25 · [QUESTION] [LOOP-PLANT]

VO: Picture a payments company at night. One computer, the primary, keeps every card payment. If its disk dies,
payments stop. So we want a second computer with a copy, a few milliseconds behind, while the first keeps working.
How do you copy a database that never stops changing? And a darker question: if someone deletes the wrong rows, does
the copy save you? Hold that one.

SCREEN: Title card. The primary box, its pages and count. A red crack and "disk failed" flash on the box, then go.
A dashed empty box on the right with "?".

## Scene 2 · The log, and crash recovery · 0:25–1:05 · [FAMILIAR] [SHRINK]

VO: PostgreSQL, a free database program, keeps its data in files cut into 8 KB pages. Before it changes a page, it
adds a note of the change to the end of a log file, the write-ahead log, or WAL. It only ever adds to the end. If the
server crashes, it goes back to the last checkpoint, a moment when every change so far had reached the data files.
Then it replays each note written after it. That's crash recovery.

SCREEN: Three page squares, "8 KB pages". Notes 1 to 4 drop onto the tape, each followed by a dot to a page. A
dashed checkpoint line after note 2. A red flash "crash"; a yellow cursor replays notes 3 and 4 onto the pages.

## Scene 3 · Recovery that never ends · 1:05–1:45 · [ANALOGY] [MAP] [NAME] [JOKE:pivot]

VO: Now here's the trick. Take a copy of the data folder, and never let its recovery end. Keep feeding it the
primary's WAL as it's written, and the copy replays each note onto the same pages. That copy is a standby. It's
recovering from a crash that never ends, and that's the whole point. Picture the café's notebook, with a photocopy
in another town. Each new line is read out over the phone and written into the copy. The notebook is the WAL, the
phone line is the network, and the copy is the standby. And it's a copy byte for byte: the same pages, the same
row positions, the same major version, the 18 in 18.1.

SCREEN: The standby box fills in; the network arrow; a dot runs, a note lands on the standby's tape, the replay
cursor applies it. A mapping block: "notebook = WAL", "phone line = network", "the copy = standby". Caption "byte for
byte: same pages, same row positions, same major version (18 in 18.1)".

## Scene 4 · Building one · 1:45–2:30 · [SHOW]

VO: One command builds it: pg_basebackup. It copies the running primary's data folder over the network, plus the WAL
written while it copies. Its dash R option leaves a small empty file, standby.signal, which says: start as a standby,
and stay in recovery. Then two processes, running programs, hold the phone line: the walsender on the primary and the
walreceiver on the standby. The walreceiver writes the WAL into the standby's own folder and forces it onto the disk.
Then the startup process replays it.

SCREEN: Command chip `pg_basebackup -X stream -R`. Pages and tape cells fly across. A chip "standby.signal". Process
chips under the boxes: walsender, walreceiver, startup. A note runs across; the "flushed" marker steps, then the
"replayed" marker.

## Scene 5 · Three positions, and a test · 2:30–3:35 · [NAME] [PREDICT] [PAUSE] [SHOW] [BREAK]

VO: A place in the WAL is an LSN, a log sequence number: a count of bytes from the start of the log. The primary's
report, pg_stat_replication, shows three of them for each standby: written, flushed to disk, and replayed. Only
replayed is what queries on the standby see. Let's test it. Pause replay on the standby, and insert 1,000 refunds on
the primary. Has the WAL reached the standby? And what will a count of refunds there say? Pause and guess.

(three seconds)

The WAL arrived. Write and flush lag were 2 and 7 milliseconds. But replay is 196,512 bytes behind, about 192 KB, and
the count still says 7. Resume replay, and the count is 1,007 at once, because the WAL was already on its disk.

SCREEN: "LSN: a count of bytes from the start of the log", e.g. `0/508F830`. Three markers, labelled. "replay:
paused". Three gold cells on the primary, count 1,007; they stream across; written and flushed move to the end;
replayed stays. A table: written 0/5111380, flushed 0/5111380, replayed 0/50E13E0, "196,512 bytes behind". Count 7.
Then "replay: resumed", the yellow marker sweeps, count 1,007.

## Scene 6 · When the standby stops · 3:35–4:20 · [BREAK] [ANALOGY] [NAME]

VO: Now stop the standby for a while. At each checkpoint, the primary deletes old WAL files, called segments, once its
own crash recovery no longer needs them. It doesn't ask the standby. When the standby comes back, it gets: requested
WAL segment has already been removed. It must be built again from a fresh copy. The fix is a replication slot, a note
on the primary of the oldest WAL this standby still needs. In the café, it's a note by the notebook: keep every page
from line 5, the other town still needs them.

SCREEN: The standby dims, "stopped". Checkpoint; cells 1 to 3 on the primary turn grey and vanish. The standby
lights, asks for an old cell; a red error. Reset; a gold flag under line 5 and a chip "slot: oldest WAL needed"; the cells from 5 on
stay.

## Scene 7 · A slot needs a limit · 4:20–5:00 · [GUARDRAIL] [JOKE:is-the-explanation]

VO: A slot is loyal. Too loyal. If its standby is gone for good, the slot keeps WAL forever, until the folder fills the
disk and the primary stops. Every payment stops, to save letters for a town nobody lives in. So drop slots you no
longer use, and give the primary a limit: max_slot_wal_keep_size, or, new in PostgreSQL 18, idle replication slot
timeout. With the standby stopped and that timeout at 10 seconds, the next checkpoint gave up on the slot.

SCREEN: The standby fades to a dashed outline, "gone". A disk bar under the primary fills to red, "disk full:
primary stops". Caption "drop slots you don't use; give them a limit". The two settings as chips. The lab's output:
`standby1 | f | lost | idle_timeout`.

## Scene 8 · The moral, and a check · 5:00–5:40 · [MORAL] [LOOP-PAYOFF] [RECAP] [PREDICT] [PAUSE]

VO: So, how do you copy a database that never stops changing? Copy its folder once, never let its recovery end, and
feed it the primary's WAL. Keep a slot so it can rejoin, and give the slot a limit. And the darker question? A
standby copies bytes, not meaning. When a cleanup script deletes every shop's fee rules, the standby deletes them
too, a few milliseconds later. For that you need a copy from the past: a backup. One quick check. Written and flushed
are at the newest byte, and replayed is behind. Does a query on the standby see the newest rows? Pause and think.

(three seconds)

No. Queries see only what's replayed. The bytes are on its disk, waiting.

SCREEN: The three steps as captions. A red "delete every fee rule" note runs across and is replayed. Caption "a copy
from the past: a backup". For the check, gold cells on both tapes, flushed at the end, replayed behind; countdown;
"queries see only what's replayed".

---

### Beat check

- QUESTION (scene 1) with a loop planted. FAMILIAR (scene 2). ANALOGY + MAP and NAME (scene 3), after the idea.
- SHOW (scene 4). PREDICT + PAUSE + SHOW, and the wrong model "it has the WAL, so it shows the rows" broken
  (scene 5). BREAK of "the primary keeps what the standby needs" and the slot named after it (scene 6).
- GUARDRAIL (scene 7), MORAL, LOOP-PAYOFF and a check (scene 8). Light moments: "recovering from a crash that never
  ends" (1:20), "letters for a town nobody lives in" (4:35).

### Accuracy notes for the producer

- The tape of cells stands for the WAL; real WAL is a stream of bytes cut into 16 MB segment files. "Cells 1 to 3
  deleted" stands for whole segments removed at a checkpoint.
- `pg_basebackup` options shown: `-X stream -R`; the lesson's full command also has `-h`, `-U`, `-D` and
  `-S standby1`. The `replicator` user and `pg_hba.conf` are left to the lesson.
- The lag figures (2 ms write, 7 ms flush, 196,512 bytes replay) and the LSNs are the lesson's lab run; yours differ.
  `replay_lag` as time is left out (the lesson explains why it's misleading while paused).
- The lesson's output for the slot timeout also shows the standby's FATAL line; the video shows the slot row only.
- The 2:30 cleanup script and backups are the lesson's opening and last section; the video only points to them.
