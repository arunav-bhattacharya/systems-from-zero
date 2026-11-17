# What is a TCP connection? Three messages and two random numbers

- Slug / scene: `tcp-handshake`, `videos/scenes/tcp_handshake.py:TcpHandshake`
- Lesson: `net-07`, section 0, "How a connection opens: three messages and two random numbers"
- Audience / level: a complete newcomer who has read the lesson on UDP and the sockets API (numbered messages,
  ACKs, resending). Knows nothing about TCP, kernels or sequence numbers.
- Length: 5:06 (~770 words of narration; Kokoro speaks about 180 words a minute, and the guesses, the rolling
  numbers and the silent sends bring it down to about 150)
- Poster: `POSTER=244.5` (the three named messages, both kernels' notes and "the connection" between them)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: before the payment moves, the two machines trade three messages full of strange
  numbers. Why three, why those numbers, and what is a "connection" when no wire belongs to these two?
- Misconception to steelman and break: "just number the bytes from 0 every time". It works once; then a stuck
  copy from the last connection on the same two ports fits the new one exactly, and one tap of a card becomes two
  payments.
- Concept chain: TCP numbers bytes, and an ACK means "every byte before this one" → so both sides must agree a
  start → 0 breaks (stray copies), so each side picks a random start → each side must tell its number and know it
  arrived (the phone call) → three messages, +1 for the first → the agreed numbers are the connection → cost: one
  round trip (hardest last: the +1 arithmetic, then the check)
- Analogy family: a phone call on a bad line ("Can you hear me?" "Yes, I hear you. Can you hear me?" "Yes.")
  and a door code of 0000 for a guessable start
- Open loops: "what is a connection, anyway?" planted in scene 1 → paid off in scene 7 ("these numbers, kept in
  both kernels"); the stuck copy in scene 3 → paid off in scene 8 (it no longer fits)
- Assumptions: numbers are the lesson's capture (ISNs 244700535 and 4042781690, ports 50744 and 9000, the
  17-byte line `AUTH 4242 100.00`, 70 ms to a bank, a tenth of a millisecond on the lab network). The narration
  says "the one ending in 691" and "536" to keep long numbers short; the screen shows them in full.

## The one picture

Top: the card reader (blue, left) and the server (gold, right), joined by a wire with a router in the middle.
Parcels (rounded chips) travel along the wire and pass behind the router; blue parcels come from the reader,
gold from the server, red means a stray that doesn't belong. Under each machine sits its kernel's notes (mine,
yours). Centre: the 17 bytes of the payment as cells with their numbers. Bottom: the log of the three messages,
which starts as the phone call and turns into TCP. Blue numbers are always the reader's, gold the server's. At
most six things on screen.

## Scene 1 · The question · 0:00–0:29 · [QUESTION] [LOOP-PLANT]

VO: A card reader is about to send one short line to a server. It's a made-up request: approve 100.00 on the
card ending 4242. But before a single byte of it moves, the two machines trade three short messages, full of
odd numbers like 244,700,535. Why three? And what is a connection, anyway? There's no wire that belongs to just
these two.

SCREEN: The reader and the server, the wire and the router. The chip `AUTH 4242 100.00` above the reader. Three
quick parcels cross (blue, gold, blue); a big blue 244,700,535 and a "?" in the centre. Grey parcels from the rest
of the internet run through the router.

## Scene 2 · The pieces we know · 0:29–1:20 · [FAMILIAR] [SHRINK]

VO: First, the pieces. Data travels in packets: small parcels of bytes, addressed to a machine, and to a port,
the number of one program on it. Here the reader uses port 50744, and the server port 9000. On the way, routers
pass the parcels along, for everyone.

In UDP and the sockets API, we numbered each message from 0, the other side answered with an ACK, got it, and we
resent anything unanswered.

TCP does that work for us. It's a set of rules followed by each machine's kernel, the core of its operating
system. And it numbers every byte, not every message. And its ACK means: I have every byte before this one. ACK 10
means bytes 0 to 9 are here. So before the first byte travels, both sides must agree where the numbering starts.

SCREEN: Ports appear in both boxes; a parcel runs across; grey parcels pass through the router. Caption for the
UDP recap. The request chip turns into 17 byte cells numbered 0 to 16 (the last is the newline). A brace over
cells 0 to 9: "ACK 10: I have bytes 0 to 9". The 0 under the first cell pulses: "where does the numbering
start?"

## Scene 3 · The obvious fix, broken · 1:20–1:57 · [BREAK] [WISH] [JOKE:soften]

VO: The obvious answer: always start at 0. And to be fair, it works. The reader sends the payment, bytes 0 to 16,
the server takes it, and the connection closes. But a copy of that parcel got stuck for a while in a router's
queue. A second later, the reader opens a new connection, on the same two ports, and starts at 0 again. Now the
stuck copy turns up. It fits the new connection perfectly, so the server takes it. One tap of a card, two payments.

Well... the customer will have questions. What we want are numbers an old connection would never have used.

SCREEN: A blue parcel "bytes 0 to 16" crosses; a card under the server, "the server took", gets a row. A copy
drops out of the router into a slot below it: "stuck in a queue". Caption "connection 2: same two ports, starts at
0 again". The stuck parcel rises, crosses and lands as a second, red row: "two payments".

NOTE: Be fair first (it works once). The joke is an understatement right after the failure, then the wish.

## Scene 4 · A random start · 1:57–2:24 · [JOKE:is-the-explanation]

VO: So each side picks its own starting number, a new one for every connection. Starting at 0 every time is like
a door code of 0000. It's the first thing anyone would try. TCP's rules mix a fast clock with the ports and a
secret, so every connection starts somewhere different, and an outsider can't guess where. Guess the numbers, and
you could slip your own bytes into somebody else's connection.

SCREEN: The kernel's notes appear under both machines. "mine" rolls through random numbers and settles: blue
244,700,535 for the reader, gold 4,042,781,690 for the server. "yours" shows "?". Captions carry the recipe.

## Scene 5 · The phone call · 2:24–2:59 · [ANALOGY] [MAP] [JOKE:pivot]

VO: Now each side must tell the other its number, and know that it arrived. You've had this problem on a phone
call with a bad line. One person says: can you hear me? The other says: yes, I hear you. Can you hear me? And the
first says: yes. Each person needs to know their own voice gets through, so each one asks, and each one answers.
That's four lines, but the middle two fit in one breath, so it takes three.

TCP works the same way. Can you hear me is: here's my starting number. Yes, I hear you, is an ACK. And the middle
message carries both.

SCREEN: The "?" rows glow. Three parcels cross with the call's words, and the log fills: → "can you hear me?",
← "yes, I hear you. can you hear me?", → "yes". The middle row splits into its two halves. The map in captions.

## Scene 6 · Three messages, with numbers · 2:59–3:44 · [PREDICT] [PAUSE] [SHOW]

VO: First message. The reader says: my bytes start after 244,700,535. The server answers: the next byte I expect
from you is... The reader's number ends in 535. Pause and guess.

(three seconds)

536. One more. This first message carries no data, yet it uses up one number, so the answer is the start plus one.
In the same message, the server adds its own starting number. Third message. The reader answers: the next byte I
expect from you is the one ending in 691. Now both sides know both numbers, and the payment can go.

SCREEN: Each log row turns from the call into TCP. Parcels carry the numbers; the receiving side's "yours" fills
in. Row 2 shows "next I expect ?" during the countdown, then 244,700,536 and "+1". Ticks on both notes at the end.

## Scene 7 · The names · 3:44–4:04 · [NAME] [LOOP-PAYOFF]

VO: This exchange is the three-way handshake. Each message is named after its flag, a marker at the front: SYN,
short for synchronize, then SYN-ACK, then ACK. The starting numbers are called initial sequence numbers. And the
connection? It's these numbers, kept in both kernels. No wire belongs to these two.

SCREEN: SYN, SYN-ACK and ACK appear in a column before the rows. "the connection" in the centre with arrows to
both notes.

## Scene 8 · Where the phone picture breaks · 4:04–4:19 · [BREAK of the analogy] [LOOP-PAYOFF]

VO: The phone picture breaks in one place: a word never turns up a minute late. A packet can. Remember the stuck
copy? It carries the old connection's numbers, nowhere near this one's. It doesn't fit, so the server throws it
away.

SCREEN: The stuck copy reappears under the router (red, "old numbers"), crosses to the server and is crossed out:
"doesn't fit: dropped".

## Scene 9 · The cost · 4:19–4:35 · [GUARDRAIL] [JOKE:amplify]

VO: All this costs one round trip, there and back, before the payment moves. On the lab network, that's a tenth of
a millisecond. To a bank 70 milliseconds away, that's 70 milliseconds of small talk before every new connection.
So keep connections open, and reuse them.

SCREEN: A dot runs there and back: "one round trip". Captions with the two numbers and the rule; the three rows
glow on "small talk".

## Scene 10 · The moral, and a check · 4:35–5:06 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So, what is a connection? Two random starting numbers, swapped in three messages, and kept by both sides.

One quick check. The payment is 17 bytes, starting at byte 536. What number does the server's ACK carry? Pause and
think.

(three seconds)

553. The bytes are 536 to 552, and the ACK names the next one it expects.

SCREEN: The rows and notes glow in order. The 17 byte cells come back, numbered 536 to 552; a parcel carries them
across; "ACK ?" above, a countdown, then a gold parcel back and "ACK 553: the next byte I expect".

---

### Beat check

- Opens with QUESTION (scene 1) from a visible oddity (three messages, huge numbers) and plants "what is a
  connection?".
- FAMILIAR (scene 2): packets, ports, and the numbered messages and ACKs from the UDP lesson.
- BREAK of the obvious fix (scene 3) before the analogy; WISH right after.
- ANALOGY + MAP (scene 5), said out loud; its breaking point (scene 8).
- PREDICT with PAUSE (scene 6, and the check in scene 10); SHOW right after each.
- NAME after the walk: three-way handshake, SYN, SYN-ACK, ACK, initial sequence numbers (scene 7).
- GUARDRAIL (scene 9): the round-trip cost, and the rule that follows (reuse connections). MORAL and RECAP (scene 10).
- Light moments: the customer's questions (~1:52), the door code of 0000 (~2:03), the bad phone line (~2:28),
  small talk (~4:28).

### Accuracy notes for the producer

- The ISN recipe is RFC 9293's: a 4-microsecond clock plus a keyed hash of the addresses and ports. The video says
  each side picks a number; in reality the server picks its own when the SYN arrives.
- "It doesn't fit, so the server throws it away": a segment outside the receive window is not accepted (RFC 9293
  answers it with an ACK). Random ISNs make such overlap very unlikely; TIME-WAIT, in the lesson's last section,
  is the other half of the protection.
- The stuck copy is shown as a copy of the payment; the lesson only says a segment from the first connection was
  delayed in a router. Why there was a copy (a resend) is left out.
- The +1 is shown for the first message only. A FIN also uses up one number; the lesson covers it in section 3.
- The SYN options (MSS 1460, window scale, SACK) are left to the lesson.
- "ACK 10 means bytes 0 to 9 are here" is a toy example; the real ACK numbers are the capture's.
- Byte 16 of the payment is the newline that `echo` adds; the screen shows it as `\n`.
- Left to the lesson's aside, for length: an ACK comes from the other machine's kernel, so it does not mean the
  program there handled the payment.
