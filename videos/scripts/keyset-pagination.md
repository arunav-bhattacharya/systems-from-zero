# Why is page 5,001 slow? Count your way there, or open at the tab

- Slug / scene: `keyset-pagination`, `videos/scenes/keyset_pagination.py:KeysetPagination`
- Lesson: `sql-08`, section 3, "Page 5,001 the slow way: OFFSET reads every row it skips" (the section's figure and
  last line point to the keyset fix of section 4, which the video shows briefly)
- Audience / level: a complete newcomer. Has met a table, ORDER BY and an index once in earlier lessons.
- Length: 5:10 (~820 words of narration at the Kokoro voice's ~180 wpm, plus a guess, a check and the silent
  moves)
- Poster: the default, 82% in (the tab behind 33, page 2 after it, and the one trip down the drawer)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: page 5,001 returns 20 rows, like page 1. Why is it slower, and why did a payment I
  already saw turn up again?
- Misconception to steelman and break: "page 5,001 is a place, like page 300 of a book, that the database opens at
  once". Broken by the guess in scene 3: it reads 100,020 entries to return 20.
- Concept chain: OFFSET skips rows by producing them → an index holds keys and pointers, not positions, so skipping
  means reading → the cost grows with the page number → counting also shifts when rows arrive or leave → the screen
  knows the last row it showed → ask for rows after that key (a cursor, a row comparison) → one trip down the index,
  no shift → the price: no page numbers, a unique order, the whole comparison (hardest last)
- Analogy family: the lesson's receipts filed in one long drawer by time; counting from the front because no receipt
  has its position written on it; the cursor is a tab clipped behind the last receipt handed over. Breaks: a person
  can open the drawer near the middle by feel; an index can't even guess.
- Open loops: "why slower?" and "where did the second coffee come from?" planted in scene 1 → answered in scenes 3
  and 5, recapped in scene 9.
- Assumptions: the million-row numbers are the lesson's EXPLAIN output (page 1: 20 entries, 0.148 ms; page 5,001:
  100,020 entries, about 50 ms; page 45,001: 900,020 rows, 1.2 s; keyset: 20 entries, 0.723 ms). The five-per-page
  example is the lesson's Try it (37 to 33, then 33 to 29 after payment 38 arrives). The keyset page and the deleted
  row check were re-run in SQLite on the seed (32 to 28; with 35 deleted, OFFSET 5 gives 31 to 27).

## The one picture

Top: the query. Under it, the index drawn as one long drawer of receipts (thin ticks), newest on the left,
"1,000,478 entries". A yellow finger counts along it; red fills what OFFSET reads and throws away, a green sliver
the 20 it returns. Middle: either a small table of costs (page, entries read, time) or, for the small example, the
seed's payments 38 to 27 as receipt cards in a row, newest on the left, with brackets for page 1 and page 2. The tab
(the cursor) is a yellow tab clipped behind a card, and a yellow arrow from above the drawer shows the one trip down.
Red means read and thrown away, or wrong; green means returned or right.

## Scene 1 · The list on your phone · 0:00–0:26 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: Picture scrolling back through your card payments on your phone, newest first, 20 at a time. The first pages appear at
once. Far back in the list, each new page takes a little longer. And once, a coffee you saw a moment ago turns up
again at the top of the next page. So why does page 5,001 cost more than page 1? And where did that second coffee come
from?

SCREEN: A phone, "your payments, newest first", with placeholder rows and a page counter (page 1, 2, 3, then 5,001
with a spinner); "coffee 17.20" at the bottom of one page and again, in red, at the top of the next. Captions with the
two questions.

## Scene 2 · The obvious query · 0:26–0:51 · [FAMILIAR] [SHRINK]

VO: Behind a list like that, the app asks the database for one page at a time. The obvious way: sort newest first, skip
the pages before this one, and keep 20. In SQL, ORDER BY created_at DESC sorts newest first, and payment_id breaks
ties. LIMIT 20 keeps 20 rows. And OFFSET 100,000 skips the first 100,000. That's page 5,001.

SCREEN: The query appears line by line, each part glowing as it's named: `SELECT payment_id, created_at,
amount_minor FROM payments` / `ORDER BY created_at DESC, payment_id DESC LIMIT 20 OFFSET 100000`.

## Scene 3 · A million rows, and a guess · 0:51–1:41 · [PREDICT] [PAUSE] [SHOW] [BREAK]

VO: Let's run it on a table of a million payments, with an index: a separate list of each payment's time and number, kept
in order, each pointing to its row. Page 1 reads the newest 20 entries and stops. A fraction of a millisecond. Page
5,001 also returns 20 rows. So how many entries does it read? Pause and guess.

(three seconds)

100,020. It starts at the newest entry, walks through 100,000 of them, fetches each row, and throws them all away.
Then it keeps the next 20. About 50 milliseconds. Page 45,001 reads 900,020 rows, and takes 1.2 seconds. Same 20 rows
out, every time. The cost grows with the page number.

SCREEN: The drawer draws in. A green sliver at its left end for page 1; the costs table starts: "page 1 · 20 ·
0.15 ms". A yellow "?" in the next row, countdown. Then the finger sweeps a tenth of the drawer, red fills behind
it, a counter runs to 100,000, a green sliver follows: "page 5,001 · 100,020 · about 50 ms". Then the red sweeps to
nine tenths: "page 45,001 · 900,020 · 1.2 s".

## Scene 4 · The drawer · 1:41–2:23 · [ANALOGY] [MAP] [JOKE:pivot]

VO: Why can't it jump? Picture the payments as receipts, filed in one long drawer by time. Someone asks for the 100,001st
receipt. No receipt has its position written on it, so you count from the front. One, two, three... and you're still
counting at lunch. The index is that drawer. Each entry holds a time, a payment number, and where its row lives. Not a
position. So to skip 100,000 entries, PostgreSQL reads them. Its manual says so: rows skipped by OFFSET still have to
be worked out. The drawer picture breaks here. A person could at least open the drawer near the middle, by feel. An
index can't even guess.

SCREEN: The drawer's label becomes "a drawer of receipts, filed by time"; one receipt pops up above it reading "a time,
a payment number, → its row", with "no position written on it" in red. The finger counts from the left again, and the
counter runs to 100,000. Captions map: "a receipt = an index entry; the drawer = the index".

## Scene 5 · The second coffee · 2:23–3:00 · [SHRINK] [SHOW] [BREAK]

VO: OFFSET has a second problem. Let's shrink it to five per page, on the course's small table. Page 1 shows payments 37
down to 33. While you read it, a new payment arrives: 38. Everything slides back one place. Page 2 skips the first
five rows, which are now 38 down to 34, so it starts at 33. Payment 33, a second time. That's the coffee. A deleted
row does the opposite: the next page skips a row nobody saw. A nightly copy, page by page, can copy a payment twice or
miss one, with no error.

SCREEN: The costs table goes; ten receipt cards (37 to 28, with dates) in a row. A bracket "page 1" over 37 to 33,
each marked "seen". Card 38 slides in at the left and every card moves right one place. The bracket "page 2: OFFSET
5" now covers 33 to 29; card 33 turns red with "again".

## Scene 6 · The tab · 3:00–3:12 · [WISH]

VO: So here's the wish. The screen already knows where the last page ended: the last row it showed. In the drawer, clip a
tab behind the last receipt you handed over. Next time, open the drawer at the tab.

SCREEN: A yellow tab clips onto the back of card 33.

## Scene 7 · The cursor, and the seek · 3:12–4:00 · [NAME] [SHOW]

VO: In SQL, the tab is called a cursor: the last row's sort values, its created_at and its payment_id. The next page asks
for the rows after it: WHERE the pair is less than the cursor's two values. PostgreSQL compares the pairs left to
right, the way you'd compare two dates: the year first, and the day only if the years match. Because the list is
newest first, less means further down. Back to our five. Page 2 is 32 down to 28. No repeat. And the new payment sorts
before the tab, so it shows up on page 1. On the million rows, PostgreSQL goes down the index once, straight to the
tab, and reads the next 20 entries. Under a millisecond, on page 2 or on page 5,001. This is called keyset pagination.

SCREEN: The query's last line changes to `WHERE (created_at, payment_id) < (:last_created_at, :last_payment_id)` and
`ORDER BY created_at DESC, payment_id DESC LIMIT 20`. The bracket "page 2: after the tab" covers 32 to 28 (green).
On the drawer, a yellow arrow drops from above straight to the tab at one tenth, and a green sliver follows; the label
"tab, page 5,001: 20 entries read, 0.7 ms" sits under the drawer.

## Scene 8 · The price · 4:00–4:27 · [GUARDRAIL]

VO: It has a price. You give up page numbers: a cursor moves one page at a time, so no jumping to page 4,000. For an
endless scroll, or a nightly export, that costs nothing. Two details decide whether it's right. The sort must be
unique, which is why payment_id is in it. And the WHERE must compare both values. Compare created_at alone, and
payments at the tab's exact time are skipped, with no error.

SCREEN: Captions: "no page numbers: one page at a time", "fine for an endless scroll or an export", "1. a unique
sort (payment_id breaks ties)", "2. compare both values, not created_at alone".

## Scene 9 · The moral, and a check · 4:27–5:10 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, why was page 5,001 slow, and where did the second coffee come from? OFFSET counts its way to a page, through every
row before it. That gets slower, and it shifts when rows come and go. Find the page by a key instead. One quick check.
Start again: page 1 shows 37 down to 33. This time, payment 35 is deleted. With OFFSET 5, which payment does nobody
ever see? Pause and think.

(three seconds)

32. Page 2 skips five rows, and 32 is now the fifth. With the tab behind 33, page 2 starts at 32 anyway.

SCREEN: Caption "counting gets slower and shifts; find the page by a key". 38 leaves, the cards slide back; card 35
fades and the rest slide left; 27 arrives at the right. Countdown. The OFFSET bracket covers 31 to 27, card 32 turns
red "never shown"; then the tab bracket covers 32 to 28 in green.

---

### Beat check

- QUESTION from a felt situation (scene 1); FAMILIAR query (scene 2).
- PREDICT with PAUSE breaks "a page is a place" (scene 3); ANALOGY + MAP explains why (scene 4), with its breaking
  point said out loud.
- SHRINK to five per page and SHOW the second break (scene 5); WISH (scene 6); NAME after it (scene 7).
- GUARDRAIL (scene 8); MORAL, loop payoff and a check answerable from the cards (scene 9).
- Light moments: still counting at lunch (about 1:45), the drawer that can't be opened by feel (about 2:10).

### Accuracy notes for the producer

- Million-row figures are the lesson's EXPLAIN output on the large data set with an index on `(created_at,
  payment_id)` (1,000,478 entries): page 1 reads 20 entries in 0.148 ms; page 5,001 reads 100,020 entries, 2,865
  buffers, 48 ms; page 45,001 read 900,020 rows in 1.2 s; the keyset page reads 20 entries, 5 buffers, 0.723 ms.
  Buffers are left to the lesson.
- "Its manual says so" paraphrases the PostgreSQL 18 documentation the lesson quotes: rows skipped by OFFSET still
  have to be computed inside the server.
- The five-per-page example is the lesson's Try it (all statuses, so failed and pending payments are in the list).
  The keyset page 2 (32 to 28) and the deleted-row check (OFFSET 5 gives 31 to 27, so 32 is never shown) were run in
  SQLite on the seed.
- The phone and its "coffee 17.20" are illustration; payment 33 is 1720 cents at shop 7 in the seed.
- The video says "under a millisecond" for the keyset page (0.723 ms in the lesson's run); the lesson says "about a
  millisecond or less".
- Left to the lesson: the OR form that PostgreSQL 18 can't use as an index condition, going backward, opaque tokens,
  and the rule that the index must match the ORDER BY column for column.
- Spoken forms via `SAY`: OFFSET, LIMIT, ORDER BY, WHERE and DESC in words, created_at as "created at", payment_id as
  "payment I D". check_audio caught "100,001st" said as "one hundred thousand first"; a `SAY` rule now says "one hundred
  thousand and first" (captions keep the digits).
