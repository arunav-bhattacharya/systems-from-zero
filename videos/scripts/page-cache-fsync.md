# Done, but not on the disk: the page cache and writeback

- Slug / scene: `page-cache-fsync`, `videos/scenes/page_cache_fsync.py:PageCacheFsync`
- Lesson: `os-09`, section 1, "Writeback: a write lands in RAM, and the disk gets it later"
- Audience / level: a complete newcomer. Knows a program saves data to files; has never heard of the page cache,
  dirty pages or fsync.
- Length: 4:50 (~810 words of narration at Kokoro's ~175 words a minute, plus three pauses and builds)
- Poster: `POSTER=192.6` (record 1 written back by age, record 2 forced with fsync in about 3 ms, the power-cut line)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: the write said it worked, and reading the file showed the record. How can it be gone
  after a power cut?
- Misconception to steelman and break: (1) "a write that succeeded is on the disk", broken by dd's 64 MB of dirty data
  and by record 3 in the power cut; (2) "a crash loses unsaved data", broken by kill -9 losing nothing.
- Concept chain: write returns in microseconds and reads see it → the bytes are in the page cache, dirty → writeback
  sends them later (age, 10 %, 20 %, fsync) → fsync waits for the disk → a power cut loses what is still dirty, a crash
  doesn't (hardest last)
- Analogy family: the lesson's post office. The clerk says done and drops your letter in the outgoing tray; a van
  empties the tray now and then; anyone asking for your letter gets it from the tray. The break: a tray survives a
  power cut, and RAM doesn't.
- Open loops: "where did the café's payment go?" planted in scene 1 → answered in scene 8; "when does it reach the
  disk?" predicted in scene 2 → shown at once.
- Assumptions: numbers are the lesson's (dd 64 MB, `file_dirty 67108864`, 30 to 34 s, 30 s expiry, 5 s wake-ups,
  10 % and 20 %, fsync about 3 ms in the stepper). The three records and their times (t = 0, 30, 31, 32 s) are the
  lesson's stepper. The card 8802 line in the hook's log file is invented for the picture.

## The one picture

Three tall boxes in a row: the payments program (teal, left) with the call it is making and what came back; the page
cache in RAM (gold, middle) with pages 0 to 2, each "dirty" (gold), "clean" (green), "empty" or "lost" (red); the disk
(blue, right) with blocks 0 to 2. Grey arrows carry writes from the program into the cache. A small teal van (later
"flusher") parks between the cache and the disk and carries a page across. A clock sits above the program. Under the
cache, a dirty-data gauge (with 10 % and 20 % marks) appears for the triggers; below it, a line says what a power cut
would leave right now.

## Scene 1 · The power cut · 0:00–0:22 · [QUESTION] [LOOP-PLANT]

VO: Picture a power cut on the café's street, two seconds after a customer taps their card. The card reader had
already beeped. The payments program had written the payment to its log file, and said approved. When the power comes
back, the payment isn't in the file. Every step had said it worked. So where did the payment go?

SCREEN: Title card. A card reader with a green tick, "approved"; a log file gains a yellow line; the screen goes dark
for a moment; the line is gone, "(not there)"; a yellow "?".

## Scene 2 · Watch a write · 0:22–1:05 · [FAMILIAR] [SHOW] [PREDICT] [PAUSE]

VO: Let's watch a write. A program adds a record to a file with a call named write. It returns success in
microseconds. And any program that reads the file straight after sees the new record. So far, it looks like it's on
the disk. Here's a bigger test from the lab. A command called dd writes 64 megabytes to a file, in a fraction of a
second. Right after, the kernel's own count says: 64 megabytes of that file are in RAM, and not on the disk. So when
does it reach the disk? Pause and guess.

(three seconds)

About 30 seconds later, when nothing else was going on. Until then, the newest data was only in RAM.

SCREEN: The program and the disk ("nothing yet"); `write(rec 1)`, "returned at once", "read: gets rec 1". Captions
"dd: 64 MB written...", `memory.stat: file_dirty 67108864`; the page cache appears, all pages dirty, "t = 0 s".
Countdown. The clock runs to 30 s; the van carries each page across; pages turn clean, blocks "on disk"; "64 MB waited
30 to 34 seconds".

## Scene 3 · What write really does · 1:05–1:27 · [NAME] [PAIN]

VO: Here's what write really does. It copies your bytes into the page cache, the kernel's copy of file pages in RAM. It
marks each page dirty, meaning newer than the disk. And it returns. Why not wait for the disk each time? Then every
small write would pay for a trip to the device. And a page rewritten a hundred times in a second can go to the disk
once.

SCREEN: Reset. A dot carries rec 1 into page 0, "dirty", "returned at once". Captions for the reason; five quick dots
into the same page.

## Scene 4 · The post office · 1:27–2:03 · [ANALOGY] [MAP] [NAME] [JOKE:is-the-explanation]

VO: A post office works the same way. You hand the clerk a letter. The clerk says done, and drops it in the outgoing
tray. Now and then, a van empties the tray. And anyone who asks for your letter before the van comes gets it straight
from the tray. So the clerk wasn't lying. Your letter really is in the building. It just hasn't left yet. Let's map it. The clerk saying done is write returning. The tray is the page cache. A letter in the tray
is a dirty page. And the van is called writeback: kernel threads, called flushers, that write dirty pages to the disk
later.

SCREEN: The cache's title becomes "the outgoing tray"; "returned at once" pulses; the van glows; a green dot comes back
out of the tray for a read. Caption "the clerk wasn't lying: the letter is in the building, it just hasn't left
yet" while "dirty" pulses. Mapping: the title returns to "page cache (RAM)", "dirty" pulses, the van becomes
"flusher", caption names writeback.

## Scene 5 · What sends the van · 2:03–2:34 · [SHOW]

VO: Four things send the van. First, age. A page that has been dirty for 30 seconds goes at the flusher's next wake-up,
every 5 seconds by default. Second, a full tray. When dirty data passes 10 percent of the memory it could use, the
flusher starts early. Third, an overflowing tray. Past 20 percent, a program that writes more is made to wait, and help.
That's when write suddenly gets slow. And fourth, the program asks, with a call named fsync.

SCREEN: Numbered captions. The clock reaches 30 s and the van takes page 0. A gauge fills past the teal 10 % mark and
the van leaves early; it fills past the red 20 % mark and the program box turns red, "made to wait"; `fsync(fd)`.

## Scene 6 · Three records · 2:34–3:17 · [SHOW]

VO: Let's follow the log file. Record 1 is a payment. write copies it into page 0, marks it dirty, and returns. If the
power went out now, record 1 would be lost. 30 seconds later, the flusher wakes. Page 0 has been dirty long enough, so
it goes to the disk, and the page is clean. Record 2 is a refund the program must not lose. write returns just as fast.
So before it says approved, the program calls fsync. The kernel writes the page, tells the disk to save it, and
returns only when the disk confirms. Milliseconds instead of microseconds, and record 2 is safe. Record 3 is written,
and not forced. It sits in the cache, dirty.

SCREEN: The lesson's stepper: t = 0, 30, 31, 32 s; `write(rec 1)` dirty, then clean and on disk; `write(rec 2)`,
`fsync(fd)` "waiting for the disk", a gold dot to the disk and a green one back, "returned in about 3 ms"; `write(rec
3)` dirty. The power-cut line under the boxes updates at each step (red lost, green survives).

NOTE: Clean walkthrough, no jokes.

## Scene 7 · Two accidents · 3:17–3:52 · [PREDICT] [PAUSE] [BREAK]

VO: Now, two different accidents. In one, the program crashes, killed on the spot. In the other, the power goes out.
Which one loses record 3? Pause and guess.

(three seconds)

Only the power cut. The dirty pages belong to the kernel, not the program. So after a crash, the flusher still writes
record 3 to the disk. A power cut wipes RAM, and record 3 goes with it, although its write said success. Here's where
the post office picture breaks. A tray of letters survives a power cut. RAM doesn't.

SCREEN: Countdown. The program box turns red, "(killed)"; the van carries page 2 to the disk anyway. Rewind: page 2
dirty again; the screen goes dark; every page "lost", "(gone)"; block 2 still "nothing yet" pulses.

## Scene 8 · The rule, and the café · 3:52–4:18 · [GUARDRAIL] [LOOP-PAYOFF]

VO: So is half a minute in RAM a problem? For most files, no. For a payment that was just approved, yes. If you'll tell
someone it's saved, call fsync first. It costs milliseconds each time, and the next part of the lesson shows how to
share that cost. And the café's payment? It was approved two seconds before the power cut, still dirty in RAM. One
fsync before saying approved would have saved it.

SCREEN: Captions; block 1 (forced with fsync) pulses green; page 2 (lost) pulses red.

## Scene 9 · The moral, and a check · 4:18–4:50 · [MORAL] [PRINCIPLE] [PREDICT] [PAUSE]

VO: So the moral of the story: write returns when the kernel has your bytes. fsync returns when the disk has them. One
quick check. The program writes record 4 into page 0, and is killed a second later. The power stays on. Is record 4 on
the disk a minute later? Pause and think.

(three seconds)

Yes. The kernel still holds the dirty page, and the flusher writes it about 30 seconds after the write.

SCREEN: The moral in yellow; the cache and then the disk glow. Record 4 into page 0, dirty; the program is killed;
countdown; the clock jumps to 71 s and the van carries page 0 to the disk.

---

### Beat check

- Opens with QUESTION (scene 1), from the lesson's power cut. FAMILIAR (a write, a read) before any term.
- PREDICT with PAUSE three times (scenes 2, 7, 9); SHOW right after each.
- NAME after the SHOW: page cache and dirty (scene 3), writeback and flusher (scene 4).
- ANALOGY and MAP (scene 4) said out loud; its break said in scene 7.
- BREAK: "succeeded means on disk" (scenes 2 and 7); "a crash loses data" (scene 7).
- GUARDRAIL (scene 8), MORAL and check (scene 9). Light moments: the clerk wasn't lying, the letter just hasn't left
  (1:45), which is what write's success means; the tray that survives a power cut while RAM doesn't (3:45), kept as an
  understatement.

### Accuracy notes for the producer

- dd: 64 MB to a file in /tmp "in a fraction of a second"; `memory.stat` showed `file_dirty 67108864`. In the lesson's
  runs it waited 30 to 34 s when nothing else happened, and 0.2 to 20 s when another container called sync or pushed
  the machine past its background line. The video shows the quiet case.
- The flusher wakes every 5 s by default (`vm.dirty_writeback_centisecs` 500); the lab box's VM uses 15 s. Expiry is
  `vm.dirty_expire_centisecs` 3000. The 10 % and 20 % are `vm.dirty_background_ratio` and `vm.dirty_ratio`, of the
  memory the kernel could use for dirty data.
- The fsync time ("about 3 ms") is the stepper's; the lesson measured 2 to 9 ms a call in the lab VM. Real fsync also
  writes the file's metadata and flushes the device's own cache (section 2 of the lesson).
- The check's 71 s: written at 41 s, dirty for 30 s; with 5 s wake-ups it would go at the next wake-up after 71 s.
- The log line "pay 8802 9.00" in the hook is invented for the picture. Group commit and replacing files safely are
  left to the lesson's later sections.
