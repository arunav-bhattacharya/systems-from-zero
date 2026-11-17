# Two answers on disk: which one wins?

- Slug / scene: `lsm-tree`, `videos/scenes/lsm_tree.py:LsmTree`
- Lesson: `store-05`, section 1, "Reading a stack of sorted files, newest first"
- Audience / level: a complete newcomer. Can read a little code; has never heard of a memtable, an SSTable or a
  tombstone, and doesn't know how a database finds a record on disk.
- Length: 5:17 (~850 words of narration at Kokoro's ~175 words a minute, plus two pauses and silent builds)
- Poster: `POSTER=208` (the tombstone stops the read: "answer: not found", SSTable 1 "not asked")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: one payment has two different records on disk, PENDING and CAPTURED. Which one does
  a read return, and how does the database know it's the right one? And how many files does it have to open?
- Misconception to steelman and break: "search the files from the oldest, like a book from page one, and take the
  first match". Broken by auth:2 (it returns last minute's PENDING), then by auth:3: a read that keeps looking for a
  value would bring a deleted payment back.
- Concept chain: files are never changed, so an update or delete is a newer record → the order of the files is the
  truth → newest first, stop at the first file that knows the key, even a tombstone → one file costs one block read
  thanks to a sparse index → but many files cost many reads: read amplification (hardest last)
- Analogy family: the lesson's clerk. A sorted tray on her desk (memtable), bound into booklets on a shelf, newest
  in front (SSTables); corrections and cancel slips go into the tray (a newer version, a tombstone). Reading: the
  tray first, then the booklets from the front of the shelf.
- Open loops: "which one comes back, and how does it know?" planted in scene 1 → answered in scene 5 and the moral;
  "how many files?" → scene 8; the read of auth:1 that costs a block read for nothing (scene 5) → the filter in the
  next section (scene 8).
- Assumptions: keys and values are the lesson's stepper (auth:1 to auth:3, PENDING, CAPTURED, a tombstone; SSTable
  1 and 2). The sparse index numbers are the lab's (blocks of 16 records, 1,000 records, 63 index entries, keys
  auth:00000 to auth:00999, one read per lookup). The 20-file case is the section's (19 and 20 useless reads).
  "form 3, 5, 7" in the clerk scene are toy forms.

## The one picture

Three tall boxes in a row, in reading order: the memtable (teal, left, "in memory"), SSTable 2 (blue, middle) and
SSTable 1 (blue, right), under "on disk, newest first". Each box lists up to three records in mono; a status line at
its bottom says "found", "not asked", "tombstone: stop". A yellow chip above the box being asked is the read
(`get(auth:2)`); grey arrows between the boxes show the reading order. Under the boxes: the answer and a count of
disk reads. Green is the right answer, red a tombstone or a wrong answer, purple the tempting wrong model. Scene 7
zooms into one SSTable (a strip of 63 blocks, block 31 opened, the sparse index in teal on the left); scene 8 turns
the shelf into 20 small files. The three boxes come back for the moral.

## Scene 1 · Two answers · 0:00–0:33 · [QUESTION] [LOOP-PLANT]

VO: Here's a card payment, named auth:2. When the bank said yes, the database saved it as PENDING: approved, but no
money has moved yet. A minute later, the money moved, and the database saved CAPTURED. Both records are on disk now,
in two different files, and neither file was ever changed. So a program asks for auth:2. Which answer comes back?
And how does the database know it's the right one?

SCREEN: Title card. A blue file box "a file on disk" with `auth:2 = PENDING`; a second, "another file", with
`auth:2 = CAPTURED`. Both pulse. A yellow chip `get(auth:2)` top left, a "?" under it, caption "which one comes
back, and how does it know?".

## Scene 2 · The clerk · 0:33–1:17 · [FAMILIAR] [ANALOGY] [MAP] [NAME] [JOKE:pivot]

VO: To see how two answers got there, picture a clerk with a pile of forms. Filing each form in its drawer means a
walk across the room, per form. That would make her the fittest clerk in the building, and the slowest. So she keeps
a tray on her desk, in order by form number. When the tray is full, she binds it into a booklet and puts it on the
shelf, newest in front. A bound booklet is never changed. A correction goes into the tray, like any new form. And to
cancel a form, she adds a slip to the tray that says cancelled.

Let's map it. The tray is the memtable: a sorted list in memory that takes every new write. A booklet is an SSTable:
a sorted file on disk that never changes. And the cancel slip is a tombstone, a record that says this key is
deleted.

SCREEN: The files go. Teal box "the tray, on her desk"; forms 7, 3, 5 drop in and sort to 3, 5, 7. They move into a
blue "booklet 1" on the right; a dashed slot in the middle, "the next one goes in front". "form 5, fixed" and a red
"form 7: cancelled" drop into the tray. Mapping: the titles become "memtable (in memory)" and "SSTable (on disk)";
"tombstone" appears under the cancel slip.

NOTE: The fittest-clerk line is the pivot joke and it carries the cost: one walk per form is one scattered write per
record, which is why the tray exists.

## Scene 3 · Build the stack · 1:17–1:59 · [SHRINK] [SHOW]

VO: Now the real thing, with three payments. auth:1, auth:2 and auth:3 arrive, all PENDING. Each goes into the
memtable, in key order. No file on disk changes. The memtable reaches its size limit, so it's written to disk in key
order, in one long write. That's called a flush, and the new file is SSTable 1. Then auth:2's money moves, so
CAPTURED goes into the memtable. And auth:3 is deleted, so a tombstone goes in. SSTable 1 isn't touched. It still
says PENDING for both. Another flush makes SSTable 2. So the disk holds two versions of auth:2, and two of auth:3.
Only the order of the files says which one is current.

SCREEN: The stepper's first four frames on the one picture. Rows slide from the memtable into SSTable 1, then into
SSTable 2. "in memory" and "on disk, newest first" above the boxes.

## Scene 4 · The tempting way · 1:59–2:17 · [BREAK]

VO: So how should a read search the files? One idea feels natural: start at the oldest, like reading a book from
page one, and take the first match. Let's try it for auth:2. SSTable 1 has it: PENDING. Done? Well... that's last
minute's answer. The money has already moved.

SCREEN: Purple caption "start at the oldest, take the first match?"; the chip goes to SSTable 1; "answer: PENDING"
turns red, "(stale)", while SSTable 2's CAPTURED pulses.

## Scene 5 · Newest first · 2:17–2:53 · [ANALOGY] [SHOW] [LOOP-PAYOFF]

VO: What would the clerk do? She checks the tray first, then the booklets from the front of the shelf, and stops at
the first one that has the form. So a read of auth:2 checks the memtable first. Not there. Then SSTable 2, the
newest file. It has auth:2: CAPTURED. The read stops. SSTable 1, with its old PENDING, is never asked. A read of
auth:1 checks the memtable. Not there. SSTable 2 doesn't have it either, and finding that out costs a block read,
for nothing. SSTable 1 does: PENDING.

SCREEN: Arrows appear between the boxes. The stepper's reads: the chip moves box to box, dots run along the arrows,
status lines ("no auth:2 here", "found", "not asked", "1 read, nothing found"), the answer and "disk reads: 1", then
"disk reads: 2".

NOTE: Clean walkthrough, no jokes.

## Scene 6 · The tombstone · 2:53–3:29 · [PREDICT] [PAUSE] [SHOW] [BREAK] [JOKE:is-the-explanation]

VO: Now auth:3, the payment that was deleted. The memtable is empty. SSTable 2 holds a tombstone, and SSTable 1
still says PENDING. What should the read answer? Pause and guess.

(three seconds)

Not found. The read stops at the tombstone. If it carried on, SSTable 1 would hand back PENDING, and a deleted
payment would come back to life. Tombstone is a good name for it. It marks the spot, and it tells you not to dig any
deeper. So the first file that knows the key wins, even when what it knows is deleted.

SCREEN: Countdown. "tombstone: stop", "answer: not found". The chip peeks at SSTable 1 ("PENDING: wrong") and comes
back; SSTable 1 greys out, "not asked". Caption "the first file that knows the key wins, even if it says deleted".

## Scene 7 · Inside one file · 3:29–4:10 · [SHOW] [NAME]

VO: That's which file. Now, what does asking one file cost? An SSTable is records in key order, grouped into blocks.
In the lab, a block is 16 records. Because the file is sorted, it doesn't need an entry for every key. A small index
holds only the first key of each block, and where that block starts. That's called a sparse index. The lab's file
of 1,000 records needs 63 entries. That's small enough to keep in memory. To find auth:00500, look for the last
block whose first key isn't above it. That's the block that starts at auth:00496. Read that one block, and scan it.
One disk read.

SCREEN: Zoom into one SSTable: a strip of 63 blocks ("block 0" to "block 62"). The teal index on the left lists
auth:00000 (block 0), auth:00016 (block 1), ..., auth:00496 (block 31), auth:00512 (block 32), ..., auth:00992
(block 62), with dashed links to the blocks. `get(auth:00500)`: the auth:00496 entry turns yellow, block 31 lights
up and opens into its 16 records; the scan steps to auth:00500 (green). Caption "one lookup in one file: one block
read".

## Scene 8 · Twenty files · 4:10–4:46 · [GUARDRAIL] [NAME] [JOKE:skeptic] [LOOP-PLANT]

VO: So one file costs at most one read. But how many files? Picture 20 SSTables on the shelf. A key that only the
oldest one holds costs 19 useless block reads first. And a key that isn't anywhere costs all 20. That's a lot of
booklets opened to learn a form isn't there. The number of disk reads for one lookup is called read amplification. LSM
trees fight it in two ways. A filter for each file lets
most useless reads skip the disk. And compaction merges files, so the stack stays short. The next part of the
lesson builds the filter.

SCREEN: The memtable and 20 narrow files numbered 20 to 1. Red crosses under 19 of them, "useless block reads: 19",
a green tick on the oldest; then 20 crosses. The files pulse red. Captions name read amplification, "1. a filter per
file", "2. compaction"; the crosses fade and the 20 files merge into one.

## Scene 9 · The moral, and a check · 4:46–5:17 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So the moral of the story: files are never changed, so their order is the truth. Read newest first, and the
first one that knows the key wins. One quick check. Say auth:1's money moves now, and CAPTURED goes into the
memtable. How many SSTables does a read of auth:1 open? Pause and think.

(three seconds)

None. The memtable knows auth:1, so it answers from memory, and no file is asked.

SCREEN: The three boxes come back as at the end of the stepper. Caption "newest first; the first file that knows the
key wins". `auth:1 = CAPTURED` drops into the memtable; `get(auth:1)`; countdown; "answer: CAPTURED, 0 files
opened"; both SSTables grey out, "not asked".

---

### Beat check

- Opens with QUESTION (scene 1), from a concrete payment with two answers.
- FAMILIAR + ANALOGY (scene 2) before the terms; MAP said out loud; NAME right after the map (the names were
  introduced in the lesson's section 0; the video re-earns them).
- BREAK: oldest-first (scene 4) and "keep looking for a value" (scene 6).
- PREDICT with PAUSE twice (scenes 6 and 9); SHOW right after each.
- NAME after the SHOW: flush (scene 3), sparse index (scene 7), read amplification (scene 8).
- GUARDRAIL (scene 8: the cost and the two fixes), MORAL and check (scene 9). Light moments: the fittest clerk
  (0:40), "that's last minute's answer" (2:12), the tombstone that says don't dig (3:22), the booklets opened to learn
  a form isn't there (4:25).

### Accuracy notes for the producer

- The stepper's first frame also appends each put to the write-ahead log; the video leaves the log to lesson 6.
- In the stepper, `get(auth:1)` skips SSTable 2 with its Bloom filter. This video comes before the filter (section 2),
  so it shows the read the filter would save ("finding that out costs a block read, for nothing"), as the section's
  20-file example does, and points to the filter as the fix.
- Block 31 starting at auth:00496 is worked out from the lab's format: keys auth:00000 to auth:00999, one index entry
  per 16 records (entries 0 to 62), and 500 = 31 x 16 + 4. The lab's test checks that a get reads one block.
- RocksDB's blocks are 4 KB by default, not 16 records; the video says "in the lab".
- Cassandra's per-column cells and hashed key order (in the section) are left to the lesson's Try it.
- "Most useless reads skip the disk": with 10 bits per key, about 1% of the filter checks still say "maybe" (the
  next section).
