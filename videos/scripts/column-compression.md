# Four currencies, a million rows: how one column squeezes small

- Slug / scene: `column-compression`, `videos/scenes/column_compression.py:ColumnCompression`
- Lesson: `store-11`, section 1, "One column's values look alike, so they squeeze small"
- Audience / level: a complete newcomer. Has seen a spreadsheet; doesn't know what a byte, a bit, a column store or
  an encoding is.
- Length: 5:28 (~855 words of narration at Kokoro's ~178 words a minute, plus three pauses and silent
  builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=160`, the end of scene 5 (plain strings, codes, the key on the cover, the 24 packed bits, "84 bytes" and
  "31 bytes")
- The learner's real question: a column holds the same few values over and over. Why store each one in full, and
  how small can it really get?
- Misconception to steelman and break: (1) "just zip it", broken by unzipping a whole 256 KB block to read one
  value; (2) "runs are the best shorthand, use them everywhere", broken by the unsorted amounts (144 bytes against
  96 plain).
- Concept chain: a column store keeps one binder per detail → one binder's values look alike → a key on the cover
  (dictionary) → codes in the fewest bits (bit-packing), numbers after a base (frame of reference) → equal neighbours
  once (run-length) → none wins everywhere, so try each per chunk and keep the smallest (hardest last)
- Analogy family: the lesson's shoebox of receipts cut into strips and filed in one binder per detail; a key written
  on the binder's cover; a vacuum-packed binder for zipping. The binders break where the lesson says they do: paper
  doesn't shrink, bits do.
- Open loops: "how small can a column like this get?" planted in scene 1 → answered in scene 10; "the chunk notes
  its smallest and largest value" planted at the end → the next section.
- Assumptions: every number is the lesson's stepper and Try it: the 12 currencies (EUR EUR EUR GBP EUR USD EUR EUR SEK
  EUR GBP EUR), 84 bytes plain, codes 0 to 3, 31 bytes, 250 KB for a million; the 12 amounts (1,250 300 8,900 450
  2,100 760 300 5,400 990 3,300 610 1,800), base 300, largest 8,600, 14 bits, 40 bytes against 96, run-length 144;
  DuckDB 5.5 MB against PostgreSQL's 66 MB; 7 MB against 250 KB, about 28 times. The receipt's values (p1, m42, EUR,
  settled, 1,250, 10:00:02) are the lesson's compare block.

## The one picture

Top: the shelf, six blue binders (id, shop, currency, status, amount, time). Middle: two rows of twelve cells, the
chunk: the top row plain (blue), the bottom row encoded (gold), each with its size in bytes at its right end. Right:
the key on the cover (gold card), later the base card. Lower band: the bytes of one value, the packed bits (green),
then the three choices and the size bars. Captions at the bottom. Yellow marks what's being read, red a cost, green
the win, purple the wrong idea.

## Scene 1 · The binders · 0:00–0:35 · [FAMILIAR] [ANALOGY] [QUESTION] [LOOP-PLANT]

VO: Picture a café owner with a shoebox of paper receipts, one for every card payment. Each receipt has an id, the
shop, the currency, a status, the amount and the time. To add up the amounts, she used to read every receipt. So she
cut each one into strips, one per detail, and filed them in six binders, in the same order. Now the total needs one
binder. But open the currency binder, and look. EUR, EUR, EUR, GBP, EUR. A million strips, and only four different
values on them. So how small can a column like this get? Hold that question.

SCREEN: Title card. A receipt with its six lines, a stack of receipts behind it ("a shoebox: one receipt per
payment"). The six lines lift off as strips and fly up into six binders on the shelf; the amount binder glows. The
currency binder glows, and twelve cells spill out of it into the top row. A "?" and the question as a caption.

## Scene 2 · The plain way · 0:35–1:05 · [PAIN] [JOKE:amplify] [WISH]

VO: Take twelve strips, one chunk of the column. Space is counted in bytes, and a byte holds about one letter.
Stored plainly, each value is a 4-byte length, then 3 bytes of text: 84 bytes for twelve. A million take 7 MB, for
four different values. Write E U R by hand a million times, and by strip four hundred you'd invent a shorthand.
That's the wish: a shorthand that's quick to read back.

SCREEN: Under the row, one value drawn as seven byte boxes (four grey, "4-byte length", then E, U, R, "3 bytes of
text") and "= 7 bytes". "12 x 7 = 84 bytes" at the row's end. Caption "a million rows: 7 MB, for 4 different
values", then "wanted: a shorthand that's quick to read back".

## Scene 3 · Zip it? · 1:05–1:30 · [BREAK]

VO: The first idea most of us have: zip it, the way you zip files before you email them. It does shrink. But every
scan then pays to unzip whatever it touches, and to read one value, you unzip the whole block around it, about
256 KB. It's a vacuum-packed binder: small on the shelf, but you cut open the bag to read one strip.

SCREEN: A purple bag closes over the row ("zipped"). A yellow arrow points at one cell; the whole bag pulses;
caption "to read one value: unzip the whole block (about 256 KB)". A red cross; the bag fades.

## Scene 4 · A key on the cover · 1:30–2:05 · [ANALOGY] [MAP] [NAME]

VO: So back to the shorthand. On the binder's cover, the owner writes a key, in alphabetical order: 0 is EUR, 1 is
GBP, 2 is SEK, and 3 is USD. Now each strip holds one small number instead of a word. Let's map it. The key on the
cover is the dictionary. The number on a strip is a code: its value's place in the key. This is called dictionary
encoding. And since the key is sorted, a test like currency before GBP becomes code below 1, right on the codes.

SCREEN: The gold card "the key on the cover" draws on the right; the four different values fly into it from the
row, each once. Twelve gold code cells appear under the strings, one by one. Captions name the parts. Then every EUR
cell and every 0 code glow together: "currency < 'GBP'  is  code < 1".

## Scene 5 · Paper doesn't shrink · 2:05–2:50 · [BREAK of the analogy] [SHRINK] [PREDICT] [PAUSE] [SHOW] [NAME]

VO: Here the binders stop being a good picture. A paper strip with a 0 on it is just as thick as one that says EUR.
Paper doesn't shrink, but bits do. A bit is a single 0 or 1, and 8 bits make a byte. Our codes only go up to 3, and
3 fits in 2 bits. So how many bytes do the twelve codes take now? Pause and guess.

(three seconds)

Two bits each, written back to back: 24 bits, which is 3 bytes. With the key, the chunk takes 31 bytes instead of
84. A million currencies take 250 KB instead of 7 MB. Storing each number in the fewest bits that hold the largest
one is called bit-packing.

SCREEN: Caption "where the binders stop working: paper doesn't shrink, bits do". "0 to 3 fits in 2 bits: 00 01 10
11". Countdown. The codes turn into 00, 01, 11 ...; a copy of them slides down into a green bar of 24 bits with
three "byte" braces; "24 bits = 3 bytes"; the row's size: "28 + 3 = 31 bytes". Caption "a million currencies:
250 KB instead of 7 MB", then "bit-packing".

## Scene 6 · Numbers too · 2:50–3:25 · [SHOW] [NAME]

VO: Numbers get the same trick. Twelve amounts, in cents, each in an 8-byte slot built for numbers with nineteen
digits: 96 bytes. First, subtract the chunk's smallest amount, 300, from every value.
Now the largest left is 8,600, and that fits in 14 bits. Twelve values take 168 bits. In three 8-byte words, plus a
small header that remembers the 300, that's 40 bytes instead of 96. Taking off a base like this is called a frame
of reference.

SCREEN: The amount binder glows. The top row becomes the twelve amounts, "12 x 8 bytes = 96 bytes". The card becomes
"header: base 300". The bottom row shows the amounts minus 300; 8,600 glows, "8,600 fits in 14 bits (up to
16,383)". Twelve green segments slide into a bar "12 x 14 bits = 168 bits"; "3 words of 8 bytes + a 16-byte
header = 40 bytes". Caption "frame of reference: subtract the chunk's smallest value first".

## Scene 7 · Runs · 3:25–3:50 · [SHOW] [NAME]

VO: One more shorthand. If the table were sorted by currency, equal codes would sit together: eight zeros, two
ones, one two and one three. Write each run once, with its length. Four runs. That's run-length encoding. It shines
on sorted columns.

SCREEN: Back to the currencies and their codes. Both rows slide into sorted order together. The eight 0 cells merge
into one wide cell "0 x 8", then "1 x 2", "2 x 1", "3 x 1": "4 runs". Caption "run-length encoding: each run once,
with its length".

## Scene 8 · None wins everywhere · 3:50–4:30 · [PREDICT] [PAUSE] [BREAK] [JOKE:release] [NAME]

VO: So should every column use runs? Try it on our twelve amounts, which aren't sorted. Smaller than plain, or
bigger? Pause and guess.

(three seconds)

Bigger. Twelve runs of length one, at 12 bytes each: 144 bytes, against 96 plain. Not much of a run. So no encoding
wins everywhere. For each chunk, the engine tries them all and keeps the smallest: here, bit-packing, at 40 bytes. DuckDB, a free database built for
reports, does this chunk by chunk. On the lesson's million payments, it bit-packed the numbers and gave the text a
dictionary: 5.5 MB in all. PostgreSQL, a free database that keeps whole rows together, needs 66.

SCREEN: The amounts again, the bottom row outlined in red: "run-length: 12 runs of length 1". Countdown. Three
chips: "run-length: 144 bytes" (red), "plain: 96 bytes", "bit-packed: 40 bytes" (green); the green one glows, the
others dim: "keep the smallest". Tags under the binders ("bit-packed" under id, shop, amount and time; "dictionary"
under currency and status). Two bars: "PostgreSQL, whole rows: 66 MB" and "DuckDB, by column: 5.5 MB".

NOTE: "Not much of a run" is the light moment, right after the reveal; it restates the cost (one run per value).

## Scene 9 · Why squeeze at all? · 4:30–4:50 · [GUARDRAIL]

VO: Disks are cheap, so why squeeze at all? Because a scan spends most of its time moving bytes, from the disk to
memory and on to the processor. 250 KB is about 28 times less to move than 7 MB, and undoing a 2-bit code takes a
few simple steps.

SCREEN: Two bars for the currency column: "plain: 7 MB" (red, long) and "codes: 250 KB" (green, short); a yellow dot
runs along each; "about 28 times fewer bytes to move".

## Scene 10 · The moral, and a check · 4:50–5:30 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, how small can a column get? As small as its values are alike. Write each different value once, in a key.
Store each number in the fewest bits. Write a run once, with its length. Then try them all and keep the smallest.

One quick check. Ten million payments, sorted by status, which has three values. Which shorthand stores the status
column smallest? Pause and think.

(three seconds)

Runs. Sorted by status, almost every chunk holds one status: a single run, one value and one count. Bit-packed codes
would still cost 2 bits a row, 2.5 MB. Each chunk also notes its smallest and largest value, so a scan can skip it
unread. That's next.

SCREEN: The moral in yellow, one clause at a time, each with its picture lit (the key, the bits bar, the runs).
For the check: the status binder glows; one chunk of status codes, twelve 0s; countdown; one wide gold cell "0 x 12",
"1 run", "a run: one value + one count, however long the chunk"; "bit-packed codes: 2 bits a row = 2.5 MB".
Last caption "values that look alike squeeze small: try each shorthand, keep the smallest".

---

### Beat check

- Opens with FAMILIAR and the QUESTION (scene 1), from the lesson's shoebox and binders.
- PAIN and WISH (scene 2), BREAK of the obvious fix (scene 3: zip it).
- ANALOGY + MAP said out loud (scene 4: the key on the cover is the dictionary, the number on a strip is the code);
  the analogy's breaking point is used (scene 5: paper doesn't shrink).
- PREDICT with PAUSE three times (scenes 5, 8 and the check in 10); SHOW right after each.
- NAME after each SHOW: dictionary encoding (4), bit-packing (5), frame of reference (6), run-length encoding (7).
- BREAK of the wrong model "runs everywhere" (scene 8). GUARDRAIL (scenes 8 and 9), MORAL and check (scene 10).
- Light moments: the hand-written million EURs (0:55), the vacuum-packed binder (1:25), "not much of a run" (4:05).

### Accuracy notes for the producer

- 84, 31, 96, 40 and 144 bytes are the lesson's stepper in the lab's format (a 4-byte length per string; RLE as an
  8-byte value and a 4-byte length per run; bit-packing in 64-bit words plus a 16-byte header).
- "A byte holds about one letter" is true of the plain ASCII codes shown; other alphabets need more.
- DuckDB chose DICT_FSST for both text columns: a dictionary whose strings are squeezed again with FSST. The video
  says "gave the text a dictionary".
- The 256 KB block size and the three reasons to avoid general-purpose compressors are DuckDB's 2022 article, as the
  lesson cites it. The video names two (slow to undo, whole blocks); "they hide the shape of the data" is left to the
  lesson.
- "A number with nineteen digits": a signed 8-byte number goes up to about 9.2 quintillion, 19 digits.
- Random 64-bit numbers gaining nothing from any encoding, and the times column (12 bits per hour once the hour's first second is subtracted) and the stacked encodings beyond
  dictionary plus bit-packing are left to the lesson.
- The check's 2.5 MB is the lesson's quiz: 10 million rows at 2 bits.
