# No reply: did it happen? Six ways to hear nothing

- Slug / scene: `partial-failure`, `videos/scenes/partial_failure.py:PartialFailure`
- Lesson: `dist-01`, section 0, "One payment, no reply, and six ways it happened"
- Audience / level: a complete newcomer. Can read a little code; knows nothing about networks, servers or card
  payments behind the till.
- Length: 5:04 (~820 words of narration, one pause for a guess, one for the check)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=188`, after the count (all six rows of the table filled: the shop's column all "no reply", the charged column
  never / at 5,050 ms / never / at 5,050 ms / at 51 ms / at 51 ms)
- The learner's real question: the card reader says "no reply". Did the money leave my account, and should I tap
  again?
- Misconception to steelman and break: "no reply means it didn't happen" (fair on one computer; broken by the six
  worlds, where the card ends up charged in four), and "just wait longer" (any queue or pause can outlast any timeout)
- Concept chain: one computer: return, throw or die → two computers and a network: partial failure → silence has six
  causes the shop can't tell apart → yes, no and unknown; a timeout starts unknown → unknown read as no charges twice
  → one idempotency key on every retry (hardest last)
- Analogy family: a text to a friend ("can you book us a table for Friday?") with no reply; six stories, one view;
  booking yourself risks two tables. The key comes back as "book a table under the name Sam".
- Open loops: "did the 12.50 leave your account?" planted in scene 1 → answered in scene 6 (in four worlds, yes);
  "what should it do?" scene 1 → scene 8
- Assumptions: numbers are the lesson's stepper and `SilenceDemo` (pay-1, 12.50, a 2,000 ms timeout; 5,000 ms
  arrivals, charges at 5,050 ms; a charge at 51 ms and a slow answer at 5,051 ms). The key labels k-1 and k-2 are
  made up for the picture.

## The one picture

Top: the shop (blue, left: pay-1 12.50, its clock, its status), the network (two grey lanes, request above, answer
below, with a queue box when one is needed), the issuer (gold, right: charged or not, crashed, paused). Below: a
table that fills one row per world, with the columns "world", "the shop sees", "card charged", and later "retry, same
key". Captions at the bottom. Italic tags above the boxes once the text-to-a-friend story is mapped.

## Scene 1 · The till · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: Picture the till at a busy café. You tap your card to pay 12.50 for lunch. The card reader spins for two seconds,
then says: no reply. Try again? Did the money leave your account? Tap again, and you might pay twice. Walk away, and
the café might never be paid. The reader can't tell you, because it doesn't know either. Why not? And what should it
do?

## Scene 2 · One computer · 0:30–0:55 · [FAMILIAR] [steelman]

VO: Start with a program on one computer. When your code calls a function, it returns an answer, or it throws an
error, or the whole program stops, and nobody is left to be confused. Code like that teaches us to expect two
outcomes. So it's tempting to read no reply as no: it didn't happen.

## Scene 3 · Two computers · 0:55–1:30 · [SHRINK] [NAME]

VO: Now split the work across two computers. The card reader runs a small program; call it the shop. To take the
payment, the shop asks the bank that gave out the card to charge it. That bank is the card issuer. They talk over a
network: cables and boxes that carry messages between them. Three parts, and each can break while the other two
keep running. That's called partial failure.

## Scene 4 · The text to a friend · 1:30–2:15 · [ANALOGY] [MAP] [JOKE:pivot]

VO: You've met this before. You text a friend: can you book us a table for Friday? Two minutes, no reply. What
happened? Maybe the text never arrived. Maybe it's stuck, and arrives later. Maybe their phone died. Maybe they're in
the shower, and will see it in five minutes. Maybe they booked it, and their reply got lost. Or the reply is just
slow. Six stories, and your phone looks exactly the same in all of them. Your text is the request, the phone network
is the network, and your friend is the issuer. Do you book the table yourself? Maybe. Then you might have two tables,
and one awkward phone call.

## Scene 5 · Predict, then six worlds · 2:15–3:40 · [PREDICT] [PAUSE] [SHOW]

VO: Let's run it for real. The shop sends pay-1, a request to charge 12.50, and starts a timer: 2,000 milliseconds,
two seconds. We'll break it six ways. Before we do: in how many of the six does the card end up charged? Pause and
guess.

(three seconds)

World one: the request is lost. A box in the network had no room, and threw it away. The issuer never hears of it.
World two: the request waits in a queue, a line of messages waiting their turn. It reaches the issuer at 5,000
milliseconds, and the card is charged at 5,050. Three seconds after the shop gave up. World three: the issuer's
program crashed before it charged the card. World four: the issuer is paused. Some languages, Java among them, now
and then stop a whole program for a moment to clear out memory, and a bad pause can last seconds. At 5,000
milliseconds it carries on, and charges the card at 5,050. World five: the card was charged at 51 milliseconds, and
the answer was lost on the way back. World six: the card was charged at 51 milliseconds, and the answer is just
slow. It lands at 5,051, after the shop has already decided.

SCREEN: Each world resets the picture, sends the yellow pay-1 chip, fills the shop's timer bar to 2,000 ms ("no
reply" in red), shows what happened on the issuer's side, and adds one row to the table.

## Scene 6 · Count, and the break · 3:40–4:20 · [LOOP-PAYOFF] [BREAK]

VO: Count the last column. Never charged: twice. Already charged: twice. Charged later: twice. Four of the six. And
the shop's column? The same in every row: no reply. So wait longer? Pick ten seconds instead of two. A queue or a
pause can always last longer than whatever you pick. Waiting doesn't settle it.

## Scene 7 · Three outcomes · 4:20–4:50 · [NAME] [GUARDRAIL] [PRINCIPLE]

VO: So a call to another machine has three outcomes: yes, no, and unknown. A timeout is just the moment the shop
stops waiting. It marks the start of unknown, nothing more. And if the reader turns unknown into no, and says payment
failed, you tap again. In four of the six worlds, that charges you twice. So the rule is short. Silence is not an
answer. Treat it as unknown.

## Scene 8 · The way out · 4:50–5:30 · [NAME] [MORAL] [JOKE:reward]

VO: So what can the shop do? Ask again, safely. Before the first attempt, it gives the payment a unique label, and
sends the same label with every retry. That label is an idempotency key. Idempotent means doing it twice has the same
effect as doing it once. The issuer remembers the labels it has charged, so a repeat gets the first answer back, not
a second charge. Where the card wasn't charged yet, the retry charges it once. Where it was, the retry gets the stored
answer. Either way, never twice. It's like texting: please book a table under the name Sam. Get that text twice, and
there's still one table under Sam.

## Scene 9 · A check, and the moral · 5:30–6:00 · [PREDICT] [PAUSE] [RECAP]

VO: One quick check. In world five, the answer is lost, and the shop retries with a brand new label every time. How
many charges? Pause and think.

(three seconds)

Two. A new label looks like a new payment. Make the key once, before the first attempt. Silence has six causes, and
the shop can't tell them apart. So treat it as unknown, and ask again with the same key.

---

### Beat check

- QUESTION (scene 1); FAMILIAR and the steelmanned wrong model (scene 2); SHRINK to three parts and NAME partial
  failure once they're on screen (scene 3).
- ANALOGY + MAP (scene 4); PREDICT + PAUSE, then SHOW six worlds (scene 5); BREAK of both wrong models (scene 6).
- NAME three outcomes and idempotency key after the worlds; GUARDRAIL (unknown read as no), PRINCIPLE ("silence is
  not an answer"), MORAL, and the check last.
- Light moments: "one awkward phone call" (2:10), "one table under Sam" (5:25).

### Accuracy notes for the producer

- Worlds, times and outcomes are the lesson's stepper and `SilenceDemo` table: lost (never), queued 5 s (charged at
  5,050 ms), issuer crashed (never), issuer paused 5 s (charged at 5,050 ms), answer lost (charged at 51 ms), answer
  slow (charged at 51 ms, answer at 5,051 ms). The shop decides "unknown at 2,000 ms" in every row.
- The card is charged in four of the six worlds (two before the timeout, two after). The lesson's closing says
  "in three of them"; the stepper ("two never, two already, two will be") and the demo table both give four, and the
  video follows them.
- "Never twice" with the key: the issuer replays the stored answer for a known key. The lesson's Try it notes that
  with three attempts some worlds still end unknown (a crashed issuer that stays down); the video claims only that the
  key prevents a second charge, not that every world ends with an answer.
- The crash world leaves out the detail that the machine underneath may have acknowledged the bytes.
- The text-to-a-friend story is the video's own analogy; the lesson's running example (the café till) is kept as the
  frame.
