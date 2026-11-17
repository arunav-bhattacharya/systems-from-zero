# Same address, different rooms: virtual addresses and the page table

- Slug / scene: `page-fault`, `videos/scenes/page_fault.py:PageFault`
- Lesson: `os-06`, section 0, "Every program gets its own addresses, and a page table maps them to RAM"
- Audience / level: a complete newcomer. Knows a program runs in memory; has never heard of addresses, pages or
  hexadecimal.
- Length: 5:28 (~860 words of narration; Kokoro speaks about 175 words a minute, plus two pauses and builds)
- Poster: `POSTER=268` (the four-level walk for 0xffff42401234 ending at byte 0x234 in frame 2)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: two programs can keep data at the same address and each read back its own. How can
  one address hold two things?
- Misconception to steelman and break: (1) "a program's addresses are places in RAM", broken three ways, then base
  and limit broken by one unbroken slice; (2) "the page table is one long list", priced at 512 GB per program.
- Concept chain: an address is a byte's number → real addresses collide, leak and can't grow → base and limit need
  one unbroken slice → pages and frames, any page in any frame, one page table per program (virtual addresses) →
  the offset is the last three hex digits → a flat table is 512 GB, so the table is a four-level tree (hardest last)
- Analogy family: the lesson's hotel with tour groups. Each group's letter says rooms 1 to 40; the front desk keeps a
  list per group saying which real room each number means; a binder with tabs for the tree; the desk looks a room up
  once, the hardware on every access.
- Open loops: "how can one address hold two things?" planted in scene 1 → answered in scene 5; "four lookups on every
  access" left open in scene 9 → the lesson's next section (the TLB).
- Assumptions: 0x1234 is a toy address for the puzzle (two programs, page 1, frames 2 and 6); 0xffff42401234 and its
  fields (511, 509, 18, 1, byte 0x234) are the lesson's figure. The page tables and frame numbers are invented for the
  picture; eight frames are drawn for 8 GB of RAM. The second program is "another program".

## The one picture

Right: RAM, a column of eight frames (frame 0 on top). Left: two program cards, the payments program (blue) above and
another program (purple) below, each holding its page table (three lines, "page 1: frame 2"). Arrows in each
program's colour run from a line of its table to a frame. In the naive scenes, coloured blocks over the RAM column are
the programs' slices (grey for the kernel). For the tree, the cards make room for the address split into five
coloured fields and four small tables (teal root, gold level 1, green level 2, purple level 3) whose highlighted
entries chain to a frame. The caption sits at the bottom. At most six things on screen.

## Scene 1 · The puzzle · 0:00–0:32 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: A computer's memory, its RAM, is one long row of bytes. Each byte has a number, its address, and programs read and
write memory by address. Addresses are written in hexadecimal, base 16, with the digits 0 to 9 and then a to f.

Now, something odd. Two programs on the same computer can each keep data at the very same address, 0x1234. And each
one reads back its own. How can one address hold two different things?

SCREEN: Title card. The RAM column draws in. Two program cards, each with "0x1234" and its own value ("balance: 9",
"count: 300"). A yellow "?".

## Scene 2 · Real addresses · 0:32–0:57 · [PAIN] [BREAK]

VO: The simplest idea: give each program a slice of the 8 gigabytes, and let its addresses be real RAM addresses. It
breaks three ways. Two programs built to use the same addresses can't both run. A bad pointer, an address that points
to the wrong place, can overwrite another program's memory, or the kernel's. And a program can't grow, if a neighbour
sits right after it.

SCREEN: "RAM, 8 GB". Slices: payments (blue, top), another (purple), the kernel (grey, bottom). "both want this" in
red over the top; a red arrow from the payments card into the purple slice, then into the kernel; a dashed growth
block that runs into the neighbour. Captions number the three breaks.

## Scene 3 · Base and limit · 0:57–1:33 · [PAIN] [WISH]

VO: Next try: a base and a limit. The hardware adds the base to every address, and refuses any address past the
limit. Now every program can start at 0, and none can reach outside its slice. But the slice must be one unbroken run
of RAM. A JVM, the program that runs Java code, may grow its heap to 4 gigabytes. So it grabs one huge chunk up front.
And free memory breaks into gaps, too small to use. Wouldn't it be nice if a program's memory could sit in any free
scraps of RAM, and still look like one neat run to the program?

SCREEN: "base" and "limit" marks on the blue slice; "addresses from 0" on both cards. "a JVM wants 4 GB in one piece"
(gold). Two dashed green gaps, "free, in pieces". The wish in yellow.

## Scene 4 · The hotel · 1:33–2:05 · [ANALOGY] [MAP]

VO: A hotel solves this every week, for tour groups. Each group's letter says rooms 1 to 40. The front desk keeps a
list for each group, saying which real room each number means. So two groups' room 12 are different rooms. And no
guest can walk into another group's room, because their group's list doesn't contain it.

Let's map it. Each tour group is a program. The room numbers on its letter are its addresses. The real rooms are RAM.
And the desk's list is a table the hardware reads, on every single read and write.

SCREEN: The RAM column becomes "the hotel's real rooms" (room 100 to 107); the cards become "tour group A" and "tour
group B", each with "letter: rooms 1 to 40" and a desk list ("room 12: 102" for A, "room 12: 106" for B). Arrows from
both groups' room 12 to two different real rooms; B's list pulses. Mapping pulses on each part.

## Scene 5 · Pages, frames and the page table · 2:05–2:54 · [NAME] [SHOW] [LOOP-PAYOFF]

VO: In the computer, the rooms are pieces of RAM of one fixed size, called frames. A program's addresses are cut into
pieces of the same size, called pages. 4 kilobytes in the lab box, and 16 on an Apple Silicon Mac. Each program has a
page table, which says which frame holds each of its pages. Any page can live in any frame. So a 1 gigabyte heap needs
no unbroken gigabyte. And a program can't touch another's memory, because the other's frames aren't in its table.
These addresses are called virtual. Every program has its own set, and the hardware translates them into real places
in RAM. So, the puzzle. Both programs use address 0x1234, which is in page 1. But their tables send page 1 to
different frames.

SCREEN: Room labels become "frame 0" to "frame 7"; the desk lists become page tables ("page 0: frame 5", "page 1:
frame 2", "page 2: frame 7" and "page 0: frame 1", "page 1: frame 6", "page 2: frame 3"). Six arrows grow into
scattered frames. The other program's arrows dim while blue dots run; then all dots run. Page 1 lines pulse; dots land
in frames 2 and 6.

## Scene 6 · Page number and offset · 2:54–3:19 · [SHRINK] [SHOW]

VO: How does the hardware find the page? It splits the address in two. With 4 kilobyte pages, the last three
hexadecimal digits are the offset, the position inside the page. Each digit is 4 bits, so that's 12 bits, and 2 to
the 12 is 4,096: one page. The rest is the page number. So 0x1234 is byte 0x234 of page 1.

SCREEN: "0x1" (purple, "page number") and "234" (yellow, "offset: the byte inside the page") at the top. Caption with
the bits.

## Scene 7 · How big is the table? · 3:19–3:55 · [PREDICT] [PAUSE] [BREAK] [JOKE:is-the-explanation]

VO: Real addresses are longer, like this one from the lab box. So how big is a page table, if it's a plain list with
one line for every possible page? The lab box gives each program 48-bit addresses, 256 terabytes in all. That's 2 to
the 36 pages, and each line takes 8 bytes. More or less than the machine's 8 gigabytes? Pause and guess.

(three seconds)

512 gigabytes. For every program. The hotel's guest list would be 64 times bigger than the hotel.

SCREEN: "0xffff42401234". The other program and the arrows fade; a tall list "page 0: ...", "a line for every page".
Captions with the arithmetic; countdown; "512 GB, for every program" in red; the list wiggles.

NOTE: The guest list bigger than the hotel is the light moment, and it is the arithmetic (512 GB over 8 GB).

## Scene 8 · The tree · 3:55–4:37 · [SHOW] [NAME]

VO: So the table is a tree. The 36 bits of page number split into four groups of 9. Each group picks one of 512 entries
in one small table. And 512 entries of 8 bytes fill exactly one page. The root's entry points to a level 1 table. Its
entry points to level 2, then level 3, whose entry holds the frame number. Then the offset picks the byte, inside that
frame. At the hotel, it's a binder with tabs. The first part of the room number picks a tab, the next picks a page
behind it, and so on. Tables exist only under addresses a program uses. So a small program needs just a few dozen
kilobytes of them.

SCREEN: The address becomes five fields: 511, 509, 18, 1 (9 bits each) and 0x234 (12 bits). Four tables (root, level
1, level 2, level 3, "512 entries"), dashed lines from each field down to its table, highlighted entries chained by
arrows, the last into frame 2; a yellow dot "byte 0x234". The tables pulse in turn for the binder.

## Scene 9 · Where the hotel stops · 4:37–4:54 · [GUARDRAIL] [LOOP-PLANT]

VO: Here's where the hotel picture stops working. A desk looks a room up once, when you check in. The hardware walks
this tree on every single read and write. Four lookups in memory, every time. That sounds slow, and it would be. Next
in the lesson, the shortcut that makes it cheap.

SCREEN: A yellow dot walks the chain; the four entries flash red.

## Scene 10 · The moral, and a check · 4:54–5:28 · [MORAL] [PRINCIPLE] [PREDICT] [PAUSE]

VO: So the moral of the story: an address is a room number on your own group's letter. The page table says which real
room it means. One quick check. The payments program keeps its balance in frame 5. Another program's table has no line
for frame 5. Can that program read the balance? Pause and think.

(three seconds)

No. Its addresses can only reach frames in its own table. If the room isn't on your group's list, no address leads
there.

SCREEN: The tree clears; both cards and their tables come back with all six arrows. Frame 5 and "page 0: frame 5"
pulse; the other program's lines pulse; countdown; a red cross by frame 5; purple dots run only to frames 1, 6 and 3.

---

### Beat check

- Opens with QUESTION (scene 1), from a puzzle the viewer can see; FAMILIAR (bytes and addresses) first.
- PAIN and BREAK (scenes 2 and 3), then WISH, before the ANALOGY and MAP (scene 4).
- NAME after the picture: frames, pages, page table, virtual (scene 5); offset (scene 6); tree levels (scene 8).
- PREDICT with PAUSE twice (scene 7, scene 10); the flat-list model broken by its own arithmetic (scene 7).
- GUARDRAIL (scene 9): where the hotel stops, and the cost it leaves open. MORAL and a check (scene 10).
- Light moments: the guest list 64 times bigger than the hotel (3:50); the analogy's own break (4:40).

### Accuracy notes for the producer

- 0x1234 is a toy address; Linux doesn't map the lowest 64 KB of a process, and real addresses look like the lab's
  `aaaac13d0000` or `fffff8183000`. Two processes do share addresses for real after `fork` (the next lesson).
- The tables, frame numbers and the second program are invented for the picture. A real machine with 8 GB has about
  two million 4 KB frames; eight are drawn.
- 48-bit addresses: 2^48 bytes = 256 TB; 2^36 pages × 8 bytes = 512 GB, 64 times 8 GB. "About 69 billion" is 2^36
  rounded.
- The walk for 0xffff42401234 (fields 511, 509, 18, 1, offset 0x234) is the lesson's figure; frame 2 as its target is
  invented.
- Left to the lesson: /proc/self/maps and its regions, the TLB (next section), page faults on first touch, and VSZ vs
  RSS from the lesson's opening.
