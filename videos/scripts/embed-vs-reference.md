# Two tills, one receipt: embed what must change together

- Slug / scene: `embed-vs-reference`, `videos/scenes/embed_vs_reference.py:EmbedVsReference`
- Lesson: `model-06`, section 0, "A document holds one payment and everything read with it"
- Audience / level: a complete newcomer. Can read a little code; knows nothing about MongoDB, documents or
  transactions.
- Length: about 4 minutes (~570 words of narration, three guesses, silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: two tills refund the same payment in the same second; how does the database make sure
  only one refund goes through, without a lock around everything?
- Misconception to steelman and break: "check the rule, then write the refund, as two steps" (with the refunds in their
  own collection, both tills read "none yet", both write, and 120.00 is refunded on 68.37). The lesson's fair point:
  a rule across separate records really does need a lock or a multi-document transaction.
- Concept chain: separate records (the SQL habit) → referencing in MongoDB → check-then-write races across two
  documents → the receipt you have to hold to write on → embedding with a running total → a write to one document is
  atomic → one guarded update: 1, then 0 (hardest) → what to embed and what to reference → transactions as the
  exception
- Analogy family: the bakery's paper receipt. Refunds written on the receipt itself with a running total at the
  bottom; you have to hold it to write on it, and only one person can (an atomic write to one document). The separate
  refunds collection is a box of loose slips that anyone can check and anyone can drop a slip into. Where it breaks:
  a receipt can't be a mile long (a document is at most 16 MB; reference what grows without limit).
- Open loops: "how does the database make sure?" planted in scene 1 → answered in scene 5 and the moral
- Assumptions: the payment, amounts, the document's fields and the results 1 and 0 are the lesson's (pay-81002,
  68.37 as amountMinor 6837, two refunds of 60.00, refundedMinor, refunds, ref-1). The version-1 refund documents
  (`paymentId`, `amountMinor`) are drawn to show "each refund holding its payment's id"; they are a design, not output.

## The one picture

Left: two tills, each with a "refund 60.00" button. Right: the data. First two collection boxes (payments on top, refunds
below); then the paper receipt with a box of loose slips beside it; then the receipt turns into the version-2 document
with its running total and refunds list, and the one-update card under it. Top: the rule. Bottom: the strip with the
payment on the left and "refunded so far" on the right. Yellow is a read or a write in progress, green a change that
went through, red a broken rule.

## Scene 1 · Two tills, one payment · 0:00–0:25 · [QUESTION] [LOOP-PLANT]

VO: A bakery customer paid 68.37 for a party order, then brought most of it back. Two staff members, at two tills, each
press refund 60.00, in the same second. The rule is that refunds never add up to more than the payment. So only one of
these should go through. How does the database make sure?

SCREEN: Title card. The two tills draw in on the left, the payment chip "pay-81002 · 68.37" on the right. Both buttons
glow together. The rule appears at the top. The strip: "pay-81002: 68.37", "refunded so far: 0.00".

## Scene 2 · Separate records · 0:25–1:05 · [FAMILIAR] [NAME]

VO: The habit from SQL databases is separate records. A payment is one row, each refund is a row in another table, and
the screen joins them back together. MongoDB, a free database program, can do the same. It stores each record as a
document: names and values inside curly braces, shaped like JSON, a common text format. A set of documents is a
collection. So version one: a payments collection, and a refunds collection where each refund holds its payment's id.
That's called referencing. The screen now needs two reads.

SCREEN: The payments collection with `{ _id: "pay-81002", status: "SETTLED", amountMinor: 6837 }`; the refunds
collection, empty. A dashed arrow labelled "paymentId" waits between them. Two read dots for the screen.

## Scene 3 · Check, then write · 1:05–1:50 · [PAIN] [PREDICT] [PAUSE] [BREAK] [JOKE:release]

VO: Each till checks the rule, then writes. Till one reads the refunds: none yet, so 60.00 fits. Till two reads at the
same moment: none yet, 60.00 fits. Both write. What does the bakery refund in total? Pause and guess. (three seconds)
120.00, on a payment of 68.37. The bakery's accountant would like a word. The check and the write were two steps, on two
documents, and the other till slipped in between. The usual cure is a lock around everything, or a multi-document
transaction: a group of writes that happen together, or not at all.

SCREEN: Yellow read dots from both tills to the refunds collection at once; "none yet: 60.00 fits" beside each till.
Both write: two refund documents drop in. Countdown. The strip turns red: "refunded so far: 120.00". A red cross on the
rule.

## Scene 4 · The receipt · 1:50–2:30 · [ANALOGY] [MAP]

VO: Think of the paper receipt instead. Write each refund on the receipt itself, with a running total at the bottom. To
write on it, you have to hold it, and only one person can hold it at a time. Till one takes the receipt, sees nothing
refunded, writes 60.00, and the total becomes 60.00. Till two gets it next, and 60 more on top of 60 is more than 68.37.
Nothing to write. The refunds collection was a box of loose slips: anyone can check the box, and anyone can drop a slip
in.

SCREEN: The collections fade. A paper receipt (68.37, a refunds area, "refunded so far: 0.00") and, beside it, a box of
loose slips. The receipt slides to till 1: a line "refund 60.00" and the total 60.00. It slides to till 2: "60.00 +
60.00 > 68.37", a grey "nothing to write". Then the slips box glows while two slips drop in.

## Scene 5 · One document, one write · 2:30–3:20 · [NAME] [SHOW] [PREDICT] [PAUSE] [LOOP-PAYOFF] [JOKE:is-the-explanation]

VO: Version two does what the receipt does. The refunds go inside the payment's document, in a list, next to a running
total. That's called embedding. And in MongoDB, a write to one document is atomic: it happens completely or not at all,
and no other write slips in halfway. So one update does the check and the change together. It changes the payment only
if the total plus this refund is at most the amount. Then it adds the refund and raises the total. Two refunds of
60.00. How many documents does each one change? Pause and guess. (three seconds) One, then zero. The second's filter no
longer matches, so it changes nothing. No error, and no lock you had to take. And the screen gets everything in one
read.

SCREEN: The receipt becomes the document `{ _id: "pay-81002", status: "SETTLED", amountMinor: 6837, refundedMinor: 0,
refunds: [ ] }`. The one-update card: "filter: only if refundedMinor + 6000 ≤ amountMinor", "change: add the refund to
refunds, add 6000 to refundedMinor". Countdown. Till 1's update: the document becomes `refundedMinor: 6000, refunds:
[ { refundId: "ref-1", amountMinor: 6000 } ]` and till 1 shows `modifiedCount: 1`. Till 2: the filter line turns red
(6000 + 6000 > 6837) and till 2 shows `modifiedCount: 0`. The strip: "refunded so far: 60.00" in green.

## Scene 6 · What goes inside? · 3:20–3:55 · [GUARDRAIL] [BREAK of the analogy]

VO: So should everything go inside? No. Embed what's read together, changed together, and stays small. A payment has a
handful of refunds at most. Reference what grows without limit, like an account's payments over the years. A document
can be at most 16 megabytes, and a receipt can't be a mile long. And when two things truly can't share a document, like
a transfer between two accounts, MongoDB has multi-document transactions, since version 4.0. Its own docs say they
usually cost more than a one-document write.

SCREEN: Two columns of captions, "embed: read together, changed together, stays small" (green) and "reference: grows
without limit" (blue). A long receipt stretching off the bottom, crossed out; "a document: at most 16 MB". Then
"transactions (since 4.0): for what can't share a document, such as a transfer between two accounts".

## Scene 7 · The moral, and a check · 3:55–4:25 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So, two tills, one payment. Put what must change together inside one document, and one guarded write settles the
race. One quick check. After the first refund, a third till tries a refund of 8.37. Does it go through? Pause and think.
(three seconds) Yes. 60.00 plus 8.37 is exactly 68.37, and the rule says at most. One document changed, and the payment
is fully refunded.

SCREEN: Caption "what must change together lives in one document". A third chip "refund 8.37"; countdown. The filter
line reads "6000 + 837 ≤ 6837" in green; the total becomes 6837 (68.37).

---

### Beat check

- Opens with QUESTION (scene 1); FAMILIAR (scene 2) before the cure.
- PREDICT with PAUSE: the race (scene 3), the two updates (scene 5), the check (scene 7); SHOW after each.
- BREAK: the check-then-write race (scene 3), the mile-long receipt (scene 6).
- ANALOGY + MAP (scene 4) before the names embedding and atomic (scene 5). Referencing is named in scene 2, as the
  familiar starting point.
- GUARDRAIL (scene 6) and MORAL (scene 7) last. Light moments: the accountant (1:30), "no error, and no lock you had to
  take" (3:10), the mile-long receipt (3:40).

### Accuracy notes for the producer

- The document and the results (`modifiedCount` 1 then 0, refundedMinor 6000, one refund ref-1) are the lesson's Try-it
  output. The real filter also checks `status: "SETTLED"`; the card shows only the refund rule.
- The race in version 1 is the lesson's point that a rule spanning two documents needs a multi-document transaction to
  check and write safely; the video shows what happens without one. The refund documents' fields are a design sketch.
- The check (8.37) follows from the filter's "at most" (`$lte`): 6000 + 837 = 6837. It wasn't run in the lesson; the
  video says only that the filter matches and one document changes.
- Left to the lesson: BSON types, the text amount "42.50", `$jsonSchema` validators and the `strict` and `constraint`
  levels (MongoDB 9.0), and the PostgreSQL `jsonb` comparison.
- Amounts are spoken as people say them ("sixty-eight thirty-seven", "sixty") through `SAY` rules; the screen keeps
  68.37 and the minor units (6837, 6000).
