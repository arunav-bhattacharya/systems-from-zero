# Which number is true? Trust the record, rebuild the copy

- Slug / scene: `derived-data`, `videos/scenes/derived_data.py:DerivedData`
- Lesson: `found-01`, section 1, "Which data is the truth: systems of record and derived data"
- Audience / level: a complete newcomer. Can read a little code; knows nothing about files on servers, databases,
  indexes or caches.
- Length: 5:02 (~830 words of narration; the Kokoro voice speaks about 180 words a minute, and the pauses,
  guesses and silent builds bring the pace down to about 165)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=238.2` (just after the replay: every copy green and ticked, the key picture)
- The learner's real question: the app shows a number, so isn't that number the data? When two numbers disagree,
  which one is true, and how do you fix the other?
- Misconception to steelman and break: "the number on the screen is the truth, so fix it by typing the right
  number over it". Broken twice: where did the right number come from (the notebook), and followed all the way,
  the idea says to rub the refund out of the notebook, which erases a customer's money.
- Concept chain: one notebook of facts → copies worked out from it to make questions fast → a copy can be thrown
  away and rebuilt, the notebook can't (system of record, derived data) → a copy goes stale when an update is
  lost → fix it by replaying the record, never by retyping (hardest last)
- Analogy family: the café's paper notebook by the till (the record), the index at the back and the sticky note
  with the balance (the copies), coffee spilled on the sticky note (a lost copy, rebuilt by adding up again)
- Open loops: "type 9.00 over it" planted in scene 1 → tested and broken in scene 6; "which one is true?"
  planted in scene 1 → answered in scene 9; the coffee rebuild in scene 2 → called back as the replay in scene 7
- Snapshots / chapters: the symptom, the notebook, the app, the test, the lost message, the tempting fix, the
  replay, two habits, the moral
- Assumptions: numbers are the lesson's (40.00 and 9.00 at the café, a 40.00 refund; 49.00 shown, 9.00 true).
  Card endings 4417 and 8802 are made up for the picture. The video shows only the café's three money movements
  (see the accuracy notes).

## The one picture

Left: the notebook (blue, the record), lines numbered 1 to 3, new facts drop in from above. Right column: the index
(teal, top) and the sticky note (teal, bottom), each fed by an arrow from the notebook. Far right: the owner's
phone, fed by an arrow from the sticky note. Yellow dots are updates moving along the arrows; red means wrong or
lost; green means checked against the record; purple means typed by hand. Same places and colours from start to
end. At most six things on screen.

## Scene 1 · The symptom · 0:00–0:33 · [QUESTION] [LOOP-PLANT]

VO: Picture a busy café. In the morning, the owner opens the café's app on her phone. Her balance, the money her
card sales have brought in, says 49.00. But an hour ago, she refunded a 40.00 order. So the balance should be
9.00. Same app, same payments, two answers. Which one is true? And how do you fix the other one?

The tempting fix is to type 9.00 over the 49.00. It's the number everyone sees, so it feels like the real one.
Hold that thought.

SCREEN: Title card. A large phone in the centre: "café app, balance 49.00". A gold refund slip on the left
(refund, -40.00, an hour ago); "should be 9.00" in green on the right. A big "?" above. On "type 9.00 over", the
phone's number turns into a purple 9.00 with a blinking caret, then back to 49.00.

NOTE: The phone then shrinks into its place on the far right and dims while we leave the app.

## Scene 2 · The notebook · 0:33–1:13 · [FAMILIAR] [ANALOGY] [JOKE:pivot]

VO: To see which is true, picture the café without the app. It keeps a paper notebook by the till. Every sale goes
on the next empty line: which card paid, and how much. Nothing is ever rubbed out.

Two helpers grow around it. At the back, an index: each card, and the lines it's on. And by the till, a sticky
note with the balance, so nobody adds up the notebook every time someone asks.

Now, this is a café. Sooner or later, coffee lands on the sticky note. Does the owner panic? No. She adds up the
notebook and writes a new note. She'd never do it the other way round, and change the notebook to match the note.

SCREEN: The notebook draws in. Two sales drop in from above onto lines 1 and 2 (card 4417, 40.00; card 8802,
9.00). The index grows from an arrow (4417: line 1; 8802: line 2). The sticky note grows from a second arrow:
balance 49.00. A brown coffee blot lands on it. The note is wiped, a yellow cursor steps down lines 1 and 2, and the
note counts 40.00, then 49.00. A red arrow from the note back to the notebook, crossed out.

NOTE: The coffee is the light moment, and it is the lesson: a copy is disposable because the record can make it
again. The crossed-out arrow carries the rule "never the other way round".

## Scene 3 · The app works the same way · 1:13–1:41 · [MAP]

VO: The app works the same way. The program behind the card reader adds each payment as a line at the end of a
file. That file is the notebook, and the app keeps an index too. And the balance on her phone? The app doesn't add
up the file each time. It reads a saved answer, its sticky note. A saved answer like that is called a cache.

Why keep copies at all? Adding up millions of lines every time is slow. Each copy makes one question fast.

SCREEN: The phone lights up again. "the payments file" appears in the notebook's header; the index glows; an arrow
grows from the sticky note to the phone and a dot carries 49.00 along it; "the cache" appears under the note.
Captions: "why keep copies at all?", "adding up millions of lines, every time: slow", then "each copy makes one
question fast".

NOTE: Each mapping is said out loud as its label appears: file = notebook, index = index, cache = sticky note,
the app's screen reads the cache.

## Scene 4 · The test, and the names · 1:41–2:23 · [SHRINK] [PREDICT] [PAUSE] [SHOW] [NAME]

VO: So which of these is the truth? Here's a test. If a box were thrown away, could we get it back? Pause and
guess.

(three seconds)

The index: yes. Read the notebook again. The sticky note: yes. We saw the owner do it. The notebook: no. The
note knows one number, not which payments made it. Lose the notebook, and those payments are gone.

The notebook is the system of record, also called the source of truth. Each fact is written there first, and once.
When anything disagrees with it, the record wins. The index and the cache are derived data: worked out from the
record, so they can be thrown away and worked out again.

SCREEN: A yellow "?" beside each of the three boxes, and a countdown bar during the pause. The index's "?" becomes
a green tick while its entries vanish and come back along the arrow; the note's becomes a tick; the notebook's
becomes a red cross while its lines fade out. Then the lines return, "system of record" appears under the notebook
in blue and "derived data" above the copies in teal.

NOTE: The names come only after the viewer has sorted the boxes themselves.

## Scene 5 · The lost message · 2:23–3:01 · [ANALOGY] [BREAK of the analogy] [SHOW] [JOKE:release]

VO: So how did the app get 49.00? Here the café picture stops working. The owner updated her note by hand. The
program updates its copies on its own, thousands of times a second.

Watch the refund. It goes into the file first, as a new line. Then the program updates each copy. The index adds
line 3. The cache gets a short message: forget your saved balance. But that message got lost on the way. So the
cache kept handing out 49.00.

A copy that missed the newest record is called stale. And nothing on the screen says so. A stale 49.00 looks just
as sure of itself as 9.00.

SCREEN: Captions "where the café picture stops working", "the owner: by hand, now and then", "the program: on its
own, thousands of times a second" while a stream of dots runs along all three arrows. The refund drops in as line
3 (gold, card 4417, refund, -40.00). A dot reaches the index: "4417: lines 1, 3". A second dot, labelled
"forget", sets off towards the note, stops halfway and becomes a red cross with "lost". The note's outline turns
red and its label becomes "the cache: stale". The phone's 49.00 pulses.

NOTE: Where the analogy breaks is said out loud: by hand versus automatic, so the danger moves to an update lost on
the way. The light line comes right after the mechanism, never inside it.

## Scene 6 · The tempting fix, tested · 3:01–3:33 · [BREAK] [LOOP-PAYOFF] [JOKE:soften]

VO: Now, the tempting fix. Type 9.00 over the note. To be fair, the phone now shows the right number.

But where did you get 9.00? You added up the notebook. So the notebook was the judge all along. Typing it in is a
rebuild done by hand, for the one number you happened to spot.

And follow the idea underneath, that the screen is the truth. Then the notebook must be wrong, so rub out the
refund. Now everything agrees on 49.00, and a customer's refund has vanished.

Well... that's not the fix we wanted.

SCREEN: The note and the phone show a purple, hand-typed 9.00. Caption: "40.00 + 9.00 - 40.00 = 9.00, added up from
the notebook"; the notebook glows; the red "lost" cross pulses (still lost). Then both numbers go back to 49.00,
line 3 is struck through and fades, green ticks appear by the notebook, the note and the phone, and a red line
reads "a customer's refund: gone".

NOTE: Be fair first: typing does fix the screen today. The break is the steelmanned idea run to its end.

## Scene 7 · Rebuild from the record · 3:33–3:58 · [SHOW] [NAME] [LOOP-PAYOFF]

VO: Let's undo that, and do what the owner did after the coffee. Throw the copies away. Nothing is lost, because the
file hasn't changed.

Read the file from the first line, in order, and work each copy out again. 40.00. 49.00. And the refund: 9.00.

That's called replaying the record. The rebuild didn't need to know what went wrong, and nobody typed a number.

SCREEN: Line 3 comes back. The index entries, the note's number, the phone's number and the red cross all go. The
yellow cursor steps down lines 1, 2 and 3; dots run to both copies each time; the index refills, and the note counts
40.00, 49.00, 9.00 (green). A dot carries 9.00 to the phone (green). Ticks on the index, the note and the phone.

## Scene 8 · Two habits, and a cost · 3:58–4:21 · [GUARDRAIL]

VO: Two habits keep this safe. Write the record first and the copies second. If the power cuts out in between, a
copy is only behind, and a replay catches it up. And never rub out a line. A rebuild is only as good as the record
it reads.

One cost: a rebuild reads the whole record. Three lines take no time. Years of payments can take hours.

SCREEN: Captions "1. the record first, then the copies" (the notebook glows, then dots run to the copies), "a power
cut in between leaves a copy behind; a replay catches it up" and "2. never rub out a line" (the lines glow in order). Then "the cost: a rebuild reads every line" while the cursor
sweeps the lines.

## Scene 9 · The moral, and a check · 4:21–5:01 · [MORAL] [RECAP] [PRINCIPLE] [JOKE:reward] [PREDICT] [PAUSE]

VO: So, 49.00 or 9.00? Every copy is worked out from the notebook, and the notebook says 9.00. It wins, even when
the sticky note has nicer handwriting.

A copy that disagrees with the record is wrong. Rebuild it, don't retype it. And of any data you meet, ask: is this
where the fact is decided, or a copy of it?

One quick check. The index says a card is on line 5, but the notebook has no line 5. Which one is wrong, and what do
you do? Pause and think.

(three seconds)

The index is wrong. Throw it away, and replay the notebook.

SCREEN: Caption "49.00 or 9.00?"; dots run from the notebook to every copy; the notebook and the phone's 9.00 glow;
"the notebook says 9.00, and the notebook wins"; the sticky note wiggles on "nicer handwriting". Then "rebuild,
don't retype" and "is this where the fact is decided, or a copy of it?". For the check, the index's 8802 entry turns red,
"line 5", and a dashed red slot marks line 5 of the notebook as empty; countdown bar. Then the index is wiped and
replayed: "8802: line 2" again, with a tick, and "rebuild, don't retype" stays on the last frame.

---

### Beat check

- Opens with QUESTION (scene 1), from a felt symptom (the wrong balance).
- FAMILIAR + ANALOGY (scene 2) before any technical word; MAP said out loud (scene 3).
- PREDICT with PAUSE (scene 4, and the check in scene 9); SHOW right after each.
- BREAK: the analogy's limit (scene 5) and the wrong model run to its end (scene 6).
- NAME after the first SHOW: cache (scene 3, after the sticky note), system of record and derived data (scene 4,
  after the viewer sorts the boxes), stale (scene 5), replaying (scene 7).
- GUARDRAIL (scene 8) and MORAL (scene 9) come last. Light moments: the coffee (0:59), the stale number that looks
  sure of itself (2:57), "that's not the fix we wanted" (3:30), the nicer handwriting (4:28).
- Open loops paid off by name: "the tempting fix" (scene 6), "49.00 or 9.00?" (scene 9), "what the owner did after
  the coffee" (scene 7).

### Accuracy notes for the producer

- The lesson's stepper and demo keep seven records: each payment is written twice (AUTHORIZED, then CAPTURED), and a
  bookshop payment (`pay-2`, 12.50) sits between the café's two. The video shows only the café's three money
  movements (40.00, 9.00, the 40.00 refund) as three notebook lines. The balances are the same: 49.00 before the
  refund, 9.00 after.
- The lesson's index maps a payment number to where its record is (or its latest status in the stepper). The video's
  index is "by card", one of the reshapes the section names ("by payment number, by shop and day, by card"). The
  card endings 4417 and 8802 are invented.
- The lesson's program applies each new record to the index and tells the cache to forget the shop's saved balance;
  only that message is lost. The video shows the same thing.
- After a rebuild, the lesson's cache starts empty, and the first request adds up the log and saves 9.00. The video
  shows that adding-up as a running total during the replay.
- "Thousands of times a second" and "years of payments can take hours" are the lesson's illustrative figures; real
  rebuild times depend on the size of the record and the machine.
- The video says "in order" but doesn't show why: a sum doesn't care about order. The lesson's case where order
  matters (a refund replayed before its capture leaves the index saying CAPTURED) is left to the stepper.
- Left to the lesson: views and materialized views, PostgreSQL or Kafka as the system of record, and the cost of a
  copy being missing until its rebuild finishes.
- Amounts are spoken as people say them ("forty-nine") through a `SAY` rule; captions keep "49.00".
