# A file's name only points to it

- Slug / scene: `inodes-links`, `videos/scenes/inodes_links.py:InodesLinks`
- Lesson: `os-10`, section 0, "Names and inodes: a file's name only points to it"
- Audience / level: a complete newcomer. Has used a file browser; knows nothing about disks, blocks, inodes or the
  kernel.
- Length: 5:21 (~810 words of narration, plus two guesses and silent builds)
- Poster: `POSTER=184` (the whole picture: three cards, inode 13, the symlink and the blocks)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: someone deleted a 20 GB log and the disk is still 98 percent full. So what did
  delete actually remove?
- Misconceptions to steelman and break: (1) "a file is its name, so keep everything next to the name" (broken by a
  second name: two rows, two sizes after one append); (2) "rm deletes the file" (broken by predict-then-show: after
  `rm ledger.csv` the hard link still reads every byte, not one block is freed, and only the symlink fails)
- Concept chain: what a file system must store → one row per name breaks on two names → split the row: the inode
  (the numbered book) and directory entries (catalogue cards) → a hard link is a second card → a symlink is a card
  that says "see under" → rm removes one card (unlink) → the kernel frees a file only when no card and no program
  holds it (hardest last) → limits
- Analogy family: a library. The numbered book is the inode, a catalogue card (name and book number) is a directory
  entry, the catalogue is the directory, a "see under" card is a symlink, a borrowed book is a file a program has
  open. Where it breaks: a library has one flat catalogue, folders sit inside folders.
- Open loops: "what did delete actually remove?" planted in scene 1 → paid off in scene 8 (the log is still open)
  and scene 10 (one name)
- Assumptions: inode 13, inode 12 and block 2065 are the lesson's figure (a small disk image read with `debugfs`); a
  real machine prints numbers like 1573046. The log's name `auth.log` is taken from the lesson's later sections. The
  author card ("Okafor") and inode 14 for the new file are made up for the picture; the log's inode number isn't
  shown.

## The one picture

Left: the directory `/tmp` (teal), a catalogue of cards, each a name and an inode number. Middle: inode 13 (blue),
drawn as a book with its number on the spine: size, owner and the rest, links, blocks. Right: the disk's blocks
(grid, 4 KB each; the ledger's blocks gold). Under inode 13: inode 12, the symlink (purple). Arrows run from each
card to its inode, and from the inode to its blocks. Yellow dots are the kernel looking something up; red is a name
removed or a lookup that failed; green is a program that has the file open. Captions sit along the bottom.

## Scene 1 · The full disk · 0:00–0:25 · [QUESTION] [LOOP-PLANT]

VO: A small company's program records card payments for coffee shops. It also writes a line about every payment to
a log file, and the log has grown to 20 GB. One evening the disk is 98 percent full, so someone deletes the log. It
vanishes from the folder. And the disk is still 98 percent full. So what did delete actually remove? Hold that
question.

SCREEN: Title card. A folder box with one row, "auth.log 20 GB"; a disk gauge at 98 percent, red. The row turns red
and fades; the gauge pulses and stays at 98 percent. A yellow "?".

## Scene 2 · What a file system stores · 0:25–0:52 · [FAMILIAR]

VO: It's easy to think a file is its name. A file browser shows it that way: one name, one icon, and delete takes
both. So look at what has to be stored. A disk is a long row of equal pieces called blocks, 4 KB each. For every
file, the file system, the part of the operating system that looks after files, records which blocks hold its
bytes, its size, its owner, who may read it, and when it last changed.

SCREEN: The hook leaves. A file icon named ledger.csv; on "delete takes both" a bin appears and the icon and its
name drop into it together. The block grid draws in on the right ("disk blocks", "4 KB each"). A table header: name,
size, owner, blocks.

## Scene 3 · One row per name · 0:52–1:25 · [PAIN] [WISH] [JOKE:amplify]

VO: The simplest design keeps all of that next to the name: one row per file. It breaks on the first file you want
under two names. The payments program keeps the year's payments in ledger.csv, 2 GB. An auditor wants the same file
as ledger-2026.csv, without a copy. Now two rows must agree forever. Add one payment through ledger.csv, and its row
grows by 31 bytes. The other row still says 2 GB. Forever didn't last long. We want one place that holds the file,
and names that only point to it.

SCREEN: Row "ledger.csv 2 GB payments 2065, ..." and its gold blocks; row "ledger-2026.csv" with the same values. A
dot runs into row 1: "2 GB + 31 bytes" and one more gold block. Row 2's "2 GB" turns red with a cross. Caption:
"two rows, two sizes".

## Scene 4 · The library · 1:25–2:05 · [ANALOGY] [MAP] [NAME]

VO: Libraries solved this long ago. Every book has a number on its spine, and a catalogue card says: this title,
book 13. One book can have a card under its title and another under its author, and neither card is the book. Linux
splits the row the same way. Everything about the file moves into one box
with a number and no name: size, owner, permissions, times, a count of links, and the list of blocks. That's the
numbered book. It's called an inode, short for index node. The folder keeps only the cards: each entry is a name and
an inode number. Linux calls a folder a directory.

SCREEN: The table leaves. A book (blue, spine "13") and two cards, "title: Ledger → 13" and "author: Okafor → 13",
each with an arrow to the book. The book's title becomes "inode", its pages become the fields, and an arrow grows to
the gold blocks; the title card becomes "ledger.csv → 13", the author card leaves, and the catalogue's outline
appears: "directory /tmp". Captions map each part: the book is the inode, a card is a directory entry.

## Scene 5 · Opening a file · 2:05–2:25 · [SHOW] [BREAK of the analogy]

VO: To open /tmp/ledger.csv, the kernel, the core of the operating system, reads the top directory and finds tmp.
It reads tmp and finds ledger.csv, 13. Then it reads inode 13. Here the library picture breaks: a library has one
flat catalogue, but folders sit inside folders.

SCREEN: A small box "directory /" with the entry "tmp" appears above, with an arrow down into `/tmp`. A yellow dot
walks / → tmp → the ledger.csv card → inode 13 → its blocks. Caption: "one flat catalogue vs folders inside
folders".

## Scene 6 · A second card · 2:25–2:42 · [SHOW] [NAME]

VO: Now the auditor's name is easy. Add a second entry with the same number. That's a hard link. The inode counts
its entries: links, 2. Add a payment through either name, and there's only one size to change.

SCREEN: Command chip `$ ln ledger.csv ledger-2026.csv`. A second card "ledger-2026.csv → 13" and its arrow; links 1
→ 2. A dot runs along the new card's arrow; size becomes "2 GB + 62 bytes", one more gold block.

## Scene 7 · A card that says "see under" · 2:42–3:02 · [ANALOGY] [NAME]

VO: There's a second kind of link: a card that says, see under Ledger. That's a symbolic link, or symlink.
latest.csv is an inode of its own, number 12, and its content is a path, the 10 bytes ledger.csv. The kernel looks
that name up again every time the link is opened.

SCREEN: Chip `$ ln -s ledger.csv latest.csv`. A third card "latest.csv → 12" and a purple book under inode 13
(spine "12", "symlink", "ledger.csv", "10 bytes"). Opening it: a dot to inode 12, the word "ledger.csv" lifts off and
lands on the first card, which glows, then a dot runs to inode 13.

## Scene 8 · Predict: delete ledger.csv · 3:02–3:30 · [PREDICT] [PAUSE] [SHOW] [BREAK]

VO: Now delete ledger.csv. Afterwards, which name still works: ledger-2026.csv, or latest.csv? Pause and guess.
(three seconds) The entry is gone, and links drops to 1. ledger-2026.csv still leads to inode 13, every byte
intact. latest.csv looks up ledger.csv, finds nothing, and fails. And not one block was freed.

SCREEN: Chip `$ rm ledger.csv`. A yellow "?" by the two cards; countdown bar. The first card turns red and leaves;
links 2 → 1. A dot runs card 2 → inode → blocks, with a tick. A dot runs to inode 12, "ledger.csv" lifts off and
finds an empty slot: red cross and "No such file or directory". The gold blocks pulse: "blocks freed: 0".

## Scene 9 · rm is unlink, and when a file is freed · 3:30–4:20 · [NAME] [JOKE:is-the-explanation] [ANALOGY]
[SHOW] [LOOP-PAYOFF]

VO: So rm, the delete command, doesn't really delete. It sends the kernel a request called unlink: remove one entry,
and lower the count by one. rm sounds like a shredder. It's really an eraser for one card. The kernel frees a file
only when the count reaches 0 and no program still has it open, like a library that throws a book out only when no
card points to it and nobody has it borrowed. Delete ledger-2026.csv too, and the count is 0. Nobody has it open,
so the kernel frees it, and its blocks are free again. Now our full disk. The log lost its last name, but the
payments program still had it open, writing a line every second. It's borrowed. So all 20 GB stayed. Later in the
lesson, we'll find that file and free it.

SCREEN: Chip "rm → unlink"; caption "unlink: remove one entry, lower the count by one". Rule caption: "freed when
links = 0 and no program has it open". `$ rm ledger-2026.csv`: the second card leaves, links 1 → 0 (red), inode 13
leaves and its blocks turn grey. Then the log's inode takes its place (size 20 GB, links 0 in red, blocks: nearly
all), 15 of 16 blocks turn gold, and a grey "payments program, still writing to it" box sends dots along a white
arrow into it. Caption: "links 0, but still open: the kernel keeps all 20 GB".

## Scene 10 · Two limits · 4:20–4:38 · [GUARDRAIL] [JOKE:release]

VO: Two limits on hard links. A hard link holds only a number, so it can't reach into another file system. Book 13
in another library is a different book, maybe a cookbook. And Linux refuses hard links to directories, which could
put a folder inside itself, a loop.

SCREEN: A grey book "another disk, inode 13: someone else's file" with a crossed red arrow. The "/" box returns; a
red arrow from `/tmp` back up to "/" is crossed out: "a loop in the tree of folders".

## Scene 11 · The moral, and a check · 4:38–5:05 · [MORAL] [RECAP] [PREDICT] [PAUSE] [LOOP-PAYOFF]

VO: So, what did delete remove? One name. The file is its inode, names are cards that point to it, and the kernel
frees it only when no card and no program is left. One quick check. Someone makes a new, empty ledger.csv. Now you
open latest.csv. What do you get? Pause and think. (three seconds) The new, empty file. A symlink holds a name, not
a number, so it follows whatever has that name now.

SCREEN: Captions for the moral. A new card "ledger.csv → 14" and a new blue book (spine "14", "size 0 bytes"). A
dot runs to inode 12; countdown bar. Then "ledger.csv" lifts off, lands on the new card, and a dot reaches inode 14,
which glows: "the new, empty file".

---

### Beat check

- Opens with QUESTION (scene 1), from a felt symptom (the disk that stays full).
- FAMILIAR (scene 2), PAIN and WISH (scene 3) before any technical word for the fix.
- ANALOGY and MAP (scene 4) before the names inode and directory; the analogy's break said in scene 5, extended in
  scene 9 (a borrowed book).
- PREDICT with PAUSE: scene 8 and the check in scene 11, each with a SHOW right after.
- BREAK: one row per name (scene 3), "rm deletes the file" (scene 8).
- NAME after the picture: inode and directory (4), hard link (6), symlink (7), unlink (9).
- GUARDRAIL (scene 10) and MORAL (scene 11) last. Light moments: "forever didn't last long" (1:20), "an eraser for
  one card" (3:40), "maybe a cookbook" (4:30).
- Open loop paid off by name: "what did delete remove?" (scenes 9 and 11).

### Accuracy notes for the producer

- Inode 13, block 2065 and inode 12 come from the lesson's figure and its `debugfs` section; the Try it on a real
  disk prints numbers like 1573046. A 2 GB file has about half a million 4 KB blocks; the grid shows a handful.
- The 31-byte payment line is the lesson's `auth-7731,4111,120.00,approved` plus a newline. Appending may fill the
  last block before taking a new one; the picture lights one more block to show that the blocks belong to the inode.
- The symlink holds the 10 bytes `ledger.csv` (a relative path, looked up in the symlink's own directory), as the
  lesson's Try it shows (`10 bytes, symbolic link`). The video shows the lookup as the path landing on the card.
- `rm` calls `unlinkat` in the lesson's trace; the video says unlink, as the section does.
- The log held open by the payments program is the lesson's opening and its third section (the `LogHolder` demo,
  `df` and `du`, `lsof +L1`, truncating instead of restarting), which the video only points to.
- Whether the new `ledger.csv` gets inode 14 is up to the file system; any free inode will do.
- Left to the lesson: file descriptors and where the write position lives, "Too many open files", and the journal.
