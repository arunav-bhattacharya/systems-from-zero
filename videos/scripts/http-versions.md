# One lost packet, three late answers: why HTTP/2 still waits

- Slug / scene: `http-versions`, `videos/scenes/http_versions.py:HttpVersions`
- Lesson: `net-11`, section 2, "One lost packet makes every HTTP/2 request wait"
- Audience / level: a complete newcomer. Has read the lesson's first two sections (HTTP/1.1's one request at a
  time; HTTP/2's numbered streams, told as the café's numbered tickets); knows nothing else about TCP.
- Length: 4:18 (~640 words of narration, plus the guesses and silent builds)
- Poster: `POSTER=80` (segment 1 lost, segments 2 and 3 waiting in the buffer, all three bars red at 0.63 s)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: HTTP/2 gives every request its own number on one connection, so if one packet is
  lost, why should more than one request wait?
- Misconception to steelman and break: "streams are independent, so a loss delays only its own stream" (broken
  by the lab's numbers: all three requests 120 ms late). Second fix tested: "go back to HTTP/1.1's three
  connections" (the loss hits one request, but that one waits 330 ms for a timer, and every connection pays its
  own handshakes).
- Concept chain: numbered streams share one connection → TCP delivers one ordered stream of bytes → a hole holds
  back every byte behind it (head-of-line blocking in TCP) → QUIC orders bytes per stream → it matters where loss
  is common
- Analogy family: the café from the lesson. Numbered tickets (section 1) for streams; the kitchen's one narrow
  hatch, trays in single file, for the TCP connection and its segments; a hatch per order for QUIC
- Open loops: "most people say one" planted in scene 1 → broken in scene 4; the café hatch → paid off by QUIC's
  "a hatch per order" in scene 7
- Assumptions: numbers are the lesson's Try it: three answers of 1,000 bytes, one segment each, 300 ms of work,
  50 ms each way; 0.509 s without loss, 0.627 s with one loss over HTTP/2; 0.514 s, 0.514 s and 0.841 s over
  HTTP/1.1

## The one picture

Left: the bank (green box) with three ready answers, one per stream (blue 1, teal 3, gold 5). Middle: the
connection, a pipe; segments are small squares numbered 1, 2, 3 in their stream's colour, travelling in single
file. Right: your app's computer (blue box): on top, the app's three streams (outlined while waiting, filled when
the answer arrives); underneath, TCP's receive buffer with three slots in byte order. Bottom: one bar per
request, how long it took, with a dashed "no loss" mark at 0.51 s. Same colours and places throughout; the pipe
changes shape for HTTP/1.1 (three thin pipes) and QUIC (one pipe with a lane per stream).

## Scene 1 · Numbered tickets · 0:00–0:30 · [FAMILIAR] [QUESTION] [LOOP-PLANT]

VO: Remember the café with numbered tickets? You order, you get a number, and the coffees come out in whatever
order they're ready. HTTP/2 works the same way. Many requests share one connection, and each one gets a number,
called a stream. So here's a question. If one packet on that connection gets lost, how many requests have to wait
for it? Most people say one. Keep your answer.

SCREEN: Title card. "the kitchen" and "the counter" with tickets 1, 3, 5; they fill in the order 3, 5, 1. The
boxes become "the bank" and "your app", and the pipe draws: "one connection". A "?" over the pipe.

## Scene 2 · Shrink it · 0:30–1:05 · [SHRINK] [SHOW]

VO: Let's shrink it. Your app asks the bank for three answers at once, on streams 1, 3 and 5. The bank needs 300
milliseconds for each. Then it sends each answer, 1,000 bytes, in one segment. A segment is TCP's word for one of
its packets. The path takes 50 milliseconds each way. With nothing lost, all three answers arrive together, about
half a second after the start.

SCREEN: Three answer cards in the bank. The app box splits: "TCP's receive buffer" with three dashed slots.
Segments 1, 2, 3 cross in single file, land in their slots and rise into streams 1, 3, 5, which fill. Three bars
grow to "0.51 s".

## Scene 3 · Predict · 1:05–1:25 · [PREDICT] [PAUSE]

VO: Now we drop one segment on purpose, the one carrying stream 1. Segments 2 and 3 arrive whole. Which requests
are late? Pause and guess. (three seconds)

SCREEN: A dashed "no loss" line at 0.51 s. Segment 1 stops halfway and gets a red cross; segments 2 and 3 reach
their slots. Countdown bar.

## Scene 4 · All three, and why · 1:25–2:20 · [SHOW] [BREAK] [JOKE:release]

VO: All three. Every one of them, about 120 milliseconds late. Here's why. TCP promises one stream of bytes,
delivered in order. To TCP, these three answers are bytes 1 to 3,000 of that one stream, and the first 1,000 are
missing. So segments 2 and 3 wait in TCP's receive buffer, complete, and your app gets nothing. Stream 5 has its
whole answer, sitting on the counter, and nobody may pick it up. Your app's computer keeps asking for the missing
bytes. About a round trip later, the bank sends them again. The hole fills, and TCP hands everything over at once.

SCREEN: Three red bars to "0.63 s". Slot 1 outlined red, "missing". Segments 2 and 3 pulse; the streams stay
empty; segment 3 wiggles. A white dot runs back to the bank ("please resend bytes 1 to 1,000"); segment 1 crosses
again, the hole fills, and all three rise together.

NOTE: The light line (the coffee nobody may pick up) comes right after the mechanism and restates it.

## Scene 5 · The café's hatch · 2:20–3:05 · [ANALOGY] [MAP] [NAME]

VO: Here's the café version. The kitchen makes coffees in any order, but every tray leaves through one narrow
hatch, in single file. Drop one tray, and every tray behind it waits until that coffee is made again, even the
ones that are ready. The hatch is the TCP connection. The trays are segments. And the orders are streams. This has
a name: head-of-line blocking, the first in line holding up everyone behind. HTTP/2 removed it from HTTP, and
kept it one layer down, in TCP.

SCREEN: The labels become "the kitchen", "one narrow hatch", "the counter"; the loss plays again quickly. Then the
labels go back one at a time as each part is mapped. Caption: "head-of-line blocking: the first in line holds up
everyone behind".

## Scene 6 · Back to three connections? · 3:05–3:35 · [BREAK] [GUARDRAIL]

VO: So, go back to HTTP/1.1, with three connections, three hatches? The lesson's lab tried that too. The loss hits
only one request, and the other two finish on time. But the unlucky one was 330 milliseconds late. With no segment
behind its hole, nothing told the bank quickly, so it waited for a timer. And every extra connection pays its own
handshakes.

SCREEN: The pipe becomes three thin pipes, "HTTP/1.1: three connections". Bars: connection 2 and 3 at 0.51 s,
connection 1 a red 0.84 s.

## Scene 7 · A hatch per order · 3:35–4:05 · [SHOW] [NAME] [LOOP-PAYOFF]

VO: The real fix gives every order its own hatch, on one connection. That's QUIC, the transport under HTTP/3. It
runs over UDP, and numbers the bytes of each stream separately. Lose the same segment. Segments 2 and 3 complete
streams 3 and 5, and go straight to your app. Only stream 1 waits for its resend.

SCREEN: One pipe with three lanes, "QUIC: a lane per stream"; the buffer becomes "QUIC: order per
stream", with dividers between the slots. Segment 1 is lost; segments 2 and 3 rise at once (bars at 0.51 s);
segment 1's resend arrives later (red bar, "+ one resend").

## Scene 8 · When it matters · 4:05–4:45 · [GUARDRAIL] [JOKE:is-the-explanation]

VO: Should everything leave HTTP/2, then? Not so fast. Inside a data center, a building full of servers, loss is
rare and a round trip takes a fraction of a millisecond. There, one HTTP/2 connection is a fine default. On a
phone with 1 percent loss, a busy connection hits several holes a second, and each one stalls every request in
flight. One loss also slows the whole connection's sending, for every stream at once. So measure under loss.
Testing on a clean office network is like testing an umbrella indoors.

SCREEN: Captions in green (data center) and red (phone); the pipe pulses red. "measure under loss, not on a clean
network".

## Scene 9 · The moral, and a check · 4:45–5:20 · [MORAL] [RECAP] [PRINCIPLE] [PREDICT] [PAUSE]

VO: So, how many requests wait for one lost packet? On HTTP/2, every one behind the hole. HTTP/2 removed the wait in
HTTP, not the wait in TCP. One quick check. This time segment 3 is lost, the one carrying stream 5, and segments 1
and 2 arrive. Over HTTP/2, which requests wait? Pause and think. (three seconds) Only stream 5. Segments 1 and 2
came before the hole, so TCP hands them over on time. A hole only holds up what's behind it.

SCREEN: Back to one TCP pipe. Segment 3 is lost; slot 3 outlined red. After the countdown, segments 1 and 2 rise
into streams 1 and 3; stream 5 stays empty.

---

### Beat check

- Opens with FAMILIAR (the numbered tickets the viewer just read) and the QUESTION, and plants "most people say
  one".
- SHRINK + SHOW (scene 2), PREDICT with PAUSE (scene 3 and the check), SHOW right after each.
- BREAK: "only its own stream" broken by the numbers (scene 4); "go back to HTTP/1.1" tested fairly (scene 6).
- ANALOGY + MAP (scene 5) after the break, to explain it, each part mapped out loud; the café's hatch comes back as
  "a hatch per order" for QUIC (scene 7).
- NAME after the picture: segment (scene 2), receive buffer (scene 4), head-of-line blocking (scene 5), QUIC
  (scene 7).
- GUARDRAIL (scenes 6 and 8) and MORAL (scene 9) last. Light moments: the coffee nobody may pick up, the umbrella
  tested indoors.

### Accuracy notes for the producer

- The numbers are the lesson's Try it (`H2Server.java`, curl, netem 50 ms each way, iptables dropping the first
  answer's segment once): 0.509 s without loss; 0.627 s for all three over HTTP/2 with one loss; over HTTP/1.1,
  0.514 s for two and 0.841 s for the one that lost its segment. Runs vary by a few tens of milliseconds.
- "Keeps asking for the missing bytes" stands for duplicate ACKs with SACK blocks (the stepper shows `Ack=55`,
  `SLE=1064 SRE=3142`); "a timer" is TCP's retransmission timeout, which fires when no later segment arrives to
  trigger a fast resend (lesson 8).
- QUIC's bar is drawn from the stepper's claim (only stream 1 waits for its resend); the lesson has no QUIC timing
  for this loss, so the bar is labelled "+ one resend" without a number.
- The check question has no timing either. Like HTTP/1.1's lonely loss, a lost last segment has no segment behind
  it, so its resend may wait for a timer; the video only says which streams wait.
- "Several holes a second at 1% loss" and "a round trip under a millisecond in a data center" are the lesson's
  figures. The congestion window is named only as "slows the whole connection's sending".
