# Envelopes inside envelopes: how one request is wrapped and read

- Slug / scene: `net-encapsulation`, `videos/scenes/net_encapsulation.py:NetEncapsulation`
- Lesson: `net-01`, section 1, "Envelopes inside envelopes: how the layers wrap one request"
- Audience / level: a complete newcomer. Can read a little code; knows nothing about networks, headers or routers.
- Length: 5:13 (~790 words of narration at the Kokoro voice's ~180 wpm, plus two pauses and silent builds)
- Poster: `205` s (after the router: new label, ticks on the parcel, envelope and letter)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: if the page seems to come down one wire, how does a stranger's machine in the middle
  know where to pass my request, and how does the far computer know which program it's for?
- Misconception to steelman and break: "one long wire, the request rushing along it in one piece". Broken when the
  router appears in the middle of the wire and rewrites the outer label, while everything inside arrives untouched.
- Concept chain: the request carries no usable address → each layer adds a header in front (encapsulation) → a router
  reads only the outer layers and rewrites the label → the receiver unwraps by following "what's inside" fields
  (hardest last)
- Analogy family: posting a letter. Letter = HTTP request, envelope with a flat number = TCP header and port, parcel
  with the street address = IP header, courier label naming the next depot = Ethernet header and MAC, the depot =
  a router.
- Open loops: "where to pass it?" planted in scene 1 → paid off in scene 5; "which program?" planted in scene 1 →
  paid off in scene 6; "one long wire" planted in scene 1 → broken in scene 5; "every wrapper earns its place"
  planted in scene 4 → paid off in scene 6.
- Assumptions: numbers are the lesson's real capture (74, 106, 126, 140 bytes; ports 57236 → 80; 172.20.0.2 →
  104.20.23.154; TTL 64; MACs b6:99:4a:b0:80:7f → 22:d2:d5:a2:32:a3; EtherType 0x0800; protocol 6). One router
  stands for the many on a real path.

## The one picture

Top row: your laptop (left), the server (right), joined at first by one long wire; the router appears in its middle in
scene 5. Below: the request, then the nested wrappers around it, header bands on top: the letter (white), TCP's
envelope (blue), IP's parcel (green), Ethernet's courier label (gold). The analogy's nouns sit in a grey column on the
left, the running size on the right. A gold chip is the frame moving along the wire. Yellow means "look here", green
ticks mean unchanged, same places and colours throughout.

## Scene 1 · One long wire? · 0:00–0:35 · [QUESTION] [LOOP-PLANT]

VO: Picture yourself at a café with a laptop. You type the address of a web page, press Enter, and the page appears
in about a twentieth of a second. It's easy to picture one long wire from your laptop to the computer that sent it,
with your request rushing along it in one piece. But that computer is many links away, behind
machines owned by strangers. So how does a stranger's machine know where to pass your request? And when it arrives,
how does the far computer know which program it's for? Hold those two questions.

SCREEN: Laptop and server boxes; a wire grows between them and a white chip runs along it. A yellow "?" in the middle
of the wire; captions "1. where to pass it?" and "2. which program is it for?".

## Scene 2 · The request, and what it's missing · 0:35–1:10 · [FAMILIAR] [PAIN] [WISH]

VO: Let's look at the request. Ask curl, a program that fetches web pages from the command line, for example.com, and
it writes these 74 bytes of HTTP, the language that browsers and web servers speak. Now notice what's missing.
There's a site name, but no number for the computer, no number for the program, and nothing the card next door could
use. curl hands these bytes to the kernel, the core of the operating system. On the way down, the kernel has to add
every address. What we want: every machine on the way should find the one address it needs, without reading your
letter.

SCREEN: The machines move up to the top row. The four request lines appear large, "74 bytes" under them. Three dashed
grey slots: "computer: ?", "program: ?", "next card: ?". Caption for the wish.

## Scene 3 · Posting a letter · 1:10–1:40 · [ANALOGY] [SHRINK]

VO: Think of posting a letter. You write the letter. It goes in an envelope with a flat number on it. That envelope
goes inside a parcel with the street address. Then a courier sticks a label on the outside. It says only which depot
to drive to next. Each wrapper treats what's inside as sealed.

SCREEN: The request shrinks into a white letter. A blue envelope wraps it ("flat 80"), a green parcel wraps that
("street address"), a gold label wraps everything ("next depot"). Grey nouns on the left: letter, envelope, parcel,
courier label. Each band glows in turn on "sealed".

## Scene 4 · The same picture in your laptop · 1:40–2:45 · [MAP] [SHOW] [NAME] [JOKE:release] [LOOP-PLANT]

VO: Now the same picture in your laptop. The letter is curl's request: 74 bytes of HTTP. Each layer puts a header in
front: a few bytes with its own addresses. The envelope is TCP's header, from the layer that picks the program and
keeps the bytes in order. 32 bytes, with the two ports. 74 bytes become 106. The parcel is IP's header: 20 bytes, with
the two computers' IP addresses and a counter called the time to live. 126 bytes. The courier label is Ethernet's
header: 14 bytes, with two MAC addresses, the names of network cards on this one link. 140 bytes, sent as one frame. This wrapping is called encapsulation. Each layer wraps what it was handed, and never looks inside. That's 66
bytes of wrapping around 74 bytes of letter. Online shops would be proud. But every wrapper earns its place, as we're
about to see.

SCREEN: Each band gets its technical name and field: "TCP 32 bytes, to port 80", "IP 20 bytes, to 104.20.23.154,
TTL 64", "Ethernet 14 bytes, to 22:d2:d5:a2:32:a3". The size on the right counts 74 (a message), 106 (a segment), 126
(a packet), 140 (a frame). Caption "encapsulation: each layer wraps what it was handed". Then "66 bytes of wrapping,
74 bytes of letter".

NOTE: Each mapping is said out loud as its band changes. The joke comes after the build, never inside it.

## Scene 5 · The depot · 2:45–3:50 · [PREDICT] [PAUSE] [SHOW] [BREAK] [LOOP-PAYOFF] [JOKE:is-the-explanation]

VO: Back to the long wire. It isn't one wire. Your laptop's card can only reach the cards on its own link, so the
label names the next card: the router's. A router is a machine on two links that passes packets from one to the next,
like a courier's depot. When the frame leaves the depot for the next link, which labels will have changed? Pause and
guess.

(three seconds)

The router takes off the courier label, reads the street address, and lowers the time to live from 64 to 63. Then it
sticks on a new label, for the next card on the next link. It never opened the envelope. The IP addresses and the ports
arrive as they left. Only the label changed. So there never was one long wire. There's a chain of links, and the outer
label is rewritten on each one. That answers our first question: each machine on the way reads only the street
address. A router is the perfect courier: quick, and not the least bit curious. It never reads TCP or HTTP, so those
layers can change without it noticing.

SCREEN: The router drops into the middle of the wire. MAC labels appear under the laptop and the router; the label's
"to 22:d2:d5:a2:32:a3" and the router's MAC glow together. The gold chip crosses the first link. Yellow "?" beside each
band, countdown bar. Then the gold wrapper lifts off, the IP "to" field glows, "TTL 64" becomes a yellow "TTL 63", and
a new gold wrapper closes around ("to the next card"). Marks: a yellow "new" by the label, green ticks by the parcel,
envelope and letter.

## Scene 6 · Unwrapping at the server · 3:50–4:30 · [BREAK of the analogy] [SHOW] [LOOP-PAYOFF] [PRINCIPLE]

VO: The frame reaches the server. Its card keeps it, because the label names that card. Now the kernel unwraps, in the
opposite order. How does it know what's inside each wrapper? Here our post office picture needs a patch. A paper
envelope doesn't say what's in it. Every header here does. Ethernet's type field says 0x0800: an IP packet is inside.
Off comes the label. IP's protocol field says 6: a TCP segment is inside. Off comes the parcel. And TCP's port, 80,
picks the program: the web server. It reads exactly the 74 bytes curl wrote. That answers our second question. Every
header says what's inside it. The receiver follows the labels, and never guesses.

SCREEN: The chip crosses the second link. "type 0x0800" appears in the label's band and glows; caption "0x0800: an IP
packet is inside"; the label peels off. "protocol 6" replaces the TTL and glows; the parcel peels off. "to port 80"
glows; the envelope peels off; the letter glows, "74 bytes". Caption, in yellow: the rule.

## Scene 7 · Two limits · 4:30–4:55 · [GUARDRAIL]

VO: Two limits. Some boxes on the way do rewrite the street address and the port. Lesson 3 of this track meets one.
And a big answer doesn't fit in one frame. That comes later in this lesson.

SCREEN: Captions "limit 1: some boxes do rewrite the street address and the port (lesson 3)", "limit 2: a big answer
doesn't fit in one frame (later in this lesson)".

## Scene 8 · The moral, and a check · 4:55–5:30 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So, one long wire? No. A letter in three wrappers, and a chain of depots that each read only the outside one. On
the way down, each layer adds a header. On the way up, each layer reads one, and takes it off. One quick check. Put a
second router on the path. When the frame leaves it, what will the time to live say? Pause and think.

(three seconds)

62. Each router lowers it by one, and puts on a new label. Everything inside the label arrives as it left.

SCREEN: The four wrappers rebuild around the letter for the recap. For the check, a second router joins the top row;
countdown; the TTL counts 64, 63, 62 as the chip passes each router.

---

### Beat check

- Opens with QUESTION (scene 1): the felt picture of one wire and two questions the viewer can't answer yet.
- FAMILIAR + PAIN + WISH (scene 2) before any layer is named; ANALOGY (scene 3) before any header; MAP said out loud
  (scene 4).
- PREDICT with PAUSE (scene 5, and the check in scene 8); SHOW right after each.
- BREAK: the "one long wire" model (scene 5) and the analogy's limit, envelopes don't say what's inside (scene 6).
- NAME after the SHOW: header, encapsulation, segment, packet, frame (scene 4), router (scene 5).
- GUARDRAIL (scene 7) and MORAL (scene 8) last. Light moments: online shops (2:35), the incurious courier (3:40).
- Open loops paid off by name: "our first question" (scene 5), "our second question" (scene 6).

### Accuracy notes for the producer

- All numbers come from the lesson's real capture: 74 bytes of HTTP; TCP 32 (20 plus 12 of options); IP 20; Ethernet
  14; ports 57236 → 80; IP 172.20.0.2 → 104.20.23.154; TTL 64; EtherType 0x0800; protocol 6. The capture was made in
  the lab box (a Docker container); the video calls it "your laptop" to match the opening's café.
- The video shows only destination addresses on the bands; the narration says each header holds two.
- One router stands for the many on a real path. The new label's destination is drawn as "the next card": the lesson
  does not give the next hop's MAC.
- Left out (in the lesson): the socket, the TCP flags and sequence numbers in detail, the IP checksum that the router
  must recompute after lowering the TTL, the 4-byte frame checksum the card adds, UDP's protocol number 17.
- "A big answer doesn't fit in one frame" points to section 3; the waits before the request leaves (section 2) are left
  to the lesson. HTTP not knowing whether it crossed cable, Wi-Fi or a mobile network is also left to the lesson.
- Spoken forms via `SAY`: dotted addresses as "dot", 0x0800 as "hex zero eight zero zero".
