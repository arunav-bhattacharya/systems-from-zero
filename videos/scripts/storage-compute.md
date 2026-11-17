# Where the payments live: storage apart from compute, and six copies in three zones

- Slug / scene: `storage-compute`, `videos/scenes/storage_compute.py:StorageCompute`
- Lesson: `found-05`, section 2, "The cloud brings back the shared disk: storage apart from compute"
- Audience / level: a complete newcomer. Knows a computer has a disk; knows nothing about the cloud, databases,
  logs, pages or replication.
- Length: 4:44 (~730 words of narration at Kokoro's ~180 words a minute, plus two pauses and the builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=214` (a zone and a disk down: three copies left, write needs 4 crossed, read needs 3 ticked)
- The learner's real question: if the rented computer, and its disk, can vanish at any moment, where does the data
  live? And if it lives somewhere else, isn't every write a slow trip?
- Misconception to steelman and break: "durable means many copies of everything, so mirror the whole disk". Mirrored
  MySQL does that and pays 7.4 I/Os per transaction; sending only the log notes and letting storage build the pages
  does 35 times the transactions at 0.95 I/Os each, with six copies. A second break: "losing three of six copies
  must lose data", broken by the overlap of read and write quorums.
- Concept chain: a computer's own disk dies with it → a network disk survives, but every read and write is a trip
  → a database writes notes and pages, and a mirror doubles every trip → send only the notes; storage builds the
  pages (the log is the database) → six copies, write 4, read 3 → a zone and a disk fail and nothing saved is lost
  (hardest last)
- Analogy family: the lesson's café kitchen and a central warehouse. The kitchen's shelf (what burns with the
  kitchen), a warehouse down the road (a durable copy, a trip per fetch), slips saying "used two eggs" (redo log
  records), warehouse clerks who update their own stock pages, three warehouse buildings (zones).
- Open loops: "where should a database keep the payments?" planted in scene 1 → answered in scene 9; the shelf in
  scene 2 → "only a cache" in scenes 4 and 9; the burning kitchen in scene 2 → the check question.
- Assumptions: numbers are the lesson's (Aurora paper, 2017: 30-minute write-only test, 780,000 vs 27,378,000
  transactions, 7.4 vs 0.95 I/Os each, 35 times and 7.7 times; 10 GB segments, six copies, two per zone, write
  quorum 4, read quorum 3; about 10 seconds to re-copy a segment over 10 Gbit/s). "Used two eggs" is invented for
  the analogy.

## The one picture

Left: the kitchen, later the database instance (blue), holding its shelf, later its cache (gold). Right: the
warehouse, later the storage machines (teal), split by dashed lines into three zones, with copies a1 to c2. A grey
arrow between them is the road, later the network. Chips travel along it: blue notes and slips (log records), gold
8 KB pages, white reads and writes. A counter above the road shows I/Os per transaction. Under the warehouse, a
status line: copies left, write needs 4, read needs 3, with ticks and crosses. Red means failed.

## Scene 1 · The symptom · 0:00–0:20 · [QUESTION] [LOOP-PLANT]

VO: A payments company rents a computer in the cloud to run its database. That computer comes with its own disk,
and the day's payments are written there. Then the computer fails, or the cloud moves it to another machine. Its disk
goes with it. So where should a database keep the payments it must never lose?

SCREEN: A blue box "rented computer" with a gold "its own disk: today's payments" inside. It turns red with a cross;
the disk fades. A "?".

## Scene 2 · The kitchen and the warehouse · 0:20–1:00 · [FAMILIAR] [ANALOGY] [JOKE:pivot]

VO: Picture the café kitchen. Its shelf holds the ingredients. If the kitchen burns down, the shelf goes with it.
That's the rented computer and its own disk. So keep the stock in a warehouse down the road. A fire in the kitchen
loses nothing. In the cloud, that's a network disk. It lives on the provider's storage machines, and it survives. The
catch: every fetch is now a trip down the road. Every read or write is a call over the network.

SCREEN: The box becomes "kitchen" with a "shelf: ingredients". A cross on "burns down". A teal warehouse appears on
the right with one copy (a1), joined by an arrow "down the road", which becomes "network disk" and "the network". A
white "read" chip and a "write" chip travel the road to a1.

## Scene 3 · A lot of trips · 1:00–1:45 · [PAIN] [SHOW] [WISH]

VO: And a database makes a lot of trips. It saves each change twice. First a short note at the end of its log, a file
it only adds to, so a crash loses nothing. Later, the changed pages, the blocks its tables live in, often 8 kilobytes
each. Now keep a mirror in a second availability zone, a separate building with its own power and network. Every
trip happens twice. Amazon counted. A mirrored MySQL database, a popular free one, needed 7.4 reads or writes to
storage for each transaction. Each of those is called an I/O. Wouldn't it be nice to send just the short note?

SCREEN: A blue "note" chip and two gold "page 8 KB" chips travel to a1. Dashed zone lines and "zone a/b/c" appear,
with a mirror copy b1; notes and pages now go to both. Above the road: "I/Os per transaction: 7.4" (red). Captions.

## Scene 4 · Send only the slip · 1:45–2:50 · [ANALOGY] [MAP] [NAME]

VO: Back to the kitchen. The cook sends the warehouse only a slip: used two eggs. The warehouse clerks update their own
stock pages from the slips. The kitchen keeps only today's ingredients on its shelf. Now map it. The kitchen is the
database instance, the computer doing the work, called compute. The warehouse is a fleet of storage machines. The
slip is a redo log record, a short note saying what a change did. The storage machines build the 8 kilobyte pages
themselves, so pages never cross the network on a write. And the shelf is only a cache, a quick copy that can be
refilled. This is called separating storage from compute. Amazon's Aurora, a cloud database built from MySQL, sums
it up in one line: the log is the database.

SCREEN: Labels return to the café words; two blue "slip" chips go to a1 and b1, which glow; the shelf now says
"today's ingredients". Then each label maps as it's said: "database: compute", "storage machines", "the network", a
"redo record" chip, gold "page" chips appearing under the copies (built there), the shelf becoming "cache: a quick
copy". Captions "separating storage from compute", "Aurora: the log is the database".

## Scene 5 · The numbers · 2:50–3:15 · [SHOW] [JOKE:reward]

VO: Same 30-minute test, same size of machine. Mirrored MySQL: 780,000 transactions, at 7.4 I/Os each. Aurora: 27
million, at 0.95 I/Os each. That's 35 times the transactions, with 7.7 times fewer I/Os each. And Aurora was keeping
six copies of the data. More breakfasts, fewer trips.

SCREEN: Captions with both results; the counter becomes "0.95" (green). Four more copies appear: six in all.

## Scene 6 · Six copies and quorums · 3:15–3:45 · [SHRINK] [NAME]

VO: Six copies, kept how? Aurora cuts the data into 10-gigabyte segments. Each segment has six copies, two in each of
three zones. A write counts once four copies have it. A read needs three. Those numbers are quorums: how many copies
must answer before an operation counts.

SCREEN: "one 10 GB segment: six copies, two in each of three zones"; the copies glow in turn; blue "redo" chips go to
all six; the status line "copies left: 6, write needs 4 ✓, read needs 3 ✓".

## Scene 7 · A zone fails, then a disk · 3:45–4:40 · [PREDICT] [PAUSE] [SHOW] [BREAK]

VO: Now a whole zone fails. Its power, its network, or a bad change that hits every machine in it. Two copies gone.
Can we still write? Pause and guess.

(three seconds)

Yes. Four copies are left, and a write needs four. Then, while that zone is down, a disk in zone c dies. Three left.
Writes stop. Reads still work. Did we lose a saved write? No. Every saved write reached four copies. Any three copies
include at least one of those four, because three plus four is more than six. Meanwhile, the storage fleet copies the
segment onto a new machine. Ten gigabytes take about 10 seconds. That's why the segments are small. Aurora can't stop
disks failing, but it can repair them fast.

SCREEN: a1 and a2 turn red with crosses; "write? read?"; countdown; "copies left: 4" with two ticks, and redo chips
reach the four. c2 fails: "copies left: 3", a cross by write, a tick by read. The three survivors glow green with the
caption "every saved write: on 4 copies. any 3 copies overlap them: 3 + 4 > 6". A new green a1 appears and dots copy
into it from b1: "10 GB over a 10 Gbit/s link: about 10 seconds"; the status returns to 4.

## Scene 8 · The price · 4:40–4:55 · [GUARDRAIL]

VO: The price is a network trip on every write. Newer designs go further. They keep the durable copy in object
storage, cheap file storage like Amazon S3, to save on fees for bytes that cross between zones. They pay with slower
writes.

SCREEN: The road glows red: "the price: a network trip on every write"; then "newer designs: the durable copy in
object storage, like Amazon S3" and "cheaper across zones, slower writes".

## Scene 9 · The moral, and a check · 4:55–5:30 · [MORAL] [PRINCIPLE] [RECAP] [PREDICT] [PAUSE] [LOOP-PAYOFF]

VO: So where should the payments live? Not on a computer that can vanish. In the warehouse: six copies, in three
buildings. The kitchen's shelf is only a cache. Where is the durable copy, and what is only a cache? Ask that first,
of any system.

One quick check. The database instance crashes: the kitchen burns down. What's lost? Pause and think.

(three seconds)

Only the shelf, a cache. Every saved change is in the warehouse. A new instance starts, and refills its shelf.

SCREEN: The warehouse glows, then the shelf. The moral in yellow. For the check the instance turns red with a cross;
countdown; the shelf fades; "only the cache. every saved change is in storage."; the instance turns blue again and a
page chip travels back to refill the shelf. The moral returns.

---

### Beat check

- Opens with QUESTION (scene 1) from a felt loss (the computer and its disk vanish).
- FAMILIAR + ANALOGY (scene 2) before the technical words; PAIN and WISH in scene 3; MAP said out loud (scene 4).
- PREDICT with PAUSE twice (the zone failure; the check); SHOW right after each.
- BREAK: mirroring everything (7.4 I/Os) beaten by sending notes (scenes 3 to 5); "three of six left must lose data"
  broken by the quorum overlap (scene 7).
- NAME after the SHOW: network disk (2), I/O and availability zone (3), compute, redo log record, cache, separating
  storage from compute, "the log is the database" (4), quorum (6).
- GUARDRAIL (scene 8) and MORAL (scene 9) come last. Light moments: the burning kitchen (0:35), "more breakfasts,
  fewer trips" (3:10).

### Accuracy notes for the producer

- Aurora numbers from Verbitski et al. (SIGMOD 2017) as quoted in the lesson: same instance size, 30-minute
  write-only test; mirrored MySQL 780,000 transactions at 7.4 I/Os each; Aurora 27,378,000 at 0.95; "35 times" and
  "7.7 times" are the lesson's figures.
- The video shows a note plus two pages for one change, then the same to a mirror. That's a picture of "many
  trips", not the paper's count of 7.4.
- Six copies of each 10 GB segment, two per availability zone; write quorum 4, read quorum 3; a zone plus one more
  copy can fail and reads still work with no saved write lost; re-copying a 10 GB segment takes about 10 seconds
  over 10 Gbit/s. The lesson's lab checks the quorums by brute force.
- "A new instance refills its shelf" is the lesson's "a kitchen's shelf is only a cache, a quick copy that can be
  refilled". The details of how a new Aurora instance starts are left out.
- Object storage and the cross-zone fee ($0.02 per GiB on AWS) are from the lesson's KIP-1150 paragraph; the video
  doesn't name Kafka.
- "Used two eggs" is an invented slip for the analogy.
