# Copy 512 MB in 1.7 milliseconds: fork and copy-on-write

- Slug / scene: `cow-oom`, `videos/scenes/cow_oom.py:CowOom`
- Lesson: `os-07`, section 0, "Copy-on-write: how fork copies 512 MB without copying it"
- Audience / level: a complete newcomer who has met pages, frames and page tables in the previous lesson, and fork
  (a process starts a copy of itself) in an earlier one.
- Length: 5:25 (~800 words of narration at Kokoro's ~175 words a minute, plus two pauses and builds)
- Poster: `POSTER=212` (just after the copy and the reuse: the child on frame E, the parent back on C, both `rw`, "copies: 1", the copy-on-write caption)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: copying 512 MB takes 33 ms, yet the copy is running 1.7 ms after fork. How do you copy
  something faster than copying it?
- Misconception to steelman and break: (1) "a copy costs as much as the original" (the warm-up's tempting answer),
  broken by copy-everything's cost and the 1.7 ms; (2) "just share the frames", broken by a parent's write showing up
  in the child; (3) "add up RSS to count memory", broken by 1 GB against 640 MB.
- Concept chain: page tables point at frames and mark pages writable → copy every page is slow where it hurts →
  sharing frames breaks the promise of a private copy → share, mark read-only, copy one page on the first write
  (copy-on-write) → count the copies; add PSS, not RSS → the cost when everything is written (hardest last)
- Analogy family: the café's recipe binder (invented for the video; the lesson's own analogy, the overbooked flight,
  belongs to its overcommit section). The amplifier: photocopying a whole cookbook to read one recipe. The core: a second
  cook shares the binder, every page gets an ask-before-you-write sticker, and the manager photocopies just the page
  someone writes. The break: 131,072 trips to the manager against one trip to the copy shop.
- Open loops: "how do you copy faster than copying?" planted in scene 1 → answered in scenes 6 and 7; Redis's snapshot
  child in scene 3 → the check question in scene 10.
- Assumptions: numbers are the lesson's lab run (`cow.c`, 512 MB, memcpy 33 ms, child running after 1.7 ms, about 1 MB
  of page table, 32,768 copies at about 1.8 µs, Shared 384 and Private 128, RSS 513, PSS 320 + 320 = 640, 180 ms to
  write every page, a second memcpy of 28 ms). Four pages and frames A to E are the lesson's stepper.

## The one picture

Middle: RAM, a column of frames A to E, each showing its `refs` count (gold when shared). Left: the parent's page
table (blue); right: the child's (purple). Each table line ("page 2: frame C") has a mode chip, green `rw` or the gold
`read-only` sticker, and an arrow in its owner's colour to its frame. Bottom: the kernel (teal) with its status and a
`copies` counter. Yellow dots are reads, red dots are writes that hit a sticker. For the counts, the picture becomes two
bars of eight 64 MB blocks (teal shared, blue or purple private).

## Scene 1 · The question · 0:00–0:28 · [QUESTION] [LOOP-PLANT]

VO: A program fills 512 megabytes of memory. Then it calls fork, the system call that starts a second process as an
exact copy of the first. Copying 512 megabytes takes 33 milliseconds here, and needs another 512 megabytes of RAM. Yet
the copy is running 1.7 milliseconds after fork. How do you copy something faster than copying it?

SCREEN: Title card. "a program, 512 MB" → `fork()` → "its copy"; "copying 512 MB the plain way: 33 ms, and a second 512
MB of RAM" in red; "running after 1.7 ms" in green; a yellow "?".

## Scene 2 · A reminder · 0:28–0:49 · [FAMILIAR]

VO: A quick reminder. Memory comes in pages of 4 kilobytes. Each process has a page table: the kernel's list of which
frame, which piece of real RAM, holds each of its pages. Each line also says whether that page may be written. Here's a
parent with four pages. The real program has 131,072.

SCREEN: The parent's table, the RAM column (frames A to D `refs 1`, E free), four lines with green `rw` chips and arrows.

## Scene 3 · Copy everything · 0:49–1:21 · [PAIN] [JOKE:amplify]

VO: Now let's design fork ourselves. The simplest version copies every page into fresh frames. It's correct, and slow
exactly where it hurts. Redis, a program that keeps data in memory, forks a child just to write a snapshot to disk.
With 10 gigabytes of data, a child that only reads would need 20 gigabytes of RAM. Or a program forks only to start
another program, which throws the copy away at once. That's photocopying a whole cookbook to read one recipe, then
throwing it in the bin.

SCREEN: Dots stream out of every frame. Captions for Redis and for fork-then-start.

## Scene 4 · Share, and break it · 1:21–1:39 · [BREAK]

VO: Next try: share. The child gets its own page table, pointing at the parent's frames. That costs only the table,
about 1 megabyte for 512 megabytes of pages. But now, if the parent writes to page 2, the child sees the change. And the
child was promised its own copy.

SCREEN: The child's table appears with arrows into the same frames; refs become 2. A red dot from the parent's page 2
hits frame C; the child's page 2 line flashes red: "the child's page 2 changed too".

## Scene 5 · The kitchen · 1:39–2:20 · [ANALOGY] [MAP] [WISH]

VO: A café kitchen has the same problem. A second cook joins, and is promised their own copy of the recipe binder.
Photocopying all of it would take all morning, and they'll mostly just read it. So the manager does something lazier.
Both cooks share the binder, and every page gets a sticker: ask before you write. When a cook wants to change page 2,
the manager photocopies just page 2, and that copy becomes their page 2, with no sticker.

Let's map it. The cooks are the two processes. The sheets of paper are frames of RAM. The sticker is a read-only mark,
on every line of both page tables. And the manager is the kernel.

SCREEN: Gold `read-only` stickers replace every `rw` chip, on both tables. Pulses on the tables, the frames, the
stickers; the kernel box appears ("kernel: idle", "copies: 0").

## Scene 6 · What fork really does · 2:20–3:27 · [SHOW] [NAME] [PREDICT] [PAUSE]

VO: So here's what fork really does. It builds the child's table pointing at the same frames, and marks every line
read-only, the parent's too. Each frame now has two lines pointing at it. No data moved. The child reads page 1.
Reading is allowed, so the CPU loads it straight from frame B, and the kernel never hears about it. Now the child
writes to page 2. The line says read-only, so the CPU stops the write, and hands control to the kernel. That's called a
page fault. The kernel sees that the page may really be written, and that frame C is shared. So it copies frame C's 4
kilobytes into a free frame, E. It points the child's line at E, and makes it writable. Then the write runs again, and
lands in E. Now the parent writes to page 2. Its line is still read-only, so it faults too. Will the kernel copy frame
C again? Pause and guess.

(three seconds)

No. Only one line points at C now, so nobody else can see it. The kernel just makes the line writable again, and copies
nothing.

SCREEN: Stickers and refs pulse; a yellow read dot from the child's page 1 to B; a red write dot stopped by the child's
page 2 sticker; a red arrow to the kernel, "kernel: page fault"; "copy C to E", a dot from C to E, E `refs 1`, C `refs
1`, "copies: 1"; the child's page 2 arrow moves to E with a green `rw`. The parent's write faults too; countdown; the
parent's page 2 turns `rw`, "kernel: reuse C, no copy", "copies: 1" pulses.

NOTE: Clean walkthrough, no jokes.

## Scene 7 · The name · 3:27–3:39 · [NAME]

VO: This is called copy-on-write: share every page, and copy one only when someone writes to it. The kernel counts the
lines pointing at each frame, so it knows when to copy and when not to.

SCREEN: The definition in yellow; the refs counts pulse.

## Scene 8 · Count it · 3:39–4:31 · [SHOW] [BREAK]

VO: In the lab, the kernel reports each process's memory. Right after fork, the child shows 512 megabytes shared with
the parent, and 0 of its own. Then it writes one byte in every fourth page. The kernel makes 32,768 copies, 128
megabytes, at about 1.8 microseconds each. Now the child shows 384 shared, and 128 of its own. One trap. RSS, the usual
memory number, counts every page a process has in RAM. It says 513 for each, so adding them claims a gigabyte. They
really use 640. PSS splits each shared page between its sharers, and the two PSS numbers add up to exactly 640. So to
add up memory, add PSS.

SCREEN: "cow.c: 512 MB, drawn as 8 blocks of 64 MB": parent and child bars, all teal, "the same frames", "Shared 512
MB, Private 0". Two blocks per bar turn private (purple for the child, blue for the parent), "Shared 384 MB, Private
128". Lines: "RSS: 513 + 513 = about 1 GB?" (red), "really used: 512 + 128 = 640 MB", "PSS: 320 + 320 = 640 MB" (green);
the rule in yellow.

## Scene 9 · The cost · 4:31–4:55 · [GUARDRAIL] [JOKE:is-the-explanation]

VO: Copy-on-write isn't free, though. When the child wrote to every page, the faults took 180 milliseconds, several
times one big copy. The kitchen agrees: asking the manager 131,072 times takes longer than one trip to the copy shop.
Copy-on-write wins because most children write a little, or start another program and write nothing.

SCREEN: Every block turns private, "Shared 0, Private 512"; "131,072 faults: 180 ms / one big copy: 28 to 33 ms".

## Scene 10 · The moral, and a check · 4:55–5:25 · [MORAL] [PRINCIPLE] [PREDICT] [PAUSE] [LOOP-PAYOFF]

VO: So the moral of the story: fork copies the list, not the memory. Everything is shared until someone writes, and
then only that page is copied. One quick check. A child only reads, like Redis writing its snapshot. How many pages
does the kernel copy? Pause and think.

(three seconds)

None. Reads never fault, so the child can run for minutes without costing a single copy.

SCREEN: The two tables return just after fork (all `read-only`, refs 2). Yellow read dots from every child line;
countdown; "copies: 0" pulses; the moral returns.

---

### Beat check

- Opens with QUESTION (scene 1): faster than copying? Paid off in scenes 6 and 7.
- FAMILIAR (scene 2): the page table from the last lesson. PAIN (scene 3), BREAK of the obvious fix (scene 4), before
  the ANALOGY and MAP (scene 5), which explains why the fix failed and what it lacked.
- SHOW, NAME (page fault), PREDICT with PAUSE (scene 6); NAME copy-on-write (scene 7) after the walkthrough.
- Second BREAK (scene 8): adding RSS. GUARDRAIL (scene 9): the cost when every page is written, and when it wins.
- MORAL and a check (scene 10). Light moments: the cookbook (1:15), the copy shop (4:45).

### Accuracy notes for the producer

- Four pages and frames A to E follow the lesson's stepper; `cow.c` has 131,072 pages.
- The kitchen binder is invented for the video. Its sticker sits on each line of each table (both tables are marked
  read-only), which the narration says when it maps.
- The bars draw 512 MB as eight 64 MB blocks; "every fourth page" becomes two blocks for the picture. In the real run
  the copied pages are spread through the whole range, one in four.
- Numbers are the lesson's lab run: memcpy 33 ms (28 ms on a later run, hence "28 to 33 ms"), fork returned in the
  child after 1.7 ms, 32,768 faults in 58 ms (1.76 µs each, "about 1.8"), Shared 384 / Private 128, Pss 320 for each,
  Rss 513 for each. The parent's PSS after the writes (320) follows from the same split: 384 / 2 + 128.
- "The usual memory number" for RSS: it's the number `ps` and `top` show by default.
- Left to the lesson: file mappings, overcommit and the OOM killer (sections 1 to 3).
