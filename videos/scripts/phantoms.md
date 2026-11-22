# Booked twice: when the row you need to lock doesn't exist yet

- Slug / scene: `phantoms`, `videos/scenes/phantoms.py:Phantoms`
- Lesson: `txn-03`, section 1, "The booking that doesn't exist yet: phantoms" (the guardrail previews section 2)
- Audience / level: a complete newcomer. Has booked a meeting room; met the row lock in the lost-update video, but
  the video says what it does again.
- Length: 4:04 (~700 words of narration at Kokoro's ~180 words a minute, plus two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=90` (the race finished: both bars on room 4's day, the red overlap, both lanes full)
- The learner's real question: the app checked that the room was free, and even locked what it found. How did two
  teams still book it?
- Misconception to steelman and break: "FOR UPDATE on the check stops the clash, as it stopped the lost update".
  Broken by the prediction: neither check waits, because both found zero rows and a lock goes only on rows found.
- Concept chain: a booking is a row → the check asks for overlapping rows and locks them → it finds none, so it locks
  none, and both insert (phantom) → Repeatable Read doesn't help → give the clash a real row (room 4's row) or a rule
  the database checks (exclusion constraint) (hardest last)
- Analogy family: the row lock as a very literal guard, told to stand next to every booking between twelve and one;
  the fix gives him a real door to stand at (room 4's own row).
- Open loops: "how did this get through?" planted in scene 1 → answered in scene 7; the "fix that stopped the lost
  update" planted in scene 1 → broken in scene 3.
- Assumptions: times and names are the lesson's (room 4, risk team 09:00-10:00, settlement review 12:00-13:00, card
  ops 12:30-13:30, 11:58, 23P01). The check SQL is the lesson's, shortened with `:my_slot`. The "ivy" username in
  the check question is made up; the lesson lists "a username or an email address that must be unique".

## The one picture

Top: room 4's day as a time axis from 09:00 to 15:00 (grey), with bookings as bars: the risk team (grey), settlement
review (blue, upper track), card ops (purple, lower track). A check is a tinted rectangle over its time range. Below:
two lanes, settlement review on the left (blue) and card ops on the right (purple), steps as chips in time slots,
and a grey time arrow between them. Red marks the overlap; gold is the fix; yellow is the prediction and waiting.

## Scene 1 · Both at the door · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: Picture the office of the company behind a coffee-shop payments app. It has one small meeting room, room 4. At
11:58, two teams open the booking app. One books the room from 12:00 to 13:00. The other, from 12:30 to 13:30. Both
see a free room. Both get Booked. And at 12:30, both teams are at the door. The app checked before it booked. It even
locked what it found, the fix that stopped the lost update. So how did this get through?

SCREEN: Title card. A door marked "room 4"; "11:58"; the two teams with their times; two green "Booked" chips; the
clock turns to 12:30 and two figures meet at the door; "how did this get through?".

## Scene 2 · The room as rows · 0:30–1:05 · [FAMILIAR] [SHRINK]

VO: Let's look at the room the way the database does. Each booking is a row in a table, with the room and a time
range. Room 4 has one booking this morning: the risk team, nine to ten. Before it books, the app asks: is there any
booking of room 4 that overlaps my slot? And it adds FOR UPDATE, which puts a row lock on every row the question
finds. A row lock makes any other writer of that row wait. That's what stopped the lost update.

SCREEN: The time axis draws in; the risk team's bar. The check: `SELECT booking_id FROM room_bookings WHERE room_id
= 4 AND during && :my_slot FOR UPDATE;` with a yellow padlock beside `FOR UPDATE`.

## Scene 3 · The race, and the guess · 1:05–1:55 · [PREDICT] [PAUSE] [SHOW] [BREAK] [JOKE:release]

VO: So the settlement review team checks 12:00 to 13:00. A moment later, card ops checks 12:30 to 13:30. Does card
ops' check wait for the first team? Pause and guess.

(three seconds)

No. Both checks find zero rows. And a lock goes on the rows a check found, so both lock nothing. Neither can see the
other's booking until it commits. So both insert, both commit, and 12:30 to 13:00 is booked twice. Well. The lock did
everything it was asked. It was asked to guard nothing.

SCREEN: Lanes and the time arrow. Two tinted check rectangles on the axis; countdown; "0 rows" in each; the chips
become "check: 0 rows, 0 locks"; "no row found, no row locked: nobody waits". INSERTs bring two faint bars, COMMITs
make them solid; a red overlap from 12:30 to 13:00 and "12:30-13:00 booked twice".

## Scene 4 · A very literal guard · 1:55–2:40 · [ANALOGY] [MAP] [JOKE:is-the-explanation]

VO: Think of the row lock as a very literal guard. You say: stand next to every booking between twelve and one. He
looks at the sheet, finds none, and stands next to... nothing. The other team hires the same guard, with the same
orders. Two guards, both guarding empty space, and two teams walk in. Map it back. The guard is the row lock. The
bookings he can stand next to are rows that exist. The empty slot is a search that found nothing. A guard needs
something to stand by.

SCREEN: A blue guard over the empty slot, his orders in gold; he looks left and right, a yellow "?". A purple guard
joins; both bars arrive. The map, line by line: the guard = the row lock; what he can stand by = rows that exist
(the risk team's bar pulses); the empty slot = a search that found nothing. Caption "a lock can only hold a row that
is already there".

## Scene 5 · The name · 2:40–3:25 · [NAME] [BREAK] [GUARDRAIL]

VO: The second booking has a name: a phantom. It's a row that matches a search, but another transaction wrote it
after the search ran. Both the check and the write are about a row that doesn't exist yet, so the clash has nothing
to hold on to. And the stricter setting, Repeatable Read, doesn't save us. Its snapshot hides the other booking from
your reads. It doesn't stop the other team from inserting it. The same shape turns up wherever a rule says no row
like this may exist yet: a username that must be unique, one payout per shop per day, a gift card spent twice. Each
checks that something is missing, then inserts it.

SCREEN: "phantom" in red beside card ops' bar; the definition as a caption. The Repeatable Read card (the bar fades
while "hides the other booking", returns on "doesn't stop"). Three gold chips, and "check that it's missing, then
insert it".

## Scene 6 · Give the clash something real · 3:25–4:15 · [GUARDRAIL] [ANALOGY]

VO: So give the guard something real. Room 4 has its own row, in the rooms table, and it always exists. Lock that
first, then check. Now card ops waits at the room's row. When the first team commits, card ops checks again, sees
12:00 to 13:00, and doesn't book. Better still, write the rule into the table: no two bookings of one room may
overlap. PostgreSQL calls this an exclusion constraint, and it checks every booking, committed or not. The second
insert waits for the first, then fails with error 23P01. There's no check query to get wrong. Rule of thumb: if the
rule fits a constraint, make it one. A lock on a parent row is next best, as long as every path through the code
remembers to take it.

SCREEN: A gold box "rooms: row 4, always there" with a blue padlock; card ops "lock room 4: waits"; settlement
review checks, inserts and commits; the padlock turns purple; card ops "check: 1 row, so no booking". Then the
lesson's `EXCLUDE USING gist (room_id WITH =, during WITH &&)`; card ops' faint bar gets a red cross and "INSERT
12:30-13:30: ERROR 23P01". Captions with the rule of thumb.

## Scene 7 · The moral, and a check · 4:15–4:45 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So how did two teams book one room? Each locked what its check found, and its check found nothing. A lock can
only hold a row that's there. One quick check. A sign-up page checks that no user named ivy exists, with FOR UPDATE,
then inserts her. Two people sign up as ivy in the same second. What stops a duplicate? Pause and think.

(three seconds)

Nothing, yet. The check finds no row, so it locks no row. A unique constraint on the username stops it.

SCREEN: The double booking again, the two empty checks, "a lock can only hold a row that's there". A box "users
named ivy: none yet" and two chips "check ivy: 0 rows, INSERT"; countdown; "users named ivy: 2" in red, then
`UNIQUE (username)`, the second insert in red, "users named ivy: 1" in green. The moral stays on the last frame.

---

### Beat check

- Opens with QUESTION (scene 1), from a felt situation (two teams at one door).
- FAMILIAR (scene 2): the row lock that fixed the lost update, restated in plain words.
- PREDICT with PAUSE (scenes 3 and 7), SHOW right after each.
- BREAK: the steelmanned "the lock stops it" (scene 3), and Repeatable Read (scene 5).
- ANALOGY + MAP (scene 4), each part mapped out loud; the analogy returns for the fix (scene 6).
- NAME after the SHOW: phantom (scene 5), exclusion constraint (scene 6).
- GUARDRAIL (scene 6) and MORAL (scene 7) last. Light moments: "asked to guard nothing" (~1:52), the literal guard
  (~2:05).

### Accuracy notes for the producer

- The lesson's Try it: both checks print `(0 rows)` at once and B never waits; both INSERTs and COMMITs succeed, and
  bookings 2 and 3 overlap from 12:30 to 13:00. The video shows the same.
- "Neither can see the other's booking until it commits" is the lesson's wording for why the second check finds
  nothing (Read Committed; the insert is uncommitted).
- The room-row lock: the lesson's section 2 says the second booker waits on `SELECT name FROM rooms WHERE room_id = 4
  FOR UPDATE`, and its count, a new statement with a fresh snapshot, sees the first booking. The video says "checks
  again, sees 12:00 to 13:00, and doesn't book".
- The exclusion constraint: section 2's Try it shows the second INSERT waiting for the first transaction and failing
  with 23P01 when it commits (on its own 15:00 and 15:30 bookings; the video uses the race's times). It needs the
  `btree_gist` extension, which the course database installs; the video leaves that out.
- Left to the lesson: write skew and the doctors, slot tables, PostgreSQL 18's `WITHOUT OVERLAPS`, predicate and
  next-key locks, and Serializable.
- Clock times are spoken the way people say them ("twelve thirty", "one") through `SAY` rules; captions keep the
  24-hour times, so check_audio lists those as differences.
