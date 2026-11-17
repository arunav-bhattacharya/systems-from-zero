# A desk with four places: the database's own page cache

- Slug / scene: `buffer-pool`, `videos/scenes/buffer_pool.py:BufferPool`
- Lesson: `store-03`, section 0, "Keeping busy pages in memory: the buffer pool"
- Audience / level: a complete newcomer who has met the previous lesson: a table is a file of 8 KB pages, and a
  database reads a whole page to get one row. Knows nothing about caches.
- Length: 4:45 (~760 words of narration at the Kokoro voice's ~175 words a minute, plus two guesses, a check and
  silent moves)
- Poster: `POSTER=156` (page 42 in frame 3, the full page table, "which page should leave?")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: every query reads pages, and the drive is slow. Why not keep the pages in memory?
  And what happens when memory is full?
- Misconception to steelman and break: "keep every page you read in a map in memory". Broken by size: a 2 TB table
  and 64 GB of memory. Second, softer one: "let the operating system cache it" (the database knows three things
  the kernel doesn't; mmap was 2 to 20 times slower).
- Concept chain: pages are read again and again → memory is over a hundred times faster than the drive → a cache
  in memory → it needs a fixed size → frames and a page table, hits and misses → when full, a victim must leave →
  PostgreSQL's pool (shared_buffers) and the Try it's reads turning into hits → why the database keeps its own
- Analogy family: the lesson's study desk. Four open books on a small desk, the rest on a shelf across the room; a
  glance takes a second, a walk takes a minute; a fifth book means one has to go back.
- Open loops: "which book goes back?" planted in scene 1 → named as the victim in scene 5 and handed to the rest of
  the lesson; "is a read always a trip to the drive?" raised in scene 6 by the 0.15 ms → answered in the same scene.
- Assumptions: the toy pool and its pages (10, 11, 12, 13, then 42) are the lesson's figure. Which page leaves for
  42 is shown as a choice made "for now"; the lesson's later sections decide it. Every other number is the
  lesson's: about 100 µs per NVMe read, well under 1 µs from RAM, 2 TB vs 64 GB, 128 MB = 16,384 frames, 1,280
  pages read then hit, 0.15 ms, 2 to 20 times slower.

## The one picture

Left: the drive, a gold column of page tiles (0, 1, 2 ... 10, 11, 12, 13 ... 42 ...), titled "the drive (the
shelf)". Middle top: four frames in a row inside a blue outline, "memory (the desk)", each holding at most one page
tile. Below them: the page table, a teal box with one line per frame ("page 10 → frame 0"). Right: the request chip
(yellow) and its result: green for a hit, red for a miss. Captions on one line at the bottom; number lines in the
band above them.

## Scene 1 · Every query reads pages · 0:00–0:35 · [FAMILIAR] [QUESTION] [LOOP-PLANT]

VO: Every question a program asks a database reads pages. Looking up one payment reads a few. A monthly report reads
thousands. Reading one 8 KB page from a fast SSD takes about 100 microseconds. From memory, it takes well under one.
And queries keep coming back to the same pages: today's payments, the table of card limits. So keep copies in memory.
But memory is small. Which pages stay, and what happens when it's full?

SCREEN: The drive column draws in. Two lines: "from the drive: about 100 µs", "from memory: well under 1 µs". Captions
carry the question.

## Scene 2 · The desk · 0:35–1:20 · [ANALOGY] [MAP] [JOKE:pivot]

VO: Picture yourself studying at a small desk. It holds four open books, and the rest sit on a shelf across the
room. A glance at the desk takes a second. A walk to the shelf takes a minute. So you keep the books you're using on
the desk. And when you need a fifth book, one has to go back. Which one? Hold that thought.

Let's map it. The shelf is the drive. The desk is memory. And each book is a page.

The picture breaks in one small way. A desk takes books of every size. In memory, every place holds exactly one 8 KB
page, so any page fits in any place.

SCREEN: The four places draw in as an outlined desk. Titles gain "(the shelf)" and "(the desk)". Captions map each
part. The places pulse when "exactly one 8 KB page" is said.

## Scene 3 · Keep everything you read · 1:20–1:50 · [BREAK] [WISH] [JOKE:amplify]

VO: The first idea: a map in memory from each page number to that page's bytes, filled on every read. It works,
until the database is bigger than memory, and most are. A 2 TB table won't fit in a server's 64 GB of memory. That
desk would need to be the size of the library.

So the cache needs a fixed size. And once it's full, something has to leave.

SCREEN: Pages pile into the desk area and overflow; a line "a 2 TB table, 64 GB of memory" in red. Then the overflow
fades and the four places return: "a fixed size".

## Scene 4 · Four places and a list · 1:50–2:45 · [SHRINK] [SHOW] [NAME]

VO: So, four places on the desk, and a list of which page sits in which place. A query wants page 10. The list
doesn't have it. So we walk to the shelf, read page 10 into place 0, and write it on the list. Pages 11, 12 and 13
fill the other places the same way.

Now page 11 again. The list says place 1. No walk at all.

These have names. The places are frames, each the size of one page. The list is the page table. Found on the list
is a hit, and no input or output happens, no trip to the drive. Not found is a miss. The whole thing is the buffer
pool.

SCREEN: Request "read page 10"; a gold tile travels from the drive to frame 0, "about 100 µs"; the page table gains
"page 10 → frame 0". Three quick misses fill frames 1 to 3. "read page 11": the table's line glows, frame 1 glows
green, "hit: no trip to the drive". Then labels: "frames", "page table", "hit", "miss", and the desk's title becomes
"the buffer pool".

## Scene 5 · The fifth book · 2:45–3:20 · [PREDICT] [PAUSE] [SHOW] [LOOP-PAYOFF]

VO: Now a query wants page 42. Every frame is full. What has to happen first? Pause and guess.

(three seconds)

A page has to leave. The pool picks a victim, a page to throw out, or evict. Say, for now, page 13. Then page 42 is
read into its frame, and the list is updated. Which page should be the victim? That's the fifth book from the desk,
and the rest of this lesson.

SCREEN: "read page 42" in red: a miss. Countdown. Page 13's tile in frame 3 turns red and leaves; a gold tile 42
travels in; the table line becomes "page 42 → frame 3". Caption "which page leaves? the rest of this lesson".

## Scene 6 · PostgreSQL's pool, and a guess · 3:20–4:15 · [SHOW] [PREDICT] [PAUSE]

VO: PostgreSQL, a free database many companies run, calls its pool shared_buffers. By default it's 128 megabytes:
16,384 frames of 8 KB, shared by every program connected to it.

In the Try it, a table of 200,000 payments takes 1,280 pages. We throw them out of the pool and count the rows. The
first run reads all 1,280 pages. Run the same count again. What will it say? Pause and guess.

(three seconds)

1,280 hits, and no reads at all. One more honest detail: those first 1,280 reads took 0.15 milliseconds in all. The
operating system kept its own copy of the pages in memory, so the SSD was never touched.

SCREEN: Number lines: "shared_buffers: 128 MB = 16,384 frames of 8 KB". Then "first run: shared read=1280" (red);
countdown; "second run: shared hit=1280" (green). Then "1,280 reads in 0.15 ms: the kernel's copy, not the SSD".

## Scene 7 · Why not let the kernel do it? · 4:15–4:55 · [GUARDRAIL] [JOKE:soften]

VO: So why not let the operating system cache everything? Some systems do. But the database knows three things the
kernel doesn't. Which pages a query is using right now. That a changed page must not reach the drive before the log
record that describes it. And that a big scan's pages won't be read again. A 2022 study measured databases that leave
these choices to the kernel through mmap. Once memory filled up, they were 2 to 20 times slower. The kernel means
well. It just can't see inside a query.

SCREEN: Three lines, one per thing the database knows. Then "mmap: 2 to 20 times slower once memory filled up
(Crotty, Leis and Pavlo, 2022)".

## Scene 8 · The moral, and a check · 4:55–5:30 · [MORAL] [PREDICT] [PAUSE]

VO: So: keep a fixed number of page-sized frames in memory, and a page table that says which page is in which frame.
A hit costs nothing. A miss costs a trip to the drive, and maybe a victim.

One quick check. The frames now hold pages 10, 11, 12 and 42. A query reads page 11, then page 13. Which read is a
miss? Pause and think.

(three seconds)

Page 13. It was the victim, so it's back on the shelf. Page 11 is a hit.

SCREEN: Moral caption. Two requests; countdown; page 11's line glows green (hit), page 13 has no line: red "miss".

---

### Beat check

- FAMILIAR (pages from the last lesson) and QUESTION first (scene 1), with the real cost.
- ANALOGY + MAP said out loud, with its breaking point (scene 2), before any name.
- BREAK of "keep everything" (scene 3), then the WISH for a fixed size.
- NAME after the mechanism is seen (scene 4).
- PREDICT with PAUSE (scenes 5 and 6, and the check in scene 8); SHOW right after.
- GUARDRAIL: why the database keeps its own cache, and what the measured reads really were (scenes 6 and 7). MORAL last.
- Light moments: the desk the size of the library (~1:45), the fifth book (~3:15), the kernel means well (~4:50).

### Accuracy notes for the producer

- All numbers are the lesson's: about 100 µs per 8 KB read from an NVMe SSD; well under 1 µs from RAM; 2 TB and 64
  GB; `shared_buffers` 128 MB by default = 16,384 frames of 8 KB; the Try it's 200,000 rows in 1,280 pages, `shared
  read=1280` then `shared hit=1280`, and 0.151 ms of I/O timing because the pages were in the Linux page cache inside
  Docker's Linux machine; mmap 2 to 20 times slower than direct I/O once memory filled up (Crotty, Leis and Pavlo,
  2022).
- The four-frame pool with pages 10 to 13 is the lesson's figure. Page 13 as the victim is a placeholder; sections 1
  to 3 (pins, dirty pages, the clock sweep, the ring buffer) decide the real choice. The frame bookkeeping (pin
  count, dirty flag, usage count) is left to those sections.
- check_audio: 97.8% at -16.1 LUFS; the differences are Whisper spellings (kilobytes for KB, postgres, m map, "triate"
  for "Try it") and one sentence it dropped in the long pass but hears clearly on its own.
- "Shared by every program connected to it": PostgreSQL starts one backend process per connection, and every backend
  uses the same pool (the lesson's wording).
