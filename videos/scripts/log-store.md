# Where is payment 1 now? A notebook in pen, and a slip at the front

- Slug / scene: `log-store`, `videos/scenes/log_store.py:LogStore`
- Lesson: `store-01`, section 1, "Finding a payment again: a file we only add to, and a map in memory"
- Audience / level: a complete newcomer who has met section 0: the store adds every payment to the end of one file
  and forces it to the drive before it replies OK. Knows nothing about indexes or hash maps.
- Length: 5:15 (~870 words of narration at the Kokoro voice's ~180 words a minute, plus two guesses and silent
  moves)
- Poster: `POSTER=182` (get auth:1: the slip's line, the arrow to byte 92 and "read 8 bytes at 92: CAPTURED")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: the file keeps every payment safe, but how do we read one back without reading
  the whole file?
- Misconception to steelman and break: "give each key a fixed spot in the file and write over it". Broken twice:
  CAPTURED (8 bytes) doesn't fit where PENDING (7) was, and a power cut halfway through the overwrite leaves
  CAPTING, half old and half new, with no copy of either.
- Concept chain: a scan finds the answer but reads everything → writing in place breaks → the notebook in pen and
  the slip at the front → the slip points at the newest value's byte → a get is one lookup and one read → overwrite
  and delete are appends (tombstone) → names (append-only log, keydir, Bitcask) → the slip lives in RAM and is
  rebuilt from the file → limits (every key in RAM, no order)
- Analogy family: the lesson's café notebook. Each sale on the next empty line, in pen, never rubbed out; a
  correction is a new line at the bottom; a slip at the front lists the line with each customer's latest entry.
- Open loops: "how do we find auth:1?" planted in scene 1 → answered in scene 6; the slip's paper planted in
  scene 4 → broken in scene 9 (paper survives the night, RAM doesn't) → used in the check.
- Assumptions: the records, offsets and value positions are the lesson's stepper (section 2) exactly: auth:1
  PENDING at 0 (value at 26, 7 bytes), auth:2 PENDING at 33 (value at 59), auth:1 CAPTURED at 66 (value at 92, 8
  bytes), auth:2 CAPTURED at 100 (value at 126, 8 bytes). The tombstone for auth:1 at 134 is computed from the
  lab's format (20-byte header + 6-byte key, no value bytes). auth:7 is a made-up missing key. The byte strips in
  scene 3 illustrate the lesson's two claims about writing in place; CAPTING is an illustration, not an output.

## The one picture

Left: the notebook, `data.log` on the drive, a ruled page with a faint red margin. Byte offsets in the margin
(0, 33, 66, 100, 134). Each line is one record in three cells: a grey `hdr` (the 20-byte header), the key in
blue, the value. Dead records turn dark grey; the tombstone is purple. Right: the slip (teal), later named the
keydir, one line per key. Under it, the request chip (gold) and its result. Yellow marks what just changed; red
marks what broke. Captions on one line at the bottom; stat lines in the band above them.

## Scene 1 · The file, and the question · 0:00–0:35 · [FAMILIAR] [QUESTION] [LOOP-PLANT]

VO: Our store keeps every payment in one file, and it only ever adds to the end. Payment 1 arrives, PENDING,
still waiting for the bank. Then payment 2. Then the money for payment 1 really moves, and its new status,
CAPTURED, goes at the end too.

Each line is one record. auth:1 is its key, the name we look it up by. The numbers on the left are byte offsets:
how many bytes from the start of the file each record begins.

Now the card reader asks: what's the status of auth:1? How do we find it?

SCREEN: The notebook draws. Three records drop in at 0, 33 and 66. The margin numbers glow. A gold chip
`get(auth:1)` appears on the right.

## Scene 2 · The scan · 0:35–1:20 · [PAIN] [WISH] [JOKE:amplify]

VO: The simplest answer is a scan. Read the file from the start, and keep the last value you see for that key.
PENDING at byte 0. Then CAPTURED at byte 66. The last one wins: CAPTURED. That cost all 100 bytes of the file.

Fine for three records. With a million records of about 40 bytes, every lookup reads 40 megabytes. Even from
memory, that's milliseconds per lookup, and it grows with every payment. It's answering one question by rereading
the shop's whole history.

What we want is to jump straight to auth:1's newest value, and read only that.

SCREEN: A yellow cursor walks down the margin; auth:1's two values turn gold as it passes; the result "CAPTURED,
after reading all 100 bytes". Stat lines: "1 million records of about 40 bytes: 40 MB read per lookup", "and it
grows with every payment" (red).

## Scene 3 · The obvious fix, broken · 1:20–2:10 · [BREAK] [JOKE:is-the-explanation]

VO: The obvious idea: give each key a fixed spot in the file, and write over it. No old values, nothing to scan.

Let's be fair and try it. auth:1's spot holds PENDING, 7 bytes. Now write CAPTURED over it. CAPTURED is 8 bytes.
The eighth one lands on auth:2's spot.

So make every spot 8 bytes. Now every PENDING wastes a byte, and the first longer status breaks it again.

Worse, cut the power in the middle of the write. C, A, P, T, and the lights go out. The spot now says CAPTING.
Half old, half new, and no copy of either. Not a status any bank has heard of.

So writing over old bytes is the risky part. Our file already does the safe thing: it never touches them.

SCREEN: The notebook dims. On the right, a strip of byte cells: auth:1's spot and auth:2's spot, 7 cells each,
PENDING in both. CAPTURED is typed in letter by letter; the D lands red on auth:2's first cell. The strip
rebuilds with 8-cell spots and a grey empty cell after each PENDING. CAPTURED is typed again; after C, A, P, T a
red "power cut" caption, and the spot reads CAPTING in red.

## Scene 4 · The café notebook · 2:10–2:50 · [ANALOGY] [MAP]

VO: A café's paper notebook shows the way. The owner writes each sale on the next empty line, in pen, and never
rubs anything out. A correction is a new line at the bottom.

And at the front, she keeps a slip of paper. For each customer, it says which line holds their latest entry. To
look someone up, she reads the slip, then turns to one line.

Let's map it. The notebook is our file, and each line is a record. Where a line sits is its byte offset. And the
slip is a small map in memory, from each key to where its newest value starts.

SCREEN: The notebook comes back to full brightness; its title becomes "data.log: the notebook". The slip draws on
the right in teal, titled "the slip: a map in memory". Captions map each part as it's said.

## Scene 5 · Write the slip · 2:50–3:35 · [SHRINK] [PREDICT] [PAUSE] [SHOW]

VO: Let's write the slip for our file. Every record starts with a 20-byte header, which holds its sizes. Then the
key, then the value. auth:2 is one record, at 33. Its key is 6 bytes, so its value starts at 33 plus 20 plus 6:
byte 59. And PENDING is 7 bytes.

Now auth:1. It has two records. Which one should the slip point at, and at which byte? Pause and guess.

(three seconds)

The newest one, at 66. Plus 20, plus 6: its value starts at byte 92, and CAPTURED is 8 bytes. The PENDING
record at 0 stays in the file, but nothing points at it now. Those are dead bytes.

SCREEN: The header, key and value cells of the record at 33 glow in turn; caption "33 + 20 + 6 = 59". The slip
gains "auth:2  value at 59, 7 bytes". A countdown. Then "auth:1  value at 92, 8 bytes" appears at the top of the
slip, the record at 66 glows, and the record at 0 turns dark grey.

## Scene 6 · One lookup, one read · 3:35–4:05 · [SHOW] [LOOP-PAYOFF] [JOKE:reward]

VO: Now ask again: get auth:1. One look at the slip says byte 92, 8 bytes. One read of exactly those 8 bytes:
CAPTURED. Eight bytes, where the scan read the whole file.

And a key that isn't on the slip, like auth:7? The answer is no, and it costs no trip to the drive at all. The
cheapest question there is.

SCREEN: The gold chip; an arrow from the slip's auth:1 line to the value cell at 66; result "read 8 bytes at 92:
CAPTURED". The chip becomes `get(auth:7)`; result "not on the slip: no read at all".

## Scene 7 · Changes are appends too · 4:05–4:45 · [SHOW]

VO: Now payment 2 is captured. The store adds a new record at the end, at 100, and moves auth:2's line on the slip
to byte 126. The old record at 33 is dead too. Nothing was written over.

And a delete? Say we delete auth:1. The store can't rub anything out, so it adds a tombstone: a record with the
key and no value, at 134. Its value size is set to minus 1. And the slip drops auth:1.

SCREEN: `put(auth:2, CAPTURED)`: a record drops in at 100, the slip line changes, the record at 33 greys.
`delete(auth:1)`: a purple record "auth:1 · no value" at 134; auth:1's slip line fades; the record at 66 greys.

## Scene 8 · Names · 4:45–5:15 · [NAME]

VO: This design has a name: Bitcask. It's a storage engine, the part of a database that stores the bytes and finds
them again. The company Basho built it in 2010 for its database, Riak. A file you only add to is an append-only
log. And the slip is the keydir, the store's index: a lookup table from each key to where its record lives.

Bitcask's paper says a read never needs more than one trip to the drive. With the keydir, that's true by
construction.

SCREEN: Titles become "data.log: an append-only log" and "keydir: a hash map in RAM". Caption "Bitcask (Basho,
2010, for Riak)", then "a read: never more than one trip to the drive".

## Scene 9 · Where the picture breaks · 5:15–5:40 · [BREAK of the analogy]

VO: Here the café picture breaks. A paper slip survives the night. The keydir lives only in RAM, the computer's
memory, and RAM forgets everything when the power goes. So after a crash, the store rebuilds the keydir by reading
the whole file from byte 0, in order. A tombstone tells it the key is gone.

SCREEN: The slip's outline pulses red and its entry fades; a caption "after a crash: read the whole file from byte
0 to rebuild it". The entry comes back.

## Scene 10 · Two limits · 5:40–6:10 · [GUARDRAIL]

VO: Two hard limits, before you pick this design. First, the keydir must hold every key in RAM. Fifty million
keys of 40 bytes, plus the map's own bookkeeping, is several gigabytes of memory.

Second, the keydir is a hash map. It turns each key into a number that says where to look, so it finds a key in one
step, but it keeps no order. So "every payment on card 4242 between 9 and 10" means checking every key. B+trees and
LSM trees, later in this track, keep their keys in order to fix that.

SCREEN: Stat lines: "1. every key in RAM: 50 million keys of 40 bytes = several GB"; "2. no order: a range of keys
means checking every key".

## Scene 11 · The moral, and a check · 6:10–6:45 · [MORAL] [PREDICT] [PAUSE]

VO: So: write in pen, at the end, and keep a slip of where each key's newest value starts. Every write is one
append. Every read is one lookup and one read.

One quick check. The power goes out, and the slip is gone. The store reads the file from byte 0 to rebuild it. What
is on the slip at the end? Pause and think.

(three seconds)

Only auth:2, with its value at 126, 8 bytes. The tombstone for auth:1 came last, so auth:1 stays off the slip.

SCREEN: Caption with the moral. The slip empties. Countdown. A yellow cursor walks down the margin and the slip
rewrites itself record by record: auth:1 at 26, auth:2 at 59, auth:1 at 92, auth:2 at 126, then auth:1 removed by
the tombstone.

---

### Beat check

- FAMILIAR (the file from section 0) and QUESTION first (scene 1), PAIN with the 40 MB bill (scene 2).
- BREAK of the obvious fix, steelmanned, with two failures (scene 3), before the analogy.
- ANALOGY + MAP said out loud (scene 4), before any name.
- PREDICT with PAUSE (scene 5, and the check in scene 11); SHOW right after each.
- NAME after the mechanism is seen (scene 8). The analogy's breaking point used (scene 9). GUARDRAIL (scene 10).
  MORAL last.
- Light moments: rereading the shop's history (~1:10), CAPTING (~2:00), the cheapest question (~4:00).

### Accuracy notes for the producer

- Record layout, offsets and value positions are the lesson's (figure and stepper): a 20-byte header (crc 4,
  tstamp 8, ksz 4, vsz 4), then the key, then the value; 33 bytes for auth:1 PENDING, 34 for CAPTURED. The
  tombstone at 134 is 26 bytes by `LogFormat.length` (vsz = -1, no value bytes).
- 40 MB per scan for a million records of about 40 bytes, "milliseconds per lookup" even from the page cache, 50
  million keys of 40 bytes = several GB, Bitcask (Basho, 2010, Riak) and "never more than one disk seek" are the
  lesson's.
- The fixed-spot strips are a teaching illustration of the lesson's "too small or wastes room" and "half old and
  half new"; the exact torn bytes depend on where the power fails.
- check_audio: 95.6% at -16.2 LUFS. The differences are Whisper spellings (auth1, key dir, bit cask, cafes, 4 242,
  "boss show" for Basho, "react" for Riak) and "C, A, P, T" run together as "see APT".
- The narration was tightened after the first draft (6:05): the timings in the scene headers above are the plan;
  the render runs 5:15.
- Left to the lesson: PostgreSQL's write-ahead log and LSNs (the Try it), torn tails and checksums (section 2),
  merging (section 3).
