# Two hellos, then a lock: the TLS 1.3 handshake

- Slug / scene: `tls-handshake`, `videos/scenes/tls_handshake.py:TlsHandshake`
- Lesson: `net-10`, section 2, "The TLS 1.3 handshake: one round trip, then everything is locked"
- Audience / level: a complete newcomer. Has read the lesson's first two sections (the key exchange with small
  numbers, the certificate as a passport); knows nothing else about networks.
- Length: 5:25 (~830 words of narration; Kokoro speaks about 180 words a minute, and the pauses, guesses and
  silent builds bring the pace down)
- Poster: `POSTER=242.5` (the whole ladder with its arrival times: 70, 140, 175 ms)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: how do my laptop and the bank agree on a secret while the café's Wi-Fi box reads
  every word, and how can that take less than a fifth of a second?
- Misconceptions to steelman and break: (1) "the padlock hides everything from the first word" (broken: the two
  hellos are open, and the box reads the server's name); (2) "a key the box can't work out is enough" (broken:
  the box can play both parts, two keys, and read everything); (3) "the careful way is to ask first" (it costs a
  round trip every time; a wrong guess costs exactly the same, and only when it's wrong)
- Concept chain: a round trip is the unit of cost → asking first costs two → guessing (key shares in the first
  message) costs one → the two hellos are open, the rest is locked → a lock needs proof (certificate,
  CertificateVerify, Finished) → count 175 ms → guardrails (HelloRetryRequest, pools, what stays visible)
- Analogy family: ordering at a café abroad, in two languages at once (the guess); the passport from the
  lesson's section 1 comes back for the certificate
- Open loops: "the padlock hides everything from the first word?" planted in scene 1 → broken in scene 4 and
  again in the guardrails; "the careful way" in scene 2 → its 245 ms comes back in the check question
- Assumptions: the bank is 70 ms away there and back (the lesson's number); the left actor is "your laptop", as
  in the lesson's opening (the lesson's sections call it the client); the server's name is the lab's
  `api.pay.test`

## The one picture

A ladder diagram, time going down. Top row: your laptop (blue, left), the Wi-Fi box behind the counter (grey,
near the laptop), the bank (green, right, `api.pay.test`). Under each actor, a state line (what it holds: a
secret, the same key, new keys). Dashed lifelines go down from each. Each row is one crossing (35 ms): TCP's
handshake (grey), the ClientHello (white), the ServerHello (white), the locked flight (gold), Finished with the
payment (gold). Where a row crosses the box's line, a yellow eye means the box read it and a gold padlock means it
couldn't. At the bottom, "the Wi-Fi box saw:" fills in. Arrival times appear at the receiving end. Same places
and colours from start to end.

## Scene 1 · The padlock · 0:00–0:35 · [QUESTION] [LOOP-PLANT]

VO: You're in a café, on its free Wi-Fi, paying a bill on your bank's website. Every packet you send goes first
through the little Wi-Fi box behind the counter, and it can read anything that passes. And yet, in less than a
fifth of a second, a padlock appears. So how do your laptop and the bank agree on a secret key while the box
reads every word, and that fast? It's tempting to think the padlock hides everything, from the very first word.
Hold that thought.

SCREEN: Title card. The laptop and the bank fade in, then the box and the lifelines. A packet crosses; a yellow
eye opens on the box's line ("reads all it can"). A large gold padlock appears, then a "?". Caption: "the padlock
hides everything, from the first word?"

## Scene 2 · Every question costs a wait · 0:35–1:20 · [FAMILIAR] [PAIN] [WISH]

VO: Let's put the bank 70 milliseconds away, there and back. That's one round trip, and every wait for an answer
costs one. First, the two programs open a TCP connection, the protocol underneath that delivers bytes in order.
That's one round trip already. Now, the careful way to set up a lock. Ask which kinds of key exchange the bank
accepts, and wait. Then send your half, and wait for the bank's. Two more round trips before your payment can
leave. TLS 1.2, the version before, needed two as well. Wouldn't it be nice to skip the asking?

SCREEN: A dot goes there and back. Row 0: "TCP's handshake: one round trip", "70 ms". Four grey ghost rows:
"which kinds of key exchange do you accept?" (105 ms), "these kinds" (140), "my half" (175), "my half" (210).
Caption: "two more round trips: the payment leaves at 210 ms". The ghosts fade.

## Scene 3 · Ordering abroad · 1:20–2:10 · [ANALOGY] [MAP] [JOKE:pivot]

VO: Picture a café abroad. You're not sure if the cashier speaks English or French. You could ask, and wait.
Instead, you say your order twice, in English and in French. The cashier answers in French. One whole wait,
saved. Let's map it. Each language is a kind of key exchange, which TLS calls a group. Your order in each
language is a key share, your half of the exchange, made in advance for each group you guess. The cashier's
answer is the bank's reply.

SCREEN: The box and TCP row dim. The actors become "you, a traveller" and "the cashier, in a café abroad". Ghost
rows "English or French?" / "French." appear and are dropped; then "a coffee, please / un café, s'il vous
plaît" → and "in French: coming right up" ←. "English" and "French" become "group 1" and "group 2", then "key
share 1" and "key share 2". The row labels turn into "ClientHello: api.pay.test · two key shares" and
"ServerHello: picks one group, and its key share"; the actors and the box come back.

NOTE: The light moment is the traveller's trick itself; it is the explanation of the guess.

## Scene 4 · Two open hellos · 2:10–3:00 · [SHOW] [BREAK of the analogy] [LOOP-PAYOFF]

VO: So your laptop's first message, the ClientHello, carries the guesses. It names the server, api.pay.test,
lists the methods it accepts, and carries two key shares. The bank answers with the ServerHello. It picks one
group, and sends its own key share. Here the café picture stops: saying it twice makes nothing secret. The secret
comes from this lesson's first section. Each side keeps a secret at home, and sends only a public value. Each
mixes its own secret with the other's public value, and both get the same key. The box saw both public values,
and can't. And notice, the box read both hellos. The padlock doesn't hide the first words: the box knows you're
talking to api.pay.test.

SCREEN: Dots run along rows 1 and 2; a yellow eye opens on the box's line for each; "the Wi-Fi box saw:
api.pay.test, both sides' key shares". State lines: "a secret, kept at home" (gold) on both ends, then "the same
key" (green); the box: "can't work it out" (red). Caption: "the two hellos are open: the padlock starts after
them".

## Scene 5 · A lock with nobody behind it · 3:00–3:30 · [BREAK] [JOKE:release]

VO: So we have a key the box can't work out. Are we done? Against a box that only listens, yes. But the box can
also talk. It can play the bank to your laptop, and your laptop to the bank. Two keys, and it reads everything
in between. Both locks work perfectly. They lock you in with the wrong person. A lock on its own proves nothing
about who holds the other key.

SCREEN: The box's outline turns red: "plays both parts". "key A, with you" between the laptop and the box, "key
B, with the bank" between the box and the bank; state lines "key A" and "key B". Caption: "a lock on its own
proves nothing about who holds the other key".

## Scene 6 · The locked flight · 3:30–4:25 · [SHOW] [NAME] [ANALOGY callback]

VO: That's what the rest of the bank's reply is for. Everything after the ServerHello is locked. First, the
certificate, the bank's passport from the last section: this public key belongs to api.pay.test, signed by a
certificate authority. But anyone can copy a passport. So the bank also signs every byte of the conversation so
far, with a private key that never leaves the bank. That's CertificateVerify. Last, Finished: a short code worked
out from every byte so far. If the box had changed one word of the hellos, the codes wouldn't match. The box has
a copy of the passport, but not the private key. It can't make the signature, so your laptop's check fails, and
it hangs up. With the real bank, every check passes. Your laptop sends its own Finished, with your payment in the
same flight, and new keys lock your data.

SCREEN: Row 3 (gold, ←): a padlock, then "certificate,", "CertificateVerify,", "Finished" appear one by one; a
gold padlock on the box's line; the box saw "then only sizes and timing". The box's fake reply (red arrow,
"a copied certificate, no private key") gets a red cross; the laptop's state: "check fails: hangs up". Then row 4
(gold, →): "Finished, and your payment"; both state lines become "new keys, for data".

## Scene 7 · Count the wait · 4:25–4:50 · [PREDICT] [PAUSE] [SHOW]

VO: So how long before the bank sees the first byte of your payment? Pause and guess. (three seconds) TCP, 70
milliseconds. The two hellos, one round trip, 70 more. Then the payment's one-way trip, 35. That's 175
milliseconds. The careful way would take 245.

SCREEN: Countdown bar. Arrival times appear: 70 ms (row 0), 140 ms (rows 2 and 3), 175 ms at the bank (row 4).
Caption: "70 + 70 + 35 = 175 ms", then "175 ms, where asking first would take 245 ms".

## Scene 8 · Name it, and three guardrails · 4:50–5:30 · [NAME] [GUARDRAIL]

VO: This opening exchange is the TLS handshake: the messages two programs swap before any real data. TLS 1.3
needs one round trip, because your laptop guesses. Three guardrails. A wrong guess costs one more round trip: the
bank answers with a HelloRetryRequest, and your laptop says hello again. That's why clients always send a share
for x25519, which nearly every server accepts. Every new connection pays both round trips. So programs keep a
connection pool, a set of open connections they reuse, and pay once. And the hellos are open. The box still sees
the name, the addresses, and how much you send.

SCREEN: The three handshake rows pulse. Numbered captions; the ClientHello pulses red; then the TCP and hello rows
pulse; then the eyes and the box's panel glow.

## Scene 9 · The moral, and a check · 5:30–6:00 · [MORAL] [RECAP] [PRINCIPLE] [PREDICT] [PAUSE] [LOOP-PAYOFF]

VO: So: two open hellos carry the guesses. Everything after is locked, and a signature only the real bank can make
proves who answered. Guess, so you don't have to ask. Sign, so the lock means something. One quick check. The bank
accepts neither group your laptop guessed. How long before it sees your payment now? Pause and think. (three
seconds) 245 milliseconds: one extra round trip for the HelloRetryRequest. A wrong guess costs exactly what asking
first would have.

SCREEN: The eyes glow, then the padlocks, then "CertificateVerify". Caption "guess, so you don't have to ask; sign,
so the lock means something". For the check, the ClientHello pulses red and a countdown runs; then the 175 ms at
the bank becomes a red 245 ms.

---

### Beat check

- Opens with QUESTION (scene 1) from a felt situation (paying on café Wi-Fi), and plants the padlock loop.
- FAMILIAR + PAIN + WISH (scene 2): round trips, TCP, the careful way and its cost.
- ANALOGY + MAP (scene 3) said out loud: language = group, the order in each language = key share, the cashier's
  answer = ServerHello. Its limit is said in scene 4 ("saying it twice makes nothing secret").
- BREAK: the padlock loop (scene 4), the box that plays both parts (scene 5), the copied certificate (scene 6).
- PREDICT with PAUSE: scene 7 and the check in scene 9; SHOW right after each.
- NAME after the picture: group and key share (scene 3), ClientHello and ServerHello (scene 4), CertificateVerify
  and Finished (scene 6), the TLS handshake (scene 8).
- GUARDRAIL (scene 8) and MORAL (scene 9) come last. Light moments: the traveller's two-language order, "they lock
  you in with the wrong person", "a wrong guess costs exactly what asking first would have".

### Accuracy notes for the producer

- The careful way in scene 2 is a simplified "ask, then send your half"; TLS 1.2's real messages differ (its first
  round trip also carries the certificate), but it too needed two round trips before the client could send data,
  as the lesson says. 245 ms = 70 (TCP) + 140 (two round trips) + 35.
- The JDK 25 client sends two key shares (X25519MLKEM768 and x25519); the lesson's server picked X25519MLKEM768.
  The video says "two key shares" and "group 1, group 2" and names x25519 only in the guardrail.
- The ClientHello also carries a random number, the supported versions and ALPN; the video shows the server name,
  "methods" (cipher suites) and the key shares.
- The handshake keys (made after the ServerHello) lock the certificate messages; the application keys lock data.
  The video shows this as "the same key", then "new keys, for data".
- Finished is a MAC over the handshake so far with a key from the shared secret; CertificateVerify is a signature
  over the same bytes with the leaf's private key. If the box changed an open hello, both ends' views of the
  conversation differ, so the checks fail.
- "Less than a fifth of a second": in this example the laptop has the bank's Finished at 140 ms.
- What the box still sees (scene 8) is section 3's subject: addresses, the server name in the ClientHello, record
  sizes and timing. ECH and 0-RTT are left to the lesson.
