# Why is my balance 20.00? Keep the list, work out the number

- Slug / scene: `event-sourcing`, `videos/scenes/event_sourcing.py:EventSourcing`
- Lesson: `stream-03`, section 0, "A balance can't tell you why it's 20.00"
- Audience / level: a complete newcomer. Has met events, logs and change data capture in the two lessons before;
  doesn't know event sourcing, folds, or commands versus events.
- Length: 4:12 (~720 words of narration, two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=110`, the `poster` stamp (all six events of acct-17's stream, the fold at 20.00 in green, the accounts table at
  20.00, the cursor on v6)
- The learner's real question: the balance says 20.00, so where did that come from, and why can't the database say?
- Misconception to steelman and break: "the table is the data; bolt history on with a second table if you need it"
  (two records of the truth that can disagree). Then "this is just change data capture" (a row change says what the
  number became, not what happened).
- Concept chain: a row that is overwritten forgets → the bank app's list explains the number → store every change as
  an event in an append-only log → the state is a fold → the table is a cache → commands can be refused, events can't
  → corrections are new events → a redesign, and the log grows (hardest last)
- Analogy family: your bank app (the balance at the top, the list under it), a notebook you never rub out, a column
  of numbers added one line at a time, a bank booking a reversal instead of tearing out a page.
- Open loops: "why twenty?" planted in scene 1 → answered in scene 5 (a 50.00 transfer after a card payment and its
  refund).
- Assumptions: acct-17, Mira Okafor, v1 to v6 with their amounts and references, the running balances (0, 100, 70,
  25, 70, 20), "as of v5: 70.00" and "pay-982: v4, v5" are the lesson's LedgerDemo output. "Withdraw 80.00" is the
  lesson's command example. The check's "as of v3: 70.00" is the same demo's running balance.

## The one picture

Top left: the accounts table (blue), one row, acct-17 and its balance. Below it, the log: account acct-17's stream,
six event rows (deposits green, withdrawals gold). Right: the fold box (green) with the running balance, and a yellow
cursor that steps down the log. A purple command card appears above the fold box when needed.

## Scene 1 · The help line · 0:00–0:25 · [QUESTION] [LOOP-PLANT]

VO: A customer calls the payments help line. Why is my balance 20.00? Support opens the accounts table: one row for
her account, acct-17, and one number, 20.00. That's all there is. Twenty. But why twenty? The table can't say.

SCREEN: The question as a caption; the accounts table with "acct-17 20.00".

## Scene 2 · Your bank app · 0:25–0:50 · [FAMILIAR]

VO: Now think of your own bank app. The balance sits at the top, and under it, a list. Salary in, a coffee, a book,
the book refunded, fifty to a friend. Read the list, and the number makes sense.

SCREEN: The balance box (20.00) and the list beside it; the six rows appear as they are named.

## Scene 3 · The table overwrites · 0:50–1:40 · [PAIN] [BREAK] [WISH]

VO: So why can't the table say? Watch how it got to 20.00. Every change is an UPDATE, a command that changes a row,
and each one writes over the answer before it. 100.00. 70.00. 25.00. 70.00. 20.00. Each old number is gone the moment
the new one lands. You could bolt history back on, with a small program the database runs on every change, copying it
into a second table. But now there are two records of the truth, and when they disagree, which one wins? What we
really want is the app's list as the truth itself.

SCREEN: The list dims. The table's number is overwritten five times; each old number drops away. A "history table"
grows beside it with "a second truth?"; both outlines pulse red.

## Scene 4 · The log · 1:40–2:10 · [ANALOGY] [SHOW]

VO: So turn it around. Store every change as an event, a record of one thing that happened, and never change it. The
events go into a log you only add to the end of, like a notebook you never rub out. Here's account acct-17's own
list, its stream, each event with a version number.

SCREEN: The list returns, retitled "stream account-acct-17"; the version numbers pulse in turn.

## Scene 5 · The fold · 2:10–3:05 · [PREDICT] [PAUSE] [SHOW] [NAME] [LOOP-PAYOFF]

VO: Now the balance. Start from an empty account and apply each event in order, the way you'd add up a column one
line at a time. What's the balance after v4? Pause and guess.

(three seconds)

25.00. Zero, a hundred, seventy, twenty-five. Then the refund brings it back to seventy, and the transfer leaves
twenty. Adding up in order like that is called a fold. And the help line has its answer: a fifty transfer, after a
card payment and its refund. And questions the table never could answer are easy. The balance before the transfer?
Fold to v5: 70.00. Everything that mentions pay-982? v4 and v5.

SCREEN: The cursor steps down the rows while the fold box counts 0.00, 100.00, 70.00, 25.00 (yellow), 70.00, 20.00
(green). The fold box is titled "fold". Then "as of v5?" (cursor on v5, 70.00) and "mentions pay-982?" (v4 and v5
pulse).

## Scene 6 · The name · 3:05–3:35 · [NAME] [JOKE:release]

VO: Keeping every change as an event, and working the state out from them, is called event sourcing. The accounts
table, if you keep one, is just a cache: a saved copy of where the log ends, that you can always work out again. The
table was never lying, by the way. It just had a very short memory.

SCREEN: The definition as a caption; an arrow from the log up to the table, "a cache: where the log ends".

## Scene 7 · Commands and events · 3:35–4:20 · [BREAK] [GUARDRAIL]

VO: Two words need to stay apart. A command is a request, an order: withdraw 80.00 from acct-17. It can be refused.
Fold the log, the balance is 20.00, so this one is. An event is a fact, in the past tense: 80.00 was withdrawn. It
already happened, so nothing later may refuse it. Only a command that passes the rules becomes an event. And a
mistake is never rubbed out. You add a correcting event, the way v5 refunds v4. A bank books a reversal. It doesn't
tear a page out of its ledger.

SCREEN: A purple command card "withdraw 80.00", the fold's 20.00 pulses, "refused: balance 20.00". Captions for event
and rule. v4 then v5 pulse.

## Scene 8 · Not change data capture · 4:20–4:55 · [GUARDRAIL]

VO: Isn't this the change log from the first lesson? Change data capture reads row changes out of the database: the
balance went from 100.00 to 70.00. That's only what the number became. The event says MoneyWithdrawn, card pay-981:
what happened, and why. So event sourcing means redesigning the program around events. You can't switch it on later.
And the log only grows, so folding years of events gets slow. Snapshots, later in this lesson, keep it fast.

SCREEN: Caption "a row change: balance 100.00 -> 70.00"; v3 pulses. Captions for the redesign and the growing log.

## Scene 9 · The code, the moral, a check · 4:55–5:40 · [MORAL] [PREDICT] [PAUSE]

VO: In Java and Kotlin the fold is a few lines. Start at zero, and for each event, add a deposit or take away a
withdrawal. So keep the list, and work the number out from it. A balance tells you what. The log tells you why.

One quick check. Support wants the balance as it was right after v3. Can the table tell them? Can the log? Pause and
think.

(three seconds)

The table can't. It only knows 20.00. The log can: fold to v3, and it's 70.00.

SCREEN: Java (a loop with a pattern `switch`) and Kotlin (`events.fold`) side by side. Then "a balance tells you what;
the log tells you why". For the check, v3 glows; the table's 20.00 pulses red; the cursor folds v1 to v3, 70.00, tick.

---

### Beat check

- Opens with QUESTION (scene 1); FAMILIAR is the bank app (scene 2).
- PAIN and BREAK: the overwrites and the bolted-on history table (scene 3), then the WISH.
- PREDICT with PAUSE: the balance after v4 (scene 5) and the check (scene 9). NAME after the SHOW: fold (scene 5),
  event sourcing and cache (scene 6), command and event (scene 7).
- GUARDRAIL: commands can be refused, corrections are new events (scene 7); a redesign, and the log grows (scene 8).
  MORAL last (scene 9). Light moment: the table's short memory (scene 6).

### Accuracy notes for the producer

- Every number is from the lesson's LedgerDemo output (balances 0.00, 100.00, 70.00, 25.00, 70.00, 20.00; as of v5
  70.00; pay-982 in v4 and v5).
- The table's overwrites are shown one per event for the picture; the lesson says only that every UPDATE overwrote
  the answer before it.
- The code is the lesson's Kotlin `balance` fold; the Java version is the same fold as a loop over a sealed `Event`
  type with a pattern `switch` (Java 21).
- Snapshots, projections and expected versions are the later sections; the video only names snapshots.
