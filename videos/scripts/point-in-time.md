# 98% on paper, 62% at the till: training data that can't see the future

- Slug / scene: `point-in-time`, `videos/scenes/point_in_time.py:PointInTime`
- Lesson: `batch-14`, section 1, "Training data that can't see the future: the point-in-time join"
- Audience / level: a complete newcomer. Has had a "was this you?" text from a bank; doesn't know what a label, a
  feature, a chargeback, leakage or a join is.
- Length: 4:55 (~830 words at Kokoro's ~175 words a minute, plus two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=150`, the point-in-time pick (green arc back to the 10 October row, training row "= 0", red future shading)
- The learner's real question: the model caught 98% of fraud on last month's payments and 62% once it was live. Nothing
  in the code was wrong. Where did the difference go?
- Misconception to steelman and break: (1) "every fact in the training data is real history, so it's honest", broken
  by the newest row that counts the fraud's own chargeback; (2) "just take the newest row at or before the payment
  (by its as-of time)", broken by the 01:00 payment and the correction written on 15 October.
- Concept chain: labels and features → a nightly feature row on a timeline → the newest-row join puts the fraud's own
  chargeback into its training row (label leakage) → the timetable: judge by the board that was up that day → the
  point-in-time join → each row has two times, both must be at or before the payment (hardest last) → tools and their
  defaults
- Analogy family: the lesson's railway timetable. A passenger missed her 14:00 connection last Tuesday; you judge her
  choice by Tuesday's board, not today's. A correction pinned up on Friday, dated Tuesday, she couldn't have seen.
- Open loops: "where did 98 become 62?" planted in scene 1 → paid off in scene 8; the fire engine in scene 3 → called
  back in scene 9.
- Assumptions: the timeline, the card and its values are the lesson's stepper (rows at 02:00 as of midnight, fraud 10
  October 14:00, chargeback 12 October, 1 from 13 October, payment 13 October 01:00, correction of 12 October written
  15 October with value 1). The demo numbers are the Try it's (5,000 cards, 150,000 payments, 2,378 fraud, 98% and
  62% caught, 16% and 31% precision is left out). The rows for 14 to 16 October are the stepper's "newest row, value
  1" continued.

## The one picture

A timeline of 10 to 16 October across the middle. Above it, one small chip per night (the nightly feature row, grey
when 0, gold when 1). The payment as a red dashed line, the chargeback as a red marker. Below, one training row
("payment time → chargebacks_30d = ?"). Red shading over everything written after the payment. Green arcs for the
point-in-time pick, red arcs for the newest-row pick. A close-up strip of the night of 13 October appears under the
timeline for the second leak. Captions at the bottom.

## Scene 1 · 98 and 62 · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: Your bank sends you a text: "Was this you? 300.00 at a shop in Lisbon." Behind it is a program that learned from
past payments which ones turned out to be fraud. Picture the team that built one. Tested on last month's payments,
it caught 98 percent of the fraud. Then they switched it on, and it caught 62. Nothing in the code was wrong. So where
did the difference go? Hold that question.

SCREEN: Title card. A phone message bubble. Then "on last month's payments: 98%" (gold) and "live: 62%" (red), and a
"?".

## Scene 2 · Labels and features · 0:30–1:05 · [FAMILIAR] [SHRINK]

VO: A model like this learns from labels: past payments, each marked fraud or not. The mark comes weeks later, when a
chargeback arrives or doesn't. A chargeback is the bank taking the money back from the shop, after the cardholder
says, I didn't make this payment. It also learns from features: numbers about the card, like how many chargebacks it
had in the last 30 days. Every night at two, a job writes one row for the card, counted as of midnight. For now, the
count is 0.

SCREEN: Label line top left: "label: a payment on 10 Oct, 14:00, fraud". The timeline draws; feature title; chips
"0" for 10, 11, 12 October.

## Scene 3 · The easy join · 1:05–2:05 · [SHOW] [PREDICT] [PAUSE] [JOKE:is-the-explanation] [NAME]

VO: On 10 October at two in the afternoon, someone uses the card for fraud. Its chargeback arrives on the twelfth.
So from the thirteenth on, the nightly count is 1. Now build the training row for that fraud. The easy join takes the
card's newest row, the one that's there today. What number does the training row get? Pause and guess.

(three seconds)

1. And that 1 is the chargeback this very fraud caused. So the model learns that fraud comes with a chargeback
already on file. That's like learning to spot a fire by the fire engine parked outside. It works great on old
photos. It's no help while the fire is starting. This has a name: label leakage. Facts from after the decision
reach the data the model learns from.

SCREEN: Red dashed payment line, red marker on 12 October "its chargeback arrives", gold chips "1" from 13 to 16
October. The training row "10 Oct 14:00 → chargebacks_30d = ?"; countdown; a red arc to the newest chip; "= 1" in red;
red shading after the payment, "written after the payment". Caption "label leakage: facts from after the decision".

## Scene 4 · The timetable · 2:05–2:40 · [ANALOGY] [MAP]

VO: A railway makes the rule easy to see. A passenger says she missed her connection at 14:00 last Tuesday. To judge
whether she picked a sensible train, you'd look at the timetable that was on the board that Tuesday, not today's.
Today's board knows about changes she couldn't have seen. Map it. The passenger's Tuesday is the moment of the
payment. Each night's row is the board on that day. And the newest row is today's board.

SCREEN: Under the timeline, two small boards: "the board on Tuesday" (green) and "today's board: changes made since"
(red). Mapping captions, each with its part of the timeline glowing.

## Scene 5 · Look back from the payment · 2:40–3:05 · [SHOW] [NAME]

VO: So, look back from each label instead. Take the newest row that was there at the moment of the payment. For this
fraud, that's the 10 October row: 0. That's what the model would have read at the till. This is called a point in
time join.

SCREEN: The red arc goes; a green arc back to the 10 October chip; "= 0" in green; caption "point-in-time join: the
newest row that existed at the payment's moment".

## Scene 6 · Two times on every row · 3:05–4:00 · [BREAK] [SHOW] [LOOP-PAYOFF of the timetable]

VO: So far so good. But each row carries two times. One is the moment it's about: midnight. The other is when it was
written: two in the morning. Take a payment at one in the morning on 13 October. The 13 October row is about midnight,
which is earlier. But it wasn't written until two. At one, it didn't exist. So the join skips it, and takes the 12
October row: 0. It gets worse. On 15 October, a late chargeback report comes in, and the team works out 12 October
again: now 1. The correction is about the twelfth, but it was written on the fifteenth. Our one o'clock payment still
gets 0. It's a notice pinned to the board on Friday, dated Tuesday. The passenger never saw it.

SCREEN: A close-up strip "the night of 13 October": 00:00 "the row is about", 01:00 "payment", 02:00 "the row is
written". Training row "13 Oct 01:00 → = 0". A purple correction chip above 12 October "1, written 15 Oct"; a dashed
line from 15 October to it; it gets a red cross for the 01:00 payment.

## Scene 7 · The rule · 4:00–4:20 · [NAME]

VO: So the rule has three parts. Take the newest row that's about a time at or before the payment. And that was
written at or before the payment, too. And ignore rows older than a time limit, after which a value counts as
missing.

SCREEN: Three captions: "1. about a time at or before the payment", "2. written at or before the payment", "3.
older than the time limit: missing".

## Scene 8 · The numbers · 4:20–4:50 · [SHOW] [LOOP-PAYOFF]

VO: The lesson's demo runs this on a month of payments: 150,000 of them, on 5,000 cards, 2,378 of them fraud. With the
newest row, every single payment got a value written after it. The rule, flag the payment if the card has had a
chargeback, catches 98 percent of the fraud on that data. On the point in time data, it catches 62. And live, at the
till, 62. That's where the difference went. It was never there.

SCREEN: Three lines: "trained on the newest rows: catches 98%" (red), "trained point in time: catches 62%" (green),
"live, at the till: catches 62%" (white).

## Scene 9 · Tools, and the default · 4:50–5:15 · [GUARDRAIL]

VO: You rarely write this join by hand. Feature stores, programs that keep features for models, like Feast, do it for
you, and DuckDB, a small database, has an ASOF JOIN. But check what time they look at. By default, Feast looks at the
time a row is about. Keeping out values written later, like our correction, is a setting you turn on.

SCREEN: Captions "feature stores (Feast), DuckDB's ASOF JOIN: the lookup, done for you" and "by default: the time a
row is about. 'written by then' is a setting you turn on".

## Scene 10 · The moral, and a check · 5:15–5:45 · [MORAL] [PREDICT] [PAUSE]

VO: So: train only on what the model could have read at that moment. Anything written later doesn't count. No fire
engines in the training data.

One quick check. A payment at half past one in the morning on 14 October. Which row does it get, and what value? Pause
and think.

(three seconds)

The 13 October row: 1. The 14 October row is about midnight, but it isn't written until two.

SCREEN: Moral caption. For the check, the training row "14 Oct 01:30 → ?"; countdown; a green arc to the 13 October
chip, "= 1"; the 14 October chip crossed "written 02:00".

---

### Beat check

- QUESTION (scene 1) from a felt symptom; FAMILIAR + SHRINK (scene 2): one card, one feature, one fraud.
- PREDICT with PAUSE in scene 3 and the check in scene 10.
- BREAK: the "real history is honest" model (scene 3) and the as-of-only join (scene 6).
- ANALOGY + MAP (scene 4), called back in scene 6 (the Friday notice).
- NAME after SHOW: chargeback (plain sentence), label leakage, point-in-time join.
- GUARDRAIL (scene 9) and MORAL (scene 10) last. Light moments: the fire engine (about 1:50), the notice pinned up
  on Friday (about 3:55), "no fire engines in the training data" (about 5:20).

### Accuracy notes for the producer

- The timeline is the lesson's stepper for one card. The stepper's "newest row" is 15 October; the picture runs to 16
  October so the check question has a row to skip; both say 1.
- The correction is "12 October worked out again after a late chargeback report, value 1, written 15 October", as in
  the stepper; the 13 October 01:00 payment still gets 0.
- The demo numbers are the Try it's (PointInTimeDemo, seed 11): 5,000 cards, 150,000 labels, 2,378 fraud, 98% recall
  on the newest-row join, 62% point in time and live. Precision (16% vs 31%) is left to the lesson.
- "Caught" is recall: the share of all fraud that the rule flags.
- Feast's default is the event timestamp (our "about" time); `filter_by_created_timestamp=True` adds the written-time
  check. DuckDB's ASOF JOIN matches the nearest earlier row on one time column. Spark 4.3's ASOF JOIN is left out.
- TTL is said as "a time limit". The online and offline stores are left to the lesson.
