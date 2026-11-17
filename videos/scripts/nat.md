# One address, many computers: how a home router shares it

- Slug / scene: `nat`, `videos/scenes/nat.py:Nat`
- Lesson: `net-03`, section 2, "Sharing one public address: private blocks and NAT"
- Audience / level: a complete newcomer. Knows what an IP address is only as "a computer's number on the network".
- Length: 4:41 (~700 words of narration at the Kokoro voice's ~180 wpm, plus two pauses and silent builds)
- Poster: `216` s (both table lines, port 3417 in place)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: my phone, laptop and TV all show the internet one address, so how does each reply
  find the right device?
- Misconception to steelman and break: "rewriting the address is enough". Broken when two inside computers use the
  same port to the same server: outside, their packets look identical, so a reply could belong to either.
- Concept chain: too few addresses → private blocks, reused everywhere → a reply to a private address has nowhere to
  go → the router rewrites the source and writes it down → two connections collide unless it rewrites the port too →
  the table's costs: nothing gets in without a line, quiet lines vanish (hardest last)
- Analogy family: an office building with one street address and a mailroom. Building's address = the router's
  outside address; mailroom = the router; desks = the computers inside; the clerk's ledger = the router's table.
  Breaks (in the lesson's next section) when the ledger forgets a line.
- Open loops: "how do the replies find the right one?" planted in scene 1 → answered in scene 8; "someone at the
  door" wished for in scene 3 → granted by the mailroom in scene 4.
- Assumptions: the lesson's lab network and stepper: client 10.10.1.10 and peer 10.10.1.20 inside; router 10.10.1.2
  inside and 10.10.2.2 outside; server 10.10.2.20, port 8080; both connect from port 41000; peer's connection gets
  outside port 3417 (the lesson's Try it run).

## The one picture

After a short hook (your phone and a website), one diagram for the rest: client and peer on the left ("inside"), the
router in the middle with one address on each side (outside in yellow), the server on the right ("outside"). A packet
card above the inside wire shows the packet as it looks inside; a card above the outside wire shows it outside, so
every rewrite is a before and after. The router's table grows at the bottom, one line per connection. Yellow means
rewritten, green means delivered, red means a clash or a drop.

## Scene 1 · The hook · 0:00–0:35 · [QUESTION] [LOOP-PLANT]

VO: Look at your phone's Wi-Fi settings at home. It shows an IP address, such as 192.168.1.23. Now ask a website which
address you're calling from. You get a different one: the same one your laptop and TV get. Three devices share one
address on the internet. Yet the film goes to the TV, and the messages to your phone. How does the box on the wall keep
them apart? And here's the odd part. Millions of homes use 192.168.1.23 right now.

SCREEN: Your phone (192.168.1.23) and a website ("you're calling from: one other address"), then a laptop and a TV.

## Scene 2 · Why private addresses · 0:35–1:10 · [FAMILIAR]

VO: Start with a counting problem. An IP address has 32 bits, so there are about 4.3 billion of them. Today there are
more mobile phone contracts in the world than that. So three blocks were set aside for private use: addresses starting
with 10, with 172.16 to 172.31, and with 192.168. Anyone may use them inside their own network, as many times over as
they like, and no router on the internet carries packets to them.

SCREEN: Captions; the three blocks (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) in green; "no router on the internet
carries packets to them" in red.

## Scene 3 · A reply with nowhere to go · 1:10–1:55 · [SHRINK] [PAIN] [WISH]

VO: Let's watch it on the lab network. Inside, client and peer have private addresses. Outside sits a server. In
between, a router, with one address on each side. Client opens a connection to the server, from port 41000 to port
8080. A port is the number that picks one program on a computer. The question gets there. But the answer is addressed
to 10.10.1.10, and the server has no way back to it. Out on the internet, no router could even tell which of a million
homes you mean. What we need is someone at the door who takes each reply to the right desk.

SCREEN: The lab diagram builds. Card: "from 10.10.1.10:41000, to 10.10.2.20:8080"; a dot runs to the server. The answer's
card turns "to 10.10.1.10:41000" red; its dot stops halfway: red cross, "no way back to 10.10.1.10".

## Scene 4 · The mailroom · 1:55–2:30 · [ANALOGY] [MAP]

VO: Think of an office building with one street address. Every letter leaves through the mailroom, which writes the
building's address as the return address. Replies come back to the mailroom, and a clerk walks each one to the desk
that sent the original. Map it. The mailroom is the router. The desks are the computers inside. And the building's
street address is the router's outside address, 10.10.2.2.

SCREEN: Tags "the mailroom" over the router and "inside: the desks"; the outside address glows.

## Scene 5 · Rewrite, and write it down · 2:30–3:15 · [SHOW] [NAME]

VO: So the router rewrites the source of every packet going out, to its own outside address. And before the packet
leaves, it writes down what it did: the inside address and port, the outside ones, and the far end. The server sees a
packet from 10.10.2.2, an address on its own network, so it can answer. The router finds the line, rewrites the
destination back to 10.10.1.10, and sends it inside. This is NAT: network address translation.

SCREEN: Inside card "from 10.10.1.10:41000"; outside card "from 10.10.2.2:41000" (yellow). The table appears: inside,
outside, far end, then line 1. The answer's card "to 10.10.2.2:41000"; line 1 glows; the inside card "to
10.10.1.10:41000" (green); a green dot reaches client.

## Scene 6 · Two connections, one port · 3:15–4:05 · [PREDICT] [PAUSE] [BREAK] [SHOW] [JOKE:release]

VO: Now peer connects too: same server, and by chance, the same port, 41000. If the router rewrites only the address,
what will peer's packet look like outside? Pause and guess.

(three seconds)

Exactly like client's: 10.10.2.2, port 41000, to the same server. So when an answer comes back to port 41000, whose is
it? The router can't tell. So the router rewrites the port too. It gives peer's connection a different outside port. In
the lesson's run, it picked 3417. Now every line is different, and every answer can be matched. In the mailroom, the
ledger says: replies for 41000 go to client, replies for 3417 go to peer. Nearly every NAT you'll meet works this way.
Linux calls its version masquerade. And the server? As far as it knows, it's chatting with one very busy computer.

SCREEN: Line 2 appears with its outside "10.10.2.2:41000" in red, next to line 1's; a reply comes back and the router
flashes red. Then line 2's outside becomes "10.10.2.2:3417" (yellow); replies run to client and to peer. Caption "one
line per connection, addresses and ports (Linux: MASQUERADE)".

## Scene 7 · Two costs · 4:05–4:35 · [GUARDRAIL]

VO: This trick has two costs. First, nothing outside can start a conversation. A packet that arrives unasked matches no
line, so it goes nowhere. Second, the table can't grow forever, so a line that stays quiet for too long is crossed
out. Neither end is told. Client still thinks its connection is open. Its next packet matches nothing, and is dropped.
The next section shows how long routers wait, and what to do about it.

SCREEN: A red "new, from outside" card; its dot stops at the router. Line 1 is struck through; client's next packet
stops with a red cross.

## Scene 8 · The moral, and a check · 4:35–5:00 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So how does the film find the TV? The router wrote it down: one line per conversation, rewritten on the way out
and on the way back. One quick check. A third computer inside connects to the same server, also from port 41000. What
does the router do? Pause and think.

(three seconds)

It picks another free outside port, and writes a third line.

SCREEN: Line 1 comes back; a third line "a third computer, port 41000 | ? | 10.10.2.20:8080"; countdown; the "?"
becomes "10.10.2.2: another free port" (green).

---

### Beat check

- QUESTION from a felt mystery (scene 1); FAMILIAR counting problem (scene 2); PAIN and WISH (scene 3).
- ANALOGY + MAP (scene 4) before the mechanism is named; NAME after the SHOW (scene 5).
- PREDICT with PAUSE and the naive model broken (scene 6), and the check (scene 8).
- GUARDRAIL (scene 7) and MORAL (scene 8) last. Light moments: "millions of homes" (0:30), "one very busy
  computer" (4:00).

### Accuracy notes for the producer

- In the lab, the router's outside address 10.10.2.2 is itself in 10.0.0.0/8; it plays the public address. The video
  calls it "the outside address", never "public".
- The lesson's figures: about 4.3 billion IPv4 addresses; more mobile contracts than that; RFC 1918's three blocks.
  IANA's 2011 run-out and carrier-grade NAT (100.64.0.0/10) are left to the lesson.
- Port 3417 is from the lesson's Try it run; Linux picks a free port, so another run may differ.
- The unasked packet in scene 7 is drawn without a source address: what matters is that no line has its far end.
  The lesson adds that it ends at the router itself, which has nothing listening on 41000.
- Idle timeouts (5 days for TCP in Linux conntrack, 350 seconds on an AWS NAT gateway) and the fixes are section 3.
- Spoken forms via `SAY`: dotted addresses as "dot", 192.168 as "one ninety-two dot one sixty-eight", 8080 as
  "eighty eighty", 3417 as "thirty-four seventeen".
