# One fact, many copies: why a table should say things once

- Slug / scene: `normalization`, `videos/scenes/normalization.py:Normalization`
- Lesson: `sql-02`, section 0, "Repeated facts drift apart"
- Audience / level: a complete newcomer. Can read a little code; has never designed a table.
- Length: 5:08 (~800 words of narration at the Kokoro voice's ~180 words a minute, plus two guesses and the
  silent moves)
- Poster: `POSTER=262` (all three tables, payment 15 followed to Volt Electronics and 5732: the join path)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: the file has every detail on every row, which is the quickest way to load it. So
  what's actually wrong with that?
- Misconception to steelman and break: "the copies only disagree when someone is careless, so be careful and
  change every copy". Broken twice: careful is what the barista was, 199 times out of 200; and no amount of care
  lets you write down category 5814 before a payment arrives, or keep Quick Bite's category after deleting its only
  payment.
- Concept chain: one fact copied onto many rows → copies drift (update anomaly) → a fact can't exist on its own
  (insert anomaly) → deleting one fact deletes another (delete anomaly) → give each fact one home and point at it
  (a key) → normalization → the price is a join (hardest last)
- Analogy family: the lesson's café order book. Every line repeats the customer's name and phone number (a row
  repeating a fact); the fix is a box of customer cards, one per customer, with each line saying "customer 17" (a
  table of its own, pointed at by its key).
- Open loops: "which number is right?" planted in scene 1 → "which spelling is right?" in scene 3 → answered in
  scene 7 (the question can't come up again).
- Assumptions: the ten rows and five columns are the lesson's `payments_export` output exactly. The café lines
  (Ana, the 555 numbers, the drinks and prices) are made up for the picture. The split tables are drawn with the
  course schema's names, `merchants (name, mcc)` and `mcc_codes (mcc, description)`; the course's `merchants` also
  has an id, left out here because the file points by name.

## The one picture

Scene 1: the café's order book (blue notebook). From scene 2 on: the file's table `payments_export` (blue frame), ten
rows, columns `payment_id`, `customer_name`, `merchant_name`, `mcc`, `mcc_description`. Red outlines mark copies that
disagree; gold marks the repeated fact (Volt's category). In scene 5 the right-hand columns move out into two teal
tables, `mcc_codes` (bottom right) and `merchants` (top right): the café's card box. Arrows show what points at
what. Captions sit on one line at the bottom. At most six things change at once.

## Scene 1 · The order book · 0:00–0:35 · [FAMILIAR] [PAIN] [QUESTION] [JOKE:pivot] [LOOP-PLANT]

VO: Picture a café's old order book. For every order, the barista writes the customer's name, phone number, drink
and price on one line. It's quick, and on the first day it works perfectly.

Then a regular changes her phone number. Her number sits on 200 lines, and someone has to change all of them. They
change 199.

In an exam, 199 out of 200 is a great score. In a book of facts, it means the book now says two different things.
Which number is right? Nobody can tell.

SCREEN: The notebook draws in, five lines (four of them Ana's, with 555-0142). "her number is on 200 lines". A
yellow cursor steps down her lines and changes them to 555-0199, skipping one, which turns red. Caption "changed:
199 of 200". Then "two numbers for one person: which is right?"

NOTE: The exam line is the light moment, and it is the lesson: one missed copy is a contradiction, not a small error.

## Scene 2 · The same book, as a table · 0:35–1:20 · [MAP] [SHRINK]

VO: A database table can fall into the same trap. A table is like a spreadsheet: each row is one record, and each
column one fact about it.

A partner bank, another company that handles card payments for some of the same shops, sends a file of payments every
night. The quickest way to load it is to keep it as it arrives, with every detail on every row.

The mcc is the merchant category code: four digits the card companies give each shop, to say what kind of business it
is. Volt Electronics is in category 5732, electronics shops. This file says so four times in ten rows. A year of files
would say it about 50,000 times.

So the table is the order book, a row is a line, and Volt's category is her phone number: one fact, copied onto many
rows.

SCREEN: The book fades; the table builds row by row. Volt's four `5732` cells turn gold. Captions map each part as it
is said.

## Scene 3 · Spot the disagreements · 1:20–1:55 · [PREDICT] [PAUSE] [SHOW]

VO: Every copy is a chance to disagree, and this small file already disagrees with itself twice. Can you spot where?
Pause and look.

(three seconds)

Payment 17 spells Farid's surname with one d. Payment 18 spells it with two, and calls category 5732 Electronic
stores, without the s. So which spelling is right? The table can't tell you,
because nothing keeps the copies equal.

SCREEN: Countdown bar. Then red outlines on the names of 17 and 18, and on 18's description.

## Scene 4 · Be careful? · 1:55–3:00 · [BREAK] [NAME] [JOKE:release]

VO: You might be thinking: so be careful. Fix the bad rows, and next time, change every copy. To be fair, that does
fix today's mistake.

But careful is what the barista was, 199 times. A fact stored on many rows must be changed on all of them, and
missing one leaves the table contradicting itself. That's called an update anomaly. An anomaly is something wrong that
the design allows.

And care can't help with the other two. Category 5814 means fast food restaurants. Where would you write that down?
Every row is a payment, and no fast food payment has arrived yet. That's an insert anomaly.

Now payment 21, the only Quick Bite row. Say it turns out to be fraud, and you delete it. The fact that Quick Bite is
a restaurant goes with it. You came to remove one bad payment, and lost a restaurant. That's a delete anomaly.

Three kinds of damage, and one cause: the same fact, stored on many rows.

SCREEN: Captions name each anomaly in red. A dashed ghost row under the table: "? ? ? 5814 Fast food restaurants",
the question marks red. Row 21 is struck through and fades, then comes back. Volt's gold cells pulse on "one cause".

## Scene 5 · One home per fact · 3:00–4:15 · [WISH] [ANALOGY] [SHOW] [NAME]

VO: So what would the café do? Wouldn't it be nice to write her number down only once?

Keep one card per customer, in a little box, with her name and number. Each line in the book then says customer 17.
When her number changes, you change one card, and there's nothing to miss.

Let's do the same with the table, starting with the categories. Someone still has to decide which spelling is true,
but only once. The card companies' list says Electronics stores. Then each code and its description move to a table
of their own. Ten rows of copies become four. From now on, there's one place to fix, and nowhere for a second spelling
to live.

The shops get their own table too: each shop and its code, once. The payments keep only the shop's name, which points
at its row.

Each shop's name now appears once in its table, and so does each code. A column like that is called a key: its value
names exactly one row, so other rows can point at it.

And the other two problems are gone. 5814 gets its row today, with no payment needed. Delete payment 21, and Quick
Bite keeps its category.

Deciding which facts get a table of their own is called normalization. Farid's name needs the same cure: one row per
customer.

SCREEN: A strip under the table: a book line "customer 17 · latte · 3.50", an arrow, a teal card "customer 17 · Ana ·
555-0142" that flips once to 555-0199. Row 18's description becomes "Electronics stores" (green). The `mcc` and
description cells fly into `mcc_codes` and merge into four rows. The shop names and codes fly into `merchants` and
merge into four rows; the payments table narrows; arrows: payments → merchants → mcc_codes. Gold underlines and "key"
under `name` and `mcc`. `5814 | Fast food restaurants` joins `mcc_codes` (green). Row 21 dims while Quick Bite's
`merchants` row stays, then comes back.

## Scene 6 · The price · 4:15–4:40 · [GUARDRAIL]

VO: Splitting has a price. To print a payment with its category's description, the database now has to put three
tables back together. That's called a join, and it's the next lesson.

So split out the facts that belong to something else, like a shop or a category. Facts about the payment itself stay
on its row.

SCREEN: A yellow dot follows payment 15 → Volt Electronics → 5732 → Electronics stores. Captions.

## Scene 7 · The moral, and a check · 4:40–5:10 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, which spelling was right? Now the question can't come up again, because each fact has one home. Store each
fact once, keyed by what decides it, and point at it from everywhere else.

One quick check. The card companies rename category 7011, hotels, motels, resorts. In the old file, how many rows had
to change? And now? Pause and think.

(three seconds)

Three in that file: payments 13, 16 and 22, and more every night. Now, one row in the categories table.

SCREEN: "store each fact once, keyed by what decides it". For the check: the 7011 row outlined yellow, countdown;
then the three Harbor Hotel cells glow gold, and the 7011 row green with a tick.

---

### Beat check

- FAMILIAR + PAIN + QUESTION first (the order book, scene 1).
- MAP said out loud (scene 2): table = book, row = line, Volt's category = her phone number.
- PREDICT with PAUSE (scene 3, and the check in scene 7); SHOW right after each.
- BREAK: "be careful" steelmanned, then broken by the 199 and by the two anomalies care can't touch (scene 4).
- NAME after each is seen: update, insert and delete anomaly (scene 4); key and normalization (scene 5); join
  (scene 6).
- GUARDRAIL (scene 6): the price is a join; split out facts about something else. MORAL last.
- Light moments: the exam score (~0:25), "lost a restaurant" (~2:45), nowhere for a second spelling to live (~3:40).

### Accuracy notes for the producer

- The ten rows and their values are the lesson's `payments_export` output (seed: payment 17's name is overwritten to
  "Farid Hadad", payment 18's description to "Electronic stores"). No query output is shown.
- "Four times in ten rows" and "about 50,000 times" are the lesson's figures.
- The split follows the lesson's worked example: decide the true spelling from the card companies' list, fix it, then
  load one row per code (the worked example's table is `export_mcc`; the video uses the course's `mcc_codes`). The
  worked example also shows the primary key refusing a second spelling; the video says it in words only.
- `merchants` keyed by name follows the dependency `merchant_name → mcc`. The course's real `merchants` table has
  `merchant_id` as its key and payments point at it by id.
- 5814 "Fast food restaurants" is in the course's `mcc_codes`.
- Functional dependencies (how to find every such fact) are section 1; denormalization and its check are section 3,
  left out of the video.
- check_audio: 97.8% match at -16.2 LUFS; the differences are Whisper spellings (cafe's, 58 14, 7e11, quickbite).
  "Farid's" was heard as "farad" once and correctly in the other line, so no SAY rule was added.
- Codes are spoken in pairs ("fifty-seven thirty-two") through `SAY` rules; captions keep the digits.
