# The refund that came second, and the clock that threw it away

- Slug / scene: `clock-skew`, `videos/scenes/clock_skew.py:ClockSkew`
- Lesson: `dist-03`, section 2, "Last write wins throws away the write that came second"
- Audience / level: a complete newcomer. Has seen a printed receipt and a phone clock; knows nothing about timestamps
  in databases, clock skew or causality.
- Length: 5:11 (~800 words of narration, plus two pauses and silent builds)
- Poster: `POSTER=158` (all four writes on the two rulers, the two pod-b stamps red and crossed, "4 writes, 4 OKs, 2 gone")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: if two writes hit the same thing, the later one should win. Why would a database ever
  keep the earlier one?
- Misconception to steelman and break: (1) "the printed time tells you which came last", broken by the tills and by the
  trace; (2) "only a big clock error does this, so better clocks fix it", broken by shrinking the skew to 5 ms (nothing
  lost) and 7 ms (lost again): the skew only has to beat the 6 ms gap.
- Concept chain: printed times order receipts → last write wins keeps the highest stamp → a slow clock's later write
  gets a lower stamp and is dropped with an OK → it only takes a skew bigger than the gap between causally related writes
  (hardest last) → never let two clocks decide; keep every change
- Analogy family: the lesson's shop with two tills, till B 15 seconds slow, and the owner who keeps only the latest
  receipt (the store); "keep every receipt" is the fix.
- Open loops: "which receipt really came last?" planted in scene 1 → answered in scene 6.
- Assumptions: the trace is the lab's `LwwDemo` (pod-b 15 ms behind; captured .002 kept, refunded .008 stamped .993
  dropped, settled .014 kept, chargeback .020 stamped .005 dropped). The 5 ms and 7 ms runs follow the lesson ("a skew
  of 6 ms loses nothing, and 7 ms loses every write"; with 5 the trace loses nothing). Loss rates 4%, 14%, 50% and
  Jepsen's 285 of 1,009 are the lesson's. The tills' printed times (12:00:00, 11:59:55) are made up for the picture.

## The one picture

Left: two writers, the tills that become pod-a (blue, clock exact) and pod-b (gold, clock 15 ms behind). Right: the
store (the owner's book, then "payment status") showing the kept value and its stamp. Between them, each write travels as
a chip, and a green "OK" travels back. Below: two rulers on one scale, true time on top and stamp underneath; each write
is a dot on both, joined by a dashed line (straight down for pod-a, slanting 15 ms left for pod-b). Red means dropped.

## Scene 1 · Two tills · 0:00–0:35 · [QUESTION] [FAMILIAR] [ANALOGY] [LOOP-PLANT]

VO: Picture a shop with two tills. Each one prints the time on every receipt. Till B runs fifteen seconds slow, and
nobody knows. A customer buys a jacket at till A. Ten seconds later, she returns it at till B. That evening, the owner
keeps only the latest receipt for each item. By the printed times, the return came five seconds before the sale. So she
keeps the sale. The books now say the jacket was never returned. Which receipt really came last? And why did a clock
get to decide?

SCREEN: Till A and till B; a blue "jacket sold 12:00:00" chip and a gold "jacket returned 11:59:55" chip; caption
"till B: really 12:00:10, minus 15 s = 11:59:55". The owner's book keeps "jacket sold"; the return fades: "the return: gone".

## Scene 2 · Last write wins · 0:35–1:35 · [PAIN] [NAME] [MAP] [SHRINK]

VO: It's tempting to trust printed times. Your phone always seems right. But right means within a few milliseconds,
sometimes more. And computers do things a few milliseconds apart. Many databases use the owner's rule. When two writes
hit the same item, keep the one with the highest timestamp, and drop the other. It's called last write wins.
Cassandra, a database that spreads data over many machines, takes those stamps from the program that sends the write,
read from that machine's own clock. So here are our tills: two copies of the payments program, pod A and pod B. Each
stamps its writes with its own clock, and pod B's clock is fifteen milliseconds behind. The owner's book is the store:
one payment's status, and its stamp. Let's draw two lines. On top, true time, in thousandths of a second around ten
o'clock. Underneath, the stamp each write carries.

SCREEN: The tills turn into pod-a and pod-b; the book becomes "payment status". The true-time and stamp rulers draw in.

## Scene 3 · The trace · 1:35–2:50 · [PREDICT] [PAUSE] [SHOW] [JOKE:release] [NAME]

VO: pod A writes captured: the money has moved. Its stamp is two thousandths past ten. The store is empty, so it keeps
it, and says OK. pod B reads the status, sees captured, and six thousandths later writes refunded. This write was
decided after seeing the first one. So it's later by cause, and later in real time. But pod B's clock is fifteen behind,
so its stamp says seven thousandths before ten. The store compares the stamps. What does it keep, and what does it tell
pod B? Pause and guess.

(three seconds)

It keeps captured, and drops the refund. And it tells pod B: OK. Very polite. The refund was confirmed, it's gone, and
nothing logged an error. pod A writes settled: paid out to the shop. Stamp, fourteen past. Higher than two, so it's
kept. pod B writes chargeback: the customer's bank took the money back. Its stamp, five past. Lower than fourteen.
Dropped, and OK again. Four writes, four OKs, two gone. Look at the two lines. In true time, the writes take turns. By
the stamps, every pod B write slides fifteen thousandths to the left, behind the pod A write it followed. And pod B
keeps losing like this, until its clock passes the highest stamp pod A wrote.

SCREEN: Each write: a chip with its stamp travels to the store, a dot lands on each ruler, a dashed line joins them,
and "OK" flies back. Dropped stamps turn red with a cross under them.

## Scene 4 · How much skew? · 2:50–4:10 · [BREAK] [NAME] [SHOW]

VO: You might think: fifteen thousandths is a big error, so better clocks fix this. Let's test that. Shrink pod B's
error to five. Now the refund's stamp is three past, above captured's two. Kept. Nothing lost. Now seven. The stamp is
one past. Below two. Lost again. So the skew doesn't need to be big. It only has to be bigger than the gap between two
writes where the second was decided after seeing the first. Writes like that are called causally related. Here the gap
is six thousandths. Add some thinking time between the writes, and the lab counts the damage. Ten milliseconds of skew
loses four percent of confirmed writes. Twenty loses fourteen percent. A hundred or more loses half. Why stop at half?
By then every pod B write that follows a pod A write is lost, and every pod A write survives. And over the internet,
clock errors of ten to twenty milliseconds are ordinary. It happened for real. In 2013, Kyle Kingsbury tested Cassandra
with writers that took turns behind a perfect lock. It still lost 285 of 1,009 confirmed writes, about twenty-eight
percent. The stamps, not the lock, decided which write survived.

SCREEN: pod-b's clock label changes to 5 ms; its stamp dots slide right and turn green. Then 7 ms: they slide to just
left of pod-a's and turn red. A yellow "6 ms" bracket over captured and refunded on the true-time ruler. Captions carry
the loss rates and the Jepsen result.

## Scene 5 · The rule, and the fix · 4:10–4:40 · [GUARDRAIL]

VO: So here's the rule. Never let two machines' clocks decide which write wins. Better clocks shrink the window. They
don't close it. The fixes stop comparing stamps from different machines. Back in the shop: keep every receipt, not just
the latest. In a database, that's one new row for each status change, never overwritten, and you read them all. Or you
make the order explicit, with a write that applies only if the value is still the one you read. Later lessons build
those.

SCREEN: The store becomes "every status change" and lists all four. Captions carry the rule and the two fixes.

## Scene 6 · The moral, and a check · 4:40–5:10 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, which receipt came last? The clock never knew. It only knew what it printed. Two clocks can't put two machines'
writes in order, so don't ask them to. One quick check. Flip it. Pod B's clock now runs fifteen milliseconds ahead.
Whose writes get lost? Pause and think.

(three seconds)

Pod A's. Last write wins always favours the fast clock. The slow one loses, and nobody gets an error.

SCREEN: pod-b's label becomes "clock 15 ms ahead"; countdown; pod-a pulses red.

---

### Beat check

- Opens with QUESTION from the tills (the lesson's opening); FAMILIAR is a printed receipt and a phone clock.
- ANALOGY mapped out loud in scene 2 (tills = pods, printed time = stamp, owner's book = store) before the trace.
- PREDICT with PAUSE: what the store keeps (scene 3) and the check (scene 6).
- BREAK: "better clocks fix it", run at 5 ms and 7 ms (scene 4).
- NAME after the SHOW: last write wins (after the owner's rule), causally related (after the 6 ms gap is seen).
- GUARDRAIL (scene 5) and MORAL (scene 6) last. Light moments: "very polite" (2:25), the jacket that was never returned.

### Accuracy notes for the producer

- The trace and stamps are the lab's `LwwDemo` output. The register in the lab is one value with a stamp, like a
  Cassandra cell; the video calls it the store.
- The 7 ms case is reasoned from the lesson's statement (7 ms loses every slow-copy write that follows a fast-copy
  write); the lab prints only the 5 ms rerun (nothing lost).
- 4%, 14%, 50% are the lab's 10, 20 and 100 ms rows (4.2%, 13.8%, 50.0%), with 0 to 50 ms of thinking time.
- The check's answer is the same rule mirrored: with pod-b ahead, every pod-a write that follows a pod-b write is lost.
- Left to the lesson: Cassandra's driver stamping in microseconds, sets and counters, lightweight transactions, version
  vectors and logical clocks (named only as "make the order explicit"), and TrueTime and commit wait (section 3).
