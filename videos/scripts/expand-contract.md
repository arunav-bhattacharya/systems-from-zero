# A new bridge beside the old one: changing a column while two versions run

- Slug / scene: `expand-contract`, `videos/scenes/expand_contract.py:ExpandContract`
- Lesson: `enc-03`, section 3, "Change the schema in phases: expand, migrate, contract"
- Audience / level: a complete newcomer who has seen, earlier in the lesson, that an update replaces instances one at a
  time. Doesn't know what a migration, a backfill, a lock or a rollback is.
- Length: 4:36 (~740 words of narration, two pauses, silent builds)
- Poster: `POSTER=148` (phase 3, backfill: both columns filled, the fleet all v2)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: the column has to change, and two versions of the program use it at once. How do you
  change it without breaking either?
- Misconception to steelman and break: "one migration with the update: rename and convert". Broken by every v1
  instance failing with `column "amount" does not exist`; "just stop the program" broken by Stripe's three years. A
  second: "drop the old column in the release that stops using it", broken in the check.
- Concept chain: data and two versions share a table → one-shot change breaks the old version → build the new beside the
  old (expand) → dual write → backfill after the last old instance (and why) → read new, with a shadow read → write new
  → contract → the rule: each step works with the versions on both sides → locks and lock_timeout → the cost
- Analogy family: replacing a road bridge. The new bridge is built beside the old; both are open; traffic moves lane by
  lane; the old one comes down last. Drivers with last year's map are old instances. Breaks where it matters: a bridge
  carries cars, it doesn't hold them, so a column's old values must also be copied (the backfill).
- Open loops: "how do you change a column under both of them?" planted in scene 1 → the moral; "why wait for the last
  v1?" predicted in scene 4.
- Assumptions: all facts are the lesson's (payouts.amount numeric(12,2) euros → amount_minor bigint cents; 40.00 →
  4000; six instances; `column "amount" does not exist`; Stripe's 100 million records at one a second, over three years;
  the six steps; v1 changing amount after v2 wrote both; shadow read; ACCESS EXCLUSIVE locks behind an open BEGIN;
  lock_timeout of a few seconds; the DROP-in-v4 mistake). The table shows two rows of 40.00 and a "…" row; the `2s` in
  `SET lock_timeout = '2s'` is the lesson's Try it value.

## The one picture

Left: the fleet, six instance boxes coloured by version (v1 blue, v2 teal, v3 green, v4 gold). Right: the `payouts`
table, the `amount` column (blue) and later `amount_minor` (green) beside it. Dots run from an instance over the top
into a column (a write) or back (a read). Top: a strip of the six phases, the current one gold. A zone under the table
for an error line or a lock queue. Captions at the bottom.

## Scene 1 · Two versions, one table · 0:00–0:35 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: The payout program keeps every payment it makes to a shop in a table called payouts: rows and columns, like a
spreadsheet. Its amount column holds euros, like 40.00. You want cents instead, 4000, in a column called amount_minor,
like every other money field in the company.

The program runs as six copies, called instances. An update replaces them one at a time, so for a while old and new
versions run side by side, on the same table. How do you change a column under both of them?

SCREEN: Title card. The table with `amount` (euros, numeric(12,2)): 40.00, 40.00, …. Under it "amount_minor: 4000
(cents, bigint)". Six v1 boxes; three turn v2 one by one; a teal dot and a blue dot run into `amount`.

## Scene 2 · The quick way · 0:35–1:30 · [PAIN] [BREAK] [WISH]

VO: The quick way is one migration, a script that changes the table, shipped with the update: rename the column,
convert it, done. Let's watch it run.

The moment it runs, every old instance still in the fleet fails: column amount does not exist. Until the rollout ends,
those requests break.

Stop the program first, then? That avoids the errors, but the downtime grows with the table. Stripe, a large payments
company, worked out that moving 100 million records at one a second would take more than three years.

Nobody's customers wait three years. What we want is a change that never surprises anyone, old or new.

SCREEN: The column becomes `amount_minor` (cents, bigint), 4000. One instance turns v2; a blue dot runs in; red
`ERROR: column "amount" does not exist`, crosses by the five v1 boxes. Then all boxes dim ("stop everything: no errors,
but downtime"); caption with Stripe's numbers; the wish.

## Scene 3 · The bridge · 1:30–2:15 · [ANALOGY] [MAP] [JOKE:pivot] [BREAK of the analogy]

VO: Think about replacing an old bridge. Nobody blows it up on a Monday and hopes the drivers read the news. You build
the new bridge next to it. For a while, both are open. Traffic moves across, lane by lane. And only when nobody drives
over the old one, you take it down.

Map it. The old bridge is the amount column. The new bridge is amount_minor. The drivers are the instances, and some
still have last year's map. Taking the old bridge down is dropping the column.

The picture breaks in one place. A bridge carries cars, it doesn't hold them. Our columns hold values, so the old values
also have to be copied across.

SCREEN: `amount` comes back with "the old bridge" under it; a second column "the new bridge" appears beside it; dots
run into both. "drivers" over the fleet. Each mapping lights its part. Caption on the break.

## Scene 4 · Six steps · 2:15–4:00 · [SHOW] [PREDICT] [PAUSE] [NAME]

VO: Step one: expand. Add amount_minor next to amount, empty. Old instances don't mention it, so they keep working.

Step two: deploy version 2. It writes both columns, and still reads amount. Version 1 and version 2 now run side by
side, and both are happy.

Step three: backfill. Once the last version 1 instance is gone, copy amount times 100 into amount_minor, a few thousand
rows at a time, in small batches.

Why wait for the last version 1 to be gone? Pause and guess.

(three seconds)

Because a version 1 instance can still change amount on a row version 2 just wrote, and it never touches amount_minor.
That row is set, but wrong. So the backfill also fixes rows that differ, not only empty ones.

Step four: deploy version 3, which reads amount_minor. To be careful, it reads both for a while and logs every
difference. That's called a shadow read.

Step five: version 4 writes only amount_minor. Step six: contract. When no running version mentions amount, drop it.

That's expand and contract, also called parallel change. Expand the schema to hold both shapes, move readers and writers
across one rollout at a time, then contract it. And the rule behind every step: each step must work with the versions
on both sides of it.

SCREEN: The phase strip lights 1 to 6 in turn. Phase 1: `amount_minor` column with NULL, NULL, …; caption with the
`ADD COLUMN`. Phase 2: half the fleet v2; teal dots into both columns, row 2's amount_minor 4000; a blue dot into
`amount` only. Phase 3: fleet all v2; row 1 gets 4000; captions on the batches. The prediction: the fleet goes back to
half v1, a blue dot changes row 2's amount ("↑ v1 changed it") and its 4000 turns red. Phase 4: all v3; green dots read
from `amount_minor`, a grey one from `amount`; "shadow read: compare, log every difference". Phase 5: all v4, `amount`
cells NULL. Phase 6: the `amount` column fades away. Captions for the name and the rule.

## Scene 5 · Locks, and the cost · 4:00–4:40 · [GUARDRAIL]

VO: One hazard remains. Even an instant change to a table takes the strongest lock for a moment. If someone left a
transaction open, a BEGIN with no end, the change waits for it. And every read that arrives after it waits behind the
change.

A one-millisecond change can stop every read of the table. So set a lock timeout of a few seconds, and retry if it fails.

And the cost. A change that used to be one file is now several releases, a backfill that may run for hours, and a team
that knows what each version may touch. Nothing in the database enforces the order.

SCREEN: A queue under the table: "BEGIN … (left open)", "ALTER TABLE: waits", "SELECT: waits", "SELECT: waits". Then
"SET lock_timeout = '2s'; then retry" and the waiting chips clear. Captions for the cost.

## Scene 6 · The moral, and a check · 4:40–5:20 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, how do you change a column under running code? Like a bridge. Build the new one beside the old, move the
traffic, and take the old one down last.

One quick check. A teammate's version 4 stops writing amount, and the same release drops the column. What goes wrong?
Pause and think.

(three seconds)

The drop runs when the first version 4 starts. The others are still version 3, and still write amount, so every one of
their writes fails until the rollout ends. And there's no going back to version 3: its column is gone.

SCREEN: Phases 1 and 6 glow; the moral caption. For the check: `amount` back, fleet all v3, one turns v4, the column
fades; countdown; a green dot runs in, crosses by the five v3 boxes, the red error; caption "no rollback to v3 either:
ship the contract one release later".

---

### Beat check

- QUESTION (scene 1) from the felt problem: two versions share one table.
- PAIN + BREAK of the quick way (scene 2) before the analogy; WISH voiced.
- ANALOGY + MAP (scene 3), with the place it breaks used to introduce the backfill.
- PREDICT with PAUSE (scene 4: why wait for the last v1; scene 6: the check).
- NAME after the six steps are shown (expand and contract, parallel change, shadow read); the rule follows.
- GUARDRAIL (scene 5: locks, lock_timeout, the cost) and MORAL (scene 6) last.
- Light moments: "nobody's customers wait three years" (1:20), "blows it up on a Monday" (1:35).

### Accuracy notes for the producer

- The quick migration in the lesson's lab renames and converts in place; v1's error is SQLSTATE 42703. The video shows
  only the message.
- The backfill copies `round(amount * 100)`; the caption says "amount × 100". It runs after the last v1 instance is gone
  and fixes rows where `amount_minor` is NULL or different.
- Phase 5 in the lesson also lets `amount` be NULL and adds `amount_minor` NOT NULL as NOT VALID, then VALIDATE; the
  video shows only "v4 writes only amount_minor" and amount turning NULL in new rows (shown for row 1 as a picture).
- Every ALTER TABLE except VALIDATE takes an ACCESS EXCLUSIVE lock; the video says "the strongest lock".
- Flyway, Scientist, Stripe's four phases and the rule "ship each contract step one release after the code stopped using
  the old column" are in the lesson; the video keeps the last one as the check's answer.
