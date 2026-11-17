# The row moved, so why does the index still find it? A drawer with a list taped inside

- Slug / scene: `slotted-pages`, `videos/scenes/slotted_pages.py:SlottedPages`
- Lesson: `store-02`, section 1, "Rows of different sizes in one page: the slotted page"
- Audience / level: a complete newcomer who has met section 0: a table file is cut into 8 KB pages, a page is read
  whole, and an index stores where a row is so it can find it again. Knows nothing about page layouts.
- Length: 5:02 (~770 words of narration; the voice runs about 165 words a minute here because of the many numbers,
  plus a guess, a check and silent moves)
- Poster: `POSTER=226` (D in slot 3, the full slot table, the index arrow to slot 2 in green)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: rows have different sizes and get deleted. How do we place them in a page and still
  find one quickly later, when the page has been rearranged?
- Misconception to steelman and break: "an index can note a row's byte offset". Broken by packing rows from the
  front: delete B, slide C down to close the gap, and byte 500 is now the middle of C.
- Concept chain: rows packed from the front need a walk, and break offsets when they move → a numbered list at the
  front makes a lookup one step, but its size is fixed → slots and rows grow toward each other (lower and upper) →
  an index stores page and slot → delete marks the slot, tidying moves the bytes, the slot stays → slots and rows
  share the space, and dead slots aren't handed out again → names and PostgreSQL's real page (652 and 656) → the
  cost and the promise
- Analogy family: the lesson's filing drawer. A numbered list taped inside the front says where each folder sits;
  push the folders together and correct the list, but line 2 is still line 2.
- Open loops: "how does the index still find C?" planted in scene 1 → paid off in scene 6; the taped list planted
  in scene 4 → broken in scene 7 (on a page, the list takes room from the rows).
- Assumptions: the page is the lesson's stepper exactly (the lab's 4 KB page with a 4-byte header; A 300, B 200, C
  400, D 250 bytes; every lower, upper, slot and free number). The front-packed offsets in scene 2 (A at 0, B at
  300, C at 500) are worked out from those sizes for the broken version. The PostgreSQL page is the lesson's Try it
  output (lower 652, upper 656, 157 rows of 48 bytes). The drawing is not to scale: the header and slots are drawn
  wider than their 4 bytes.

## The one picture

One long page bar across the frame: byte 0 on the left, 4,096 on the right. The grey header at the left edge, teal
slot boxes growing rightward from it (slot number inside), coloured rows growing leftward from the right end (A
blue, B gold, C green, D purple), and "free" in the gap. Above the bar, two yellow markers: `lower` where the slots
end and `upper` where the rows begin. Below it, the slot table, "n = (offset, length)" in each row's colour, and on
the left an index chip "index: C is at page 7, slot 2". Red marks what broke. Captions on one line at the bottom.

## Scene 1 · The question · 0:00–0:30 · [FAMILIAR] [QUESTION] [LOOP-PLANT]

VO: A database keeps each table in a file of fixed-size pages. Rows come in different sizes: a ledger row takes 48
bytes, and one with a long note over 500. So how do we fit them into one page, and find one again quickly?

The lab's page holds 4,096 bytes. Our rows: A is 300 bytes, B is 200, and C is 400.

SCREEN: The empty page bar with 0 and 4,096 at its ends. Three loose row boxes, A, B and C, wait below it with their
sizes.

## Scene 2 · Pack them from the front · 0:30–1:15 · [PAIN] [BREAK] [JOKE:release]

VO: The simplest way packs them back to back from the start. A at byte 0, B at 300, C at 500. To find C, you read
A's length and skip it, then B's length and skip it. Slow, but it works.

Say an index, a lookup table elsewhere, notes that C starts at byte 500.

Now delete B, and slide C down to close the gap. C now starts at 300, and byte 500 is the middle of C. The index now points, with full confidence, at the middle of a
row.

SCREEN: A, B, C slide into the bar from the left, offsets 0, 300, 500 above them. A yellow cursor hops over A and
B. The index chip "index: C at byte 500" with an arrow to C's left edge. B turns red and fades, C slides left to
300, the arrow now lands in the middle of C and turns red.

## Scene 3 · A list at the front · 1:15–1:45 · [WISH] [BREAK]

VO: Next idea: a small numbered list at the start of the page. Entry 2 holds C's offset and length. Finding C is one
lookup, and C can move, as long as entry 2 is updated. But how long is the list? Fix its size, and you cap the rows
per page. Grow it, and every row behind it has to move.

SCREEN: The bar resets. A teal list of three entries at the front, the rows right after it. Captions: "one lookup:
entry 2 says where C is", "a fixed list: at most 3 rows", "a longer list: every row moves" (red, the rows shift).

## Scene 4 · The filing drawer · 1:45–2:20 · [ANALOGY] [MAP]

VO: A filing drawer shows the fix. Inside its front, a numbered list is taped: line 2 says where folder 2 sits. Pull
a folder out and push the rest together, and you correct the positions on the list. But line 2 is still line 2.
Anyone who wrote down drawer 0, line 2 still finds the folder.

Let's map it. The drawer is the page. The list is an array of slots, one per row. And each folder is a row.

SCREEN: The bar empties and its title becomes "the page: the drawer". Captions say the story; the mapping appears
as each part is named.

## Scene 5 · Grow toward each other · 2:20–3:20 · [SHRINK] [PREDICT] [PAUSE] [SHOW]

VO: So let the two grow toward each other. A 4-byte header at the start keeps two numbers. lower is where the slots
end: 4, right after the header. upper is where the rows begin: 4,096, the end of the page. Everything between them
is free.

Insert A, 300 bytes. It goes at the back, so upper drops to 3,796. Slot 0 goes at the front and holds A's offset
and length, 3,796 and 300, and lower grows to 8.

B, 200 bytes, gets slot 1, at 3,596.

Now C, 400 bytes. Where does it start, and which slot does it get? Pause and guess.

(three seconds)

At 3,196, in slot 2. lower is 16 now, and the free space is still one gap in the middle, 3,180 bytes. So the index
stores C's address as page 7, slot 2. It never stores the byte offset.

SCREEN: The header and the `lower` and `upper` markers. Each insert: the row drops in at the right end, the slot
box at the front, the slot table gains "0 = (3796, 300)", and the markers move with their numbers. Countdown. Then C
and slot 2, the gap label "free 3,180 B", and the index chip "index: C is at page 7, slot 2".

## Scene 6 · Delete, then tidy · 3:20–4:05 · [SHOW] [LOOP-PAYOFF] [JOKE:reward]

VO: Delete B. The page only marks slot 1 dead, as zero, zero. B's 200 bytes are still there, a hole between A and
C, and the free gap is still 3,180.

Tidying the page slides the live rows toward the end. C moves up 200 bytes, to 3,396, and slot 2 gets the new
offset. The index still says slot 2, so it still finds C, and the gap grows to 3,380. Same as the drawer: the folder
moved, and line 2 didn't.

SCREEN: Slot 1 turns grey, "1 = (0, 0)"; B's box becomes a dashed hole. C slides right by 200 bytes, slot 2's entry
changes to "(3396, 400)", the index chip's arrow follows slot 2 to C (green). The gap label becomes 3,380.

## Scene 7 · Where the drawer breaks, and a rule · 4:05–4:50 · [BREAK of the analogy] [GUARDRAIL] [JOKE:is-the-explanation]

VO: Here the drawer picture breaks. A list taped inside a drawer takes no room from the folders. On a page, the
slots and the rows share the same 4 KB. The page is full when lower and upper would cross.

Insert D, 250 bytes. It gets slot 3, not the dead slot 1. An old index entry might still say slot 1, and it would
find D instead of nothing. It's like giving out an old phone number: whoever saved it reaches a stranger. PostgreSQL
reuses a dead slot only after its cleanup, VACUUM, has removed every index entry that points at it.

SCREEN: The slot boxes and the rows glow from both ends toward the middle. D drops in at 3,146 with slot 3; slot 1
pulses grey; markers lower = 20, upper = 3,146; free 3,126.

## Scene 8 · Names, and a real page · 4:50–5:35 · [NAME]

VO: This layout is called a slotted page. PostgreSQL uses it, with a 24-byte header and 4-byte slots it calls line
pointers. Its header calls the two numbers pd_lower and pd_upper.

On a real 8 KB page of the ledger table, lower is 652 and upper is 656: a 24-byte header and 157 line pointers, 4
free bytes, then 157 rows of 48 bytes. One more row needs 52, so the page is full.

SCREEN: Titles become "a slotted page", "lower (pd_lower)", "upper (pd_upper)". Three lines replace the slot table:
"lower = 24 + 157 × 4 = 652", "upper = 8,192 − 157 × 48 = 656", "free: 4 bytes; one more row needs 48 + 4 = 52".

## Scene 9 · The cost, the promise, and a check · 5:35–6:15 · [GUARDRAIL] [MORAL] [PREDICT] [PAUSE]

VO: The slots add one step to every lookup: the index points at the slot, and the slot points at the row. That step
buys one promise. A row's slot number never changes while the row lives, even when its bytes move.

One quick check. Delete C now. What happens to lower, upper and the free gap? Pause and think.

(three seconds)

Nothing, yet. Slot 2 is marked dead, and C's 400 bytes stay where they are until the page is tidied.

SCREEN: The moral caption "the index points at the slot; the slot points at the row". Countdown. Slot 2 greys,
"2 = (0, 0)"; the markers and "free 3,126 B" pulse unchanged.

---

### Beat check

- FAMILIAR (pages from section 0) and QUESTION first (scene 1).
- BREAK of the offset idea (scene 2) and of the fixed list (scene 3), before the analogy.
- ANALOGY + MAP said out loud (scene 4), before any name.
- PREDICT with PAUSE (scene 5, and the check in scene 9); SHOW right after.
- NAME after the mechanism is seen (scene 8). The analogy's breaking point used (scene 7). GUARDRAIL (scenes 7, 9).
  MORAL last.
- Light moments: the index pointing at the middle of a row (~1:10), the folder moved and line 2 didn't (~4:00), the
  old phone number (~4:35).

### Accuracy notes for the producer

- Every lower, upper, slot and free number is the lesson's stepper (the lab's `SlottedPage`, a 4-byte header). The
  front-packed offsets (0, 300, 500) follow from the sizes and are only for the broken version.
- PostgreSQL: 24-byte page header, 4-byte line pointers, `pd_lower`/`pd_upper`, page 0 of `ledger` with lower 652,
  upper 656 and 157 rows of 48 bytes, all from the lesson and its Try it output. VACUUM's rule for reusing a dead
  line pointer is the lesson's.
- check_audio: 93.8% at -16.1 LUFS. "Delete B." was heard as "Delete Baye", so SAY rules speak it as "Delete row B"
  and "between row A and row C" (the extra "row"s count as differences). The rest are Whisper spellings: numbers
  written out, postgres, kilobytes, "P D", "sees" for C's.
- "Page 7" in the index entry is the stepper's example page number.
- The picture is not to scale: header and slots are drawn wider than 4 bytes so their numbers can be read.
- Left to the lesson: the special area at the end of the page, the row header (`t_hoff`), the 48-byte row of 1,000
  ledger rows and how 157 rows fill page 0 (section 0), and what VACUUM does in full (section 2).
