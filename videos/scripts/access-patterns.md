# Why did the bigger store say no? Write the questions down first

- Slug / scene: `access-patterns`, `videos/scenes/access_patterns.py:AccessPatterns`
- Lesson: `model-02`, section 1, "Write the questions down before you choose the keys"
- Audience / level: a complete newcomer. Can read a little code; knows nothing about databases spread over many
  machines, keys or indexes.
- Length: about 5 minutes (~840 words of narration, two guesses, silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: a bigger store, 40 machines, refuses a question one machine answered in milliseconds.
  Why, and what do you do about it?
- Misconceptions to steelman and break: (1) "a store can always read everything if it must" (the opening's refused
  query, and AP2's scan: read 6, return 1); (2) "the shop copy holds shop, status and time, so any question about
  those three is fast" (broken by "any status since 09:00": two runs with older items between, the whole partition
  read)
- Concept chain: a two-part address (partition key, sort key) → three outcomes (key lookup, range read, scan) → write
  the questions down first (access patterns) and hold each to "lookup or range read" → a second copy under a
  different address (the stand by the door) → no gaps in the sort key (hardest) → every copy costs a write
- Analogy family: a supermarket. Aisles arranged by kind (partitions), the sign over each aisle (partition key), the
  order along the shelf (sort key), "everything on offer" means walking every aisle (a scan), a special-offers stand
  by the door (a second copy), every delivery stocks two places (one more write). Where it breaks: a tin can only sit
  in one place; data can be copied as often as you like.
- Open loops: the café owner's refused question, planted in scene 1 → answered by the shop copy in scene 5 and by
  name in scene 8
- Assumptions: all rows are the lesson stepper's (two partitions A-1001 and A-2002, six payments; the shop copy's five
  rows for M-0042; the payment-id copy shown with one entry). The café owner's question is AP3 with the stepper's
  values (M-0042, FAILED, since 09:00).

## The one picture

Top: a strip of the three access patterns AP1 to AP3, each with a mark (tick or cross). Left: the table, filed by
account then time, two partition boxes (blue) that start life as two supermarket aisles. Right: first the list of
questions, later the two copies: filed by shop, then status, then time (teal, top) and filed by payment id (purple,
bottom). Bottom: the query strip, the question on the left and the verdict on the right (green for a lookup or range
read, red for a scan). Yellow is a read in progress.

## Scene 1 · The refused question · 0:00–0:35 · [QUESTION] [LOOP-PLANT] [JOKE:is-the-explanation]

VO: A café owner phones support. "Show me my failed payments from this morning." Last week, on a database that lived on
one machine, that question came back in a few milliseconds. This week the data lives in a new store spread over 40
machines, and the screen shows an error: this query "might involve data filtering". That's the store's polite way of
saying: I'd have to read everything, and I'd rather not. So why would a bigger store refuse a small question?

SCREEN: Title card. A speech bubble with the owner's question. Left: one machine, "a few milliseconds" in green. Right:
a grid of 40 small machines, then a red error box quoting the message. A big "?".

## Scene 2 · The supermarket · 0:35–1:40 · [FAMILIAR] [ANALOGY] [MAP] [SHRINK] [NAME]

VO: Think of a supermarket. Its shelves are arranged by kind, so all the pasta is in one aisle, and all the tins in
another. Ask for pasta, and you walk to one aisle. Ask for everything on special offer today, and you walk every aisle,
because the shelves aren't arranged by offer.

The new store keeps payments the same way. Each machine holds one slice of the data, called a partition. That's an
aisle. Every payment has an address in two parts. The partition key says which partition, like the sign over the
aisle. Here, it's the account. The sort key says where inside it, like the order along the shelf. Here, it's the time.

So a question can go three ways. Give the whole address, and the store goes straight to one item: a key lookup. Give
the account and a range of times, and it reads one run of neighbours: a range read. Anything else is a scan: read the
items, and throw most of them away.

SCREEN: Two aisles, "pasta" and "tins", with products on a shelf; red offer tags on three. A yellow shopper dot walks
every aisle. The mapping appears on the right, one line per sentence (aisle → partition; sign → partition key: the
account; order along the shelf → sort key: the time). The aisles become partitions A-1001 and A-2002 with the
stepper's six payments in time order. One row glows green (key lookup), then two neighbours (range read), then every
row flashes red (scan).

## Scene 3 · Write the questions down · 1:40–2:25 · [PAIN] [WISH] [NAME]

VO: Now the café owner's question. It names a shop, a status and a time, but the address starts with the account. So
the store can't tell where her payments are, and has to read every partition. The fix starts before any key. Write
down every question the app will ask, as the query its code will send, and how often. Each line is called an access
pattern. The app has six. We'll check the first three. AP1: an account's payments, newest first. AP2: one payment, by
its id. AP3: a shop's payments with one status, in a time window. That's the café owner's. Then hold every pattern to
one rule. It must be a key lookup or a range read. Never a scan.

SCREEN: Query strip "the café owner: shop M-0042, FAILED, since 09:00", every row flashes red, "scan: every
partition". The list of six patterns with rates appears on the right; AP4 to AP6 dim. The rule under the list.

## Scene 4 · Check the three · 2:25–3:05 · [PREDICT] [PAUSE] [SHOW] [BREAK]

VO: Let's check them against our table, filed by account, then time. Which of the three can it answer without a scan?
Pause and guess. (three seconds) AP1, account A-1001, newest first. Go to its partition, start at the end, and step back
two. A range read: read two, return two. AP2 gives a payment id, which isn't in the address. So the store reads every
item: read six, return one. In a real table, that's all of them. AP3 names a shop: also a scan.

SCREEN: The list folds into the top strip (AP1, AP2, AP3). Countdown. AP1: A-1001 glows, an arrow climbs from the
newest row, two rows go green, "range read: read 2, return 2", tick. AP2: every row turns red in turn, pay-81724 green,
"scan: read 6, return 1", cross. AP3: red sweep, "scan", cross.

## Scene 5 · The stand by the door · 3:05–4:15 · [ANALOGY] [SHOW] [LOOP-PAYOFF] [NAME] [JOKE:reward]

VO: Back to the supermarket. Shoppers keep asking for offers, so the shop adds a stand by the door: the same products,
arranged a second way. Now every delivery stocks two places. Do the same with the data. Add a second copy, filed by
payment id. AP2 now gives that copy's whole address: a key lookup, read one. And a copy for the café owner, filed by
shop, then status, then time. Her question picks shop M-0042, jumps to the failed run, and trims it to this morning:
read two, return two. Her answer arrives before her coffee gets cold.

Here the supermarket picture breaks. A tin can only sit in one place. Data can be copied as often as you like.
DynamoDB, a database that Amazon runs for its customers, calls this copy a global secondary index, and keeps it up to
date for you. In Cassandra, a free database that companies run on their own machines, it's another table, and your
code writes it. In MongoDB, a database that stores each record as a document, it's another index.

SCREEN: A small stand on the right with three tagged products; a delivery splits into two. The stand goes; the
payment-id copy builds at bottom right ("pay-81724: A-2002, 11-07 09:55"), "key lookup on the copy: read 1", AP2 tick.
The shop copy builds at top right: five rows fly over from the table and land in their new order (FAILED first). AP3:
M-0042 glows, the two FAILED rows go green, "range read: read 2, return 2", AP3 tick. Captions for the break and the
three stores' names.

## Scene 6 · Any status since nine · 4:15–4:50 · [BREAK] [NAME] [GUARDRAIL]

VO: So the shop copy holds shop, status and time. Any question about those three is fast now, right? Try shop M-0042,
any status, since nine. Items are sorted by status first, then time, so the ones after nine sit in two runs, with older
ones in between. Not one run, so not one read: the store reads all five items to keep three. That's the no-gaps rule:
the sort key is used from left to right. And a filter won't rescue it. A condition on a field outside the address runs
after the read. You pay for every item read, not every item returned.

SCREEN: Query strip "shop M-0042, any status, since 09:00". Rows 09:40, 09:55 and 11:05 turn yellow, the two older
SETTLED rows between them grey, two brackets ("run 1", "run 2"). Red sweep over all five: "scan of the shop's partition:
read 5, keep 3". Captions for the rule and the filter.

## Scene 7 · The bill · 4:50–5:25 · [GUARDRAIL] [JOKE:soften]

VO: Now the bill. When payment pay-81741 arrived, it went into the table and into both copies. One payment, three item
writes. A copy nobody asks for is a shelf you stock at every delivery, for nobody. So add a copy only for a question on
your list. And the list has a price. A new question next quarter can mean a new copy, or rewriting old items to fill
in a new key. In exchange, the questions on your list stay fast at any size.

SCREEN: A "pay-81741" chip sends three yellow dots: to its table row, to its shop-copy row, and to the payment-id copy
(whose row becomes "pay-81741: A-2002, 11-07 11:05"). "1 write = 3 item writes". Captions for the price.

## Scene 8 · The moral, and a check · 5:25–6:00 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So why did the bigger store refuse a small question? Its address started with the account, and the question named a
shop. The fix wasn't a faster scan. It was a second copy, filed by shop, planned before the first payment arrived. Write
the questions down, then choose the keys. One quick check. All failed payments, at any shop. Key lookup, range read, or
scan? Pause and think. (three seconds) A scan of everything. Status is never a partition key, so the store can't pick a
partition.

SCREEN: The three ticks glow. Captions for the moral. Query strip "all FAILED payments, any shop"; countdown. Then
every row in all three boxes flashes red: "scan of everything", caption "status is never a partition key".

---

### Beat check

- Opens with QUESTION (scene 1) from the lesson's opening (the refused query).
- FAMILIAR + ANALOGY + MAP (scene 2) before the names partition, partition key, sort key, key lookup, range read, scan.
- PAIN and WISH (scene 3) before the name "access pattern".
- PREDICT with PAUSE (scene 4, and the check in scene 8); SHOW right after each.
- BREAK: the scans in scene 4, the analogy's limit in scene 5, the no-gaps case in scene 6.
- GUARDRAIL (scenes 6 and 7) and MORAL (scene 8) come last. Light moments: the polite refusal (0:25), the coffee (3:55),
  the shelf stocked for nobody (5:05).

### Accuracy notes for the producer

- Every row on screen is the lesson stepper's. The payment-id copy shows one entry (as the stepper does); a real copy
  holds one entry per payment.
- The opening's error message is the lesson's quote (Cassandra's wording); the video doesn't name the store.
- "Read 2, return 2", "read 6, return 1", "read 1" and "1 write = 3 item writes" are the stepper's verdicts. "Read 5, keep
  3" for "any status since 09:00" counts the five M-0042 rows on screen, three of them after 09:00; the lesson's Try it
  (b) calls this case a scan of the shop's partition.
- The check is the lesson's Try it (f): `status = FAILED` is a scan of everything, because status is never a partition
  key.
- Left to the lesson: hashing, AP4 to AP6, Cassandra's table-per-question design, DynamoDB's FilterExpression by name,
  and Alex DeBrie's note on inflexibility.
- Ids are spoken through `SAY` rules (A-1001 as "A ten oh one", M-0042 as "M forty-two", pay-81741 digit by digit).
