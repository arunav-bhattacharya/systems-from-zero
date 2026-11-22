# How does a log forget? A chain of files called segments

- Slug / scene: `segments-compaction`, `videos/scenes/segments_compaction.py:SegmentsCompaction`
- Lesson: `msg-03`, section 1, "A partition is a chain of files called segments"
- Audience / level: a complete newcomer. Met the log and offsets in The log: Kafka's one big idea; knows nothing about
  files on disk or indexes.
- Length: 4:30 (~700 words of narration, two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=192` (four segments named 0, 104, 208, 312; segment 208 zoomed with its index ticks and the jump
  to 230)
- The learner's real question: a log only grows, so how does it ever delete anything, and how does the broker find
  one record among hundreds of gigabytes?
- Misconception to steelman and break: "keep the log in one big file and cut the oldest part off the front", broken
  by the file system (cutting at the start means copying 1.5 TB every day).
- Concept chain: a log grows 1.8 TB a week → one big file can't be cut at its start → a chain of files, only the
  newest grows (segments, active segment, rolling) → names by base offset find the file → a sparse index finds the
  place inside → when a segment rolls → deleting is whole files only (hardest last)
- Analogy family: the lesson's café notebooks. One notebook at a time, full ones shelved, whole notebooks thrown out
  on Mondays, the inspector's twelve-day-old order.
- Open loops: "how do you delete the front?" planted in scene 1 → scene 3; the owner's weekly rule planted in scene 1
  → the inspector in scene 7, handed on to the next section.
- Assumptions: every number is the lesson's (3,000 payments a second, 1 KB, 3 MB a second, 260 GB a day, 1.8 TB a
  week, 1.5 TB copied; the lab's 400 records of 10,000 bytes in 1 MiB segments: 0, 104, 208, 312, 104 records each
  and 88 in the active one; offset 230 in 208; 1 GiB at 2 GB a second, half a second; an index entry about every
  4,096 bytes; segment.bytes 1 GiB, segment.ms 7 days). The width of the red "oldest 260 GB" band is to scale; the
  16 index ticks and where 230 falls among them are a picture, not measured byte positions.

## The one picture

One row across the top: first the café's notebooks (gold), then one big blue file, then the same space cut into four
segment files, each showing its 20-digit name, its offset range and "closed" or "active", with a band along the
bottom for how full it is (the active one gold). A yellow query chip above the row; under it, a zoom of segment 208
as a strip with teal index ticks. Captions at the bottom.

## Scene 1 · The notebooks, and the question · 0:00–0:37 · [FAMILIAR] [ANALOGY] [QUESTION] [LOOP-PLANT]

VO: Picture a café that writes every order in a notebook. When a notebook fills, the owner shelves it and starts a
new one. Each Monday, she throws out every notebook whose last order is over a week old. Kafka, the program that
keeps logs of records for other programs to read, has the owner's problem. A log only grows. At 3,000 payments a
second, about 1 KB each, that's 3 MB a second. About 260 GB a day, and 1.8 TB a week. How do you delete the front of
something that only grows?

SCREEN: Title card. Four gold notebooks fill one after another; the first pulses red with the Monday rule. They
give way to one long blue file, "one partition of a log: one file", which pulses; the sums as captions; "1.8 TB"
inside the file; "how do you delete the front?".

## Scene 2 · One big file, broken · 0:37–1:15 · [PAIN] [BREAK] [JOKE:amplify]

VO: The simplest idea: keep the log in one big file, and cut the oldest part off the front. Here's the catch. A
file system, the part of the computer that keeps files on disk, can cut a file short at its end for almost nothing.
It can't cut at the start. So to drop the oldest 260 GB from a 1.8 TB file, you'd copy the other 1.5 TB into a new
file. Every day. That's tearing out page one of a notebook by copying every other page into a new notebook. By
hand. Every morning. So deleting has to mean throwing away whole files.

SCREEN: A red band "oldest 260 GB" at the front. A green dashed cut at the end ("almost free"), a red one at the
start ("not possible"). A yellow bar grows underneath: "a new file: copy the other 1.5 TB", then "every day". Caption
"deleting must mean throwing away whole files".

NOTE: The joke restates the cost, then the cash-back line gives the rule.

## Scene 3 · Segments · 1:15–1:49 · [WISH] [MAP] [NAME]

VO: The café already solved this: many notebooks, not one. Only the newest takes new orders. When it's full, it goes
on the shelf, and nobody writes in it again. And throwing out the oldest costs one trip to the bin, however thick the
notebook is. Kafka does the same. Each notebook is a file called a segment. The one taking new records is the active
segment. Closing a full one and opening a new one is called rolling. A closed segment never changes. And deleting old
data means deleting old files, which costs almost nothing.

SCREEN: The big file splits into four files; the newest turns gold and its band grows; the others fill. The first
dims under a cross and comes back. File names fade in, then "active: 88 so far" and "closed: 104 records".
Captions map each part.

## Scene 4 · The lab's segments · 1:49–2:16 · [SHRINK] [NAME]

VO: Here's a small log from the lesson's lab: 400 records of 10 KB each, in segments of 1 MiB, a little more than a
megabyte. About 104 records fit in each. Each segment is named after the offset of its first record, its base offset,
padded with zeros to 20 digits. So: 0, 104, 208, and the active one, 312, holding the last 88.

SCREEN: Captions for the lab; the file names pulse yellow; the ranges 0 to 103, 104 to 207, 208 to 311, 312 to 399
appear one by one.

## Scene 5 · Predict: which file? · 2:16–2:38 · [PREDICT] [PAUSE] [SHOW]

VO: Now a reader asks for offset 230. Which file does the broker open? Pause and guess.

(three seconds)

208. The broker keeps its files sorted by base offset, and picks the largest one at or below 230. 312 is too high.
208 is the one.

SCREEN: Chip "read offset 230"; countdown. Ticks on 0, 104 and 208, a cross on 312; an arrow from the chip to 208.

## Scene 6 · Inside the file: the index · 2:38–3:15 · [PAIN] [SHOW] [NAME]

VO: But a segment can be 1 GiB. Reading it from the start, at 2 GB a second, takes half a second for one lookup. So
next to each .log file sits a .index file. It maps offsets to byte positions in the file, like the index at the back
of a book. It's sparse: an entry about every 4,096 bytes, not one per record, so it's small enough to keep in
memory. The broker looks up 230 in the index, jumps to the nearest entry at or below it, and reads forward a few
kilobytes. A third file, the time index, does the same for times.

SCREEN: Dashed zoom lines open segment 208 into a wide strip; a red line sweeps it slowly ("half a second"). Teal
ticks appear along it, ".index: an entry about every 4,096 bytes". A yellow arrow drops on one tick, a short yellow
bar reads forward to a mark "230". Caption ".timeindex: the same, for times".

## Scene 7 · When it rolls, and the catch · 3:15–3:52 · [GUARDRAIL] [LOOP-PAYOFF]

VO: Two settings decide when the active segment rolls. segment.bytes, 1 GiB by default: roll before the file grows
past it. segment.ms, 7 days: roll if the segment is older than that when a new record arrives. And the catch.
Deleting means whole files only. Remember the owner who keeps orders for a week? A notebook that also holds last
Thursday's orders stays on the shelf. So an inspector can find a twelve-day-old order there, and the rule wasn't
broken. Kafka keeps records the same way: often longer than you asked. The next section shows it.

SCREEN: Chips "segment.bytes: 1 GiB (default)" and "segment.ms: 7 days (default)". The files turn gold as notebooks
again; the first pulses ("one old order and last Thursday's: the notebook stays"); "a twelve-day-old order, rule
not broken"; back to blue: "records live at least as long as you asked, often longer".

## Scene 8 · Moral and check · 3:52–4:30 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So: one log, cut into files. New records go only into the active one, closed ones never change, and deleting old
data means throwing away whole files. The file names find the right file, and a small index finds the place inside
it.

One quick check. A reader asks for offset 103. Which file does the broker open? Pause and think.

(three seconds)

The one named 0. The next file starts at 104, one record later, so 103 is the last record of the first file.

SCREEN: The active file and the closed ones pulse with the recap captions; the names pulse. Chip "read offset 103";
countdown; arrow to file 0; 104 flashes red, 0 to 103 yellow: "103: the last record of file 0".

---

### Beat check

- Opens from the familiar notebooks and a QUESTION with real sums (scene 1).
- BREAK of the obvious design (scene 2) before the mechanism; the analogy carries the fix (scene 3), MAP said out
  loud.
- PREDICT with PAUSE (scene 5, and the check in scene 8), SHOW right after.
- NAME after the picture: segment, active segment, rolling (scene 3), base offset (scene 4), .index, sparse (scene 6).
- GUARDRAIL (scene 7: roll settings, and whole files only so records outlive their limit) and MORAL (scene 8) last.
  Light moment: copying every other page by hand (1:05).

### Accuracy notes for the producer

- Numbers are the lesson's section 1 and its Try it output (segments 00000000000000000000.log, ...104.log, ...208.log,
  ...312.log; 104 records in each closed one, 88 in the active one; earliest offset 0, latest 400).
- Not every lab record is 10 KB on disk: each went in a batch of its own of about 10,072 bytes, which is why 104 fit
  in 1 MiB. The video says "about 104 records fit in each".
- The index picture is schematic: 16 ticks and the position of 230 are not real byte positions. In the lab's large
  records, nearly every record gets an index entry; with ordinary small records, an entry covers several.
- "Roll before the file grows past it" stands for the lesson's "the next batch would make the file bigger than
  this". segment.ms rolls only when a new record arrives, as the video says.
- The inspector's twelve-day-old order and "records live at least as long as you asked" are the lesson's opening and
  closing; how retention picks segments is section 2.
- Kafka 4.0's 1 MiB minimum for segment.bytes is left to the lesson. No code on screen: the section has none.
- Pronunciation: `SAY` rules for GiB, MiB, segment dot bytes, segment dot M S, dot log, dot index and 4,096.
