# Seventeen off, and no warning: how JSON lost a payment

- Slug / scene: `encodings`, `videos/scenes/encodings.py:Encodings`
- Lesson: `enc-01`, section 2, "JSON goes everywhere, and quietly rounds big numbers"
- Audience / level: a complete newcomer. Has seen a web page and a number; doesn't know what JSON, a double, 2^53 or a
  schema is.
- Length: 4:17 (~680 words of narration, two pauses, silent builds)
- Poster: `POSTER=141` (the payment number snapped from …904017 to …904000 on the 256-step line, rows above)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: the payment program sent the right number and nothing reported an error, so how did
  the dashboard end up with a different one?
- Misconception to steelman and break: "a number is a number; if it went through, it arrived". Broken by the
  dashboard's 4000 in place of 4017, and then by the prediction around 2^53 (only 2^53 + 1 changes). A second one,
  "JSON should have complained", is voiced and answered (the RFC sets no size).
- Concept chain: JSON is text every language reads → the reader turns numbers into doubles → a double has 53 binary
  digits, so big numbers have big steps → a number between steps snaps to the nearest → fine for amounts, fatal for
  names (ids) → send 64-bit numbers as strings → JSON's other gaps (fractions, bytes, no schema)
- Analogy family: scales. A kitchen scale weighs to the gram; a lorry weighbridge moves in steps of, say, 20 kilos (an
  illustrative figure). Breaks where it matters: a lorry's weight is an amount, a payment number is a name.
- Open loops: "where did the payment go?" planted in scene 1 → answered in scene 4 and the moral; the check reuses the
  steps near the payment number.
- Assumptions: all numbers are the lesson's (1849204436731904017 → 1849204436731904000; 116 bytes; 2^53 =
  9,007,199,254,740,992; four test values around 2^53 and which change; steps 256 apart near the payment number;
  3 KB → 4 KB with Base64). Computed for the picture with Python's float, the same IEEE 754 double: the neighbouring
  steps 1849204436731903744 and 1849204436731904256, "about two hundred times bigger" (205), and the check's
  1849204436731904100 → 1849204436731904000.

## The one picture

Top: two programs (left "payment program, Kotlin", right "dashboard, JavaScript in a browser") with an arrow between,
and the JSON text under it. Middle: two rows, "sent" (white) and "shown" (red when it differs). Bottom: a number line
of the double's steps (ticks), with yellow dots for numbers and red for a number that moved. Captions at the bottom.

## Scene 1 · The missing payment · 0:00–0:30 · [QUESTION] [LOOP-PLANT]

VO: Picture the owner of Fern Bakery. A customer wants a refund of 40.00. She finds the payment on her dashboard, a web
page that lists the day's card payments, and presses Refund. The answer: no such payment.

But the payment is there. The program that records payments has it, under a long number, nineteen digits, ending in
4017. It sent that number to the dashboard, and neither program reported an error. So where did the payment go?

SCREEN: Title card. The dashboard box (right) with a "Refund 40.00" chip, then red "no such payment". The payment
program box (left) with the row "sent: 1849204436731904017". An arrow between; a "?".

## Scene 2 · Text everyone reads · 0:30–1:15 · [FAMILIAR] [SHOW] [PAIN]

VO: The two programs are written in different languages, so they agree on text. The payment program writes the payment
as JSON, a plain text format every language can read: each name in quotes, then its value. Here it is, 116 bytes.

The dashboard runs JavaScript, the language web pages run. It reads the text, and turns every number into a JavaScript
number, which is a double. And here's what the dashboard shows: the same number, except it ends in 4000. Seventeen off,
and no warning.

A refund for that number finds nothing, or someone else's payment. That's the missing payment. Why would a computer
change a number nobody asked it to change?

SCREEN: The JSON line (two rows of mono text) runs along the arrow and settles under it; "116 bytes". On "a double",
a chip "every number → a double" by the dashboard. The row "shown: 1849204436731904000", the last four digits red.
Caption "17 off, no warning".

## Scene 3 · Scales · 1:15–1:50 · [ANALOGY] [MAP] [JOKE:pivot]

VO: Think about scales. A kitchen scale weighs flour to the gram. The weighbridge that weighs lorries moves in bigger
steps, say 20 kilos at a time. Nobody minds. Twenty kilos on a lorry is nothing.

A double works the same way. It has room for 53 binary digits, and no more. Small numbers get exact steps, like the
kitchen scale. Big numbers get big steps, like the weighbridge. And a number between two steps is snapped to the
nearest one.

SCREEN: Two chips: "kitchen scale: steps of 1 g" and "weighbridge: steps of 20 kg (say)". Then a number line with
close ticks on the left fading to wide ticks on the right; captions "a double: room for 53 binary digits",
"small numbers: exact steps; big numbers: big steps", "between two steps: snapped to the nearest".

## Scene 4 · The edge, and our number · 1:50–2:50 · [SHRINK] [PREDICT] [PAUSE] [SHOW]

VO: Up to 2 to the 53, about nine quadrillion, every whole number has its own step. Just above it, the steps are 2
apart. Here are four numbers around that edge. Which ones come back changed? Pause and guess.

(three seconds)

Only one. 2 to the 53, plus 1, has no step of its own, so it lands on 2 to the 53. The even numbers on either side
have steps, and survive.

Our payment number is far bigger, about two hundred times bigger, so its steps are 256 apart. The nearest step to 4017
is 4000. There's the missing 17.

SCREEN: The line now shows ...989 to ...996 (2^53 = 9007199254740992 marked): a tick on every whole number up to
...992, then only on the even ones. Four yellow dots on ...991, ...992, ...993, ...994. Countdown. Three drop onto
their ticks (green); ...993 slides to ...992 and turns red. Then the labels become ...903744, ...904000, ...904256; a
dot at ...904017 slides to ...904000; "17" in red.

## Scene 5 · Where the scales break, and the rule · 2:50–3:50 · [BREAK] [JOKE:skeptic] [NAME] [GUARDRAIL]

VO: So the scale picture holds, but it breaks in one place that matters. A lorry's weight is an amount, and close is
fine. A payment number is a name. Off by 17 is a different payment, or none.

You might be thinking JSON should have complained. It can't. The document that defines JSON sets no size for numbers.
It only warns that whole numbers up to 2 to the 53, minus 1, work in every reader. Twitter hit this with the numbers of
its posts, and added a second field holding the same number as text.

So here's the rule. A big number in JSON is safe only as a string. Send 64-bit numbers in quotes. In quotes, the
dashboard keeps all 19 digits as text, and a Java program reads it straight back into a 64-bit number.

SCREEN: Captions "a weight: an amount, close is fine" / "a payment number: a name, close is wrong". Then "RFC 8259:
no size for numbers", "safe in every reader: up to 2^53 - 1", "Twitter: id_str, the same number as a string". The JSON
line gains quotes around the number (gold); the shown row becomes the full number, green, with a tick; caption "send
64-bit numbers in quotes".

## Scene 6 · JSON's other gaps · 3:50–4:15 · [GUARDRAIL]

VO: And numbers are only the first gap. JSON can't tell a whole number from a fraction: is 40.0 an exact amount, or a
double? It has no type for raw bytes, so a 3 KB signature travels as Base64 text and grows to 4 KB. And nothing in a
JSON document says what shape the record should be. Every reader guesses, in its own code.

SCREEN: Three short rows replace the number line: "40.0: exact amount, or a double?", "bytes: Base64, 3 KB → 4 KB",
"no schema: every reader guesses".

## Scene 7 · The moral, and a check · 4:15–4:45 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, where did the payment go? Nowhere. The number was sent right, and read into a box too small for it. Two programs
never share a number. One writes bytes, and the other decides for itself what they mean.

One quick check. The next payment's number ends in 4100, and it's sent bare, without quotes. What does the dashboard
show? Pause and think.

(three seconds)

It ends in 4000 too. 4100 is nearer to 4000 than to 4256. Two payments, one number on the screen. Unless you send them
in quotes.

SCREEN: Captions "sent right, read into a box too small", "one program writes bytes; the other decides what they mean".
For the check the number line returns with the three steps; a dot at ...904100 slides to ...904000 (red), the shown row
reads ...904000 for both. Last caption: "send 64-bit numbers in quotes".

---

### Beat check

- QUESTION (scene 1) from a felt symptom; FAMILIAR (JSON as shared text) before the mechanism.
- SHOW the failure (scene 2) before any explanation; ANALOGY + MAP (scene 3) said part by part.
- PREDICT with PAUSE (scene 4 and the check); SHOW right after.
- BREAK: the wrong model "a number is a number" (scene 2), and the analogy's own limit, amount versus name (scene 5).
- NAME: double (scene 2, glossed in scene 3), the rule (scene 5). GUARDRAIL (scenes 5 and 6), MORAL last.
- Light moments: the lorry that nobody minds (1:25), "JSON should have complained" (3:05), "a box too small" (4:20).

### Accuracy notes for the producer

- A double rounds to the nearest representable value in binary (round half to even); the video's "snapped to the
  nearest step" is that. 53 bits hold the significand (52 stored plus one implied).
- "Room for 53 binary digits" is the lesson's wording; the edge where gaps appear is 2^53, and the safe range RFC 8259
  names is up to 2^53 - 1.
- The weighbridge's 20 kg step is an illustrative figure, said with "say".
- The step labels ...903744 and ...904256 and the check's ...904100 were computed with Python floats (IEEE 754
  doubles), the same as JavaScript's numbers.
- Jackson reading a quoted number into a `Long` is the lesson's claim ("without any extra setting"); the video says "a
  Java program".
- Left to the lesson: CSV and XML, JSON Schema and `additionalProperties`, binary JSON (next section).
