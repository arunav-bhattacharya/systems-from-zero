# The most specific route wins: how a router picks the next step

- Slug / scene: `routing`, `videos/scenes/routing.py:Routing`
- Lesson: `net-04`, section 0, "How a router picks the next step: the most specific route wins"
- Audience / level: a complete newcomer. Knows an IP address only as "four numbers that name one machine".
- Length: 4:52 (~745 words of narration at the Kokoro voice's ~180 wpm, plus two pauses and silent builds)
- Poster: `214` s (client's table with 0, 16 and 24 bits, the /24 line boxed in green)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: nobody on the way knows the whole path, so how does each router know which way to send
  a packet? And when several lines of its list fit, which one does it use?
- Misconception to steelman and break: "read the list from the top and stop at the first line that fits". Client's
  table prints the default first, so that reading sends peer's packet to Docker's gateway, out toward the internet,
  to reach a computer on client's own wire.
- Concept chain: each router forwards alone → a table of blocks, not addresses → a block is a prefix (fixed bits) →
  when several lines fit, the most fixed bits wins, whatever the order → each router decides alone (hardest last)
- Analogy family: a chain of parcel sorting offices. Sorter = router; reading the address and dropping the parcel in
  the right van = forwarding to the next hop; pigeonholes for one street, the whole city and "everything else: the
  national hub" = /24, /16 and /0.
- Open loops: "how does each router know?" planted in scene 1 → answered in scene 7; "it also fits the default, hold
  that thought" planted in scene 4 → paid off in scene 5; the bouncing packet planted in scene 6 for section 1.
- Assumptions: the lesson's lab: client 10.10.1.10, peer 10.10.1.20, Docker's gateway 10.10.1.1 on lan; router
  10.10.1.2 with cards on lan, wan (server 10.10.2.20) and tunnel; router2 10.10.3.3; ledger 10.10.4.40 on dc.

## The one picture

Top row: client, router, router2, ledger, joined by lan (a shared wire), tunnel and dc. Below: Docker's gateway and
peer on lan, the server on wan. A yellow card at the top names the packet's destination. Below the network, a routing
table (router's, then client's). Yellow dots are packets; a highlighted row is the line used: red for the wrong
reading, green for the winner. Same places throughout.

## Scene 1 · Who knows the way? · 0:00–0:40 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: Client wants to send a packet to ledger, at 10.10.4.40, the computer that keeps the café's payment records. A
packet is a small piece of data with a label in front: where it came from, and where it's going. On the way, it
crosses two routers: machines joined to more than one network, whose job is to pass packets on. Nobody on the way
knows the whole path. So how does each router know which way to send it?

SCREEN: Client and ledger, the packet card "packet: to 10.10.4.40"; the routers, links and the lower row draw in;
both routers glow.

## Scene 2 · Sorting offices · 0:40–1:15 · [ANALOGY] [MAP] [NAME] [JOKE:pivot]

VO: Think of a chain of parcel sorting offices. A sorter reads the address, drops the parcel in the van for the right
direction, and never thinks about it again. Routers work the same way. Each one reads the destination, hands the packet
to the next machine, and forgets it. That hand-off is called forwarding, and the next machine is the next hop. A sorter
never asks a parcel where it's been. Nobody has the time. So each router decides with one thing in hand: the
destination.

SCREEN: A dot hops client → router → router2 → ledger, each router glowing as it passes. Captions name forwarding and
the next hop.

## Scene 3 · One line isn't enough · 1:15–1:50 · [SHRINK] [BREAK]

VO: It decides from a list called its routing table. Start with the simplest list that could work: one line.
Everything goes to my gateway, the router that leads out. That's the default route. For a machine with one way out,
it's all you need. But router has three ways out. A packet for the server must leave on wan. One for ledger must go
into the tunnel. One line can't say both.

SCREEN: "router's table: everything → my gateway". Dots leave router on wan and into the tunnel; the line turns red.

## Scene 4 · Blocks, and router's table · 1:50–2:50 · [SHOW] [NAME] [LOOP-PLANT]

VO: So a router keeps one line per block of addresses. A block is written like this: 10.10.4.0/24. An address is 32
bits, 8 for each of its four numbers. The /24 says the first 24 bits, here the first three numbers, are fixed. So the
block holds every address from 10.10.4.0 to 10.10.4.255. That count of fixed bits is the prefix length. Router's table
gets a line for each of its own cards, which the kernel adds by itself, a line typed in by hand for ledger's block, and
the default, now written 0.0.0.0/0: no fixed bits at all, so every address fits. Watch ledger's packet arrive.
10.10.4.40 fits 10.10.4.0/24, so router sends it into the tunnel, to router2. Notice it also fits the default. Hold
that thought.

SCREEN: Four number boxes, "10", "10", "4" in green (fixed, 8 bits each) and "0 to 255" in grey; "/24: the first 24
bits are fixed"; "10.10.4.0 to 10.10.4.255". Then router's table: 10.10.1.0/24 lan, 10.10.2.0/24 wan, 10.10.3.0/24
tunnel (its own cards), 10.10.4.0/24 via router2 (10.10.3.3), 0.0.0.0/0 Docker's gateway (10.10.1.1). The
10.10.4.0/24 line is boxed as the dot enters the tunnel; then the default is boxed in grey.

## Scene 5 · Three lines fit · 2:50–4:00 · [PREDICT] [PAUSE] [BREAK] [JOKE:soften] [NAME] [LOOP-PAYOFF] [MAP]

VO: Now look at client's table. The lesson gives it a broad line: every address in 10.10.0.0/16 goes to router. Client
already had its own network, 10.10.1.0/24, straight across lan, and the default. A packet for peer, at 10.10.1.20,
fits all three. Which line wins? Pause and guess.

(three seconds)

Most lists, we read from the top and stop at the first line that fits. Here, that's the default. So peer's packet would
go to Docker's gateway, the way out to the internet, to reach a computer on client's own wire. Well... that's like
posting a note to your neighbour through the national hub. The real rule is longest prefix match. Of all the lines that
fit, the one with the most fixed bits wins, because it describes the destination most precisely. 24 beats 16, which
beats 0. So peer's packet goes straight across lan, and ledger's goes to router. And the order of the lines never
matters. A sorting office works the same way. The pigeonhole for one street beats the one for the whole city, which
beats everything else: send it to the national hub.

SCREEN: Client's table in the order `ip route` prints it: 0.0.0.0/0, 10.10.0.0/16, 10.10.1.0/24. "fits" beside all
three; countdown. The default is boxed in red and a red dot runs to Docker's gateway. Then "fits" becomes "0 bits",
"16 bits", "24 bits"; the /24 line is boxed in green; a green dot runs to peer, a yellow one to router.

## Scene 6 · Where lines come from, and the limit · 4:00–4:35 · [GUARDRAIL] [LOOP-PLANT]

VO: On the internet, nobody types these lines in. Routers tell each other which blocks they can reach, using a routing
protocol called BGP. A full table holds around a million blocks. One property matters for what comes next. Each router
decides alone, with no memory of where the packet has been. That lets the internet route around a broken link. It also
means two routers whose tables disagree could pass a packet back and forth forever. The next section makes two of
them do it.

SCREEN: Captions; both routers glow; a red dot bounces back and forth on the tunnel.

## Scene 7 · The moral, and a check · 4:35–5:00 · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So how does a router know the way? It doesn't. It knows the next step: the most specific line that fits. One quick
check. Client sends a packet to 1.1.1.1, out on the internet. Which of client's three lines wins? Pause and think.

(three seconds)

The default. 1.1.1.1 doesn't start with 10.10, so the only line that fits is 0.0.0.0/0. Off to Docker's gateway.

SCREEN: The packet card becomes "packet: to 1.1.1.1"; countdown; the default line is boxed in green and a green dot runs
to Docker's gateway.

---

### Beat check

- QUESTION (scene 1); ANALOGY + MAP (scene 2); SHRINK and BREAK of the one-line table (scene 3).
- NAME after SHOW: forwarding and next hop (scene 2), default route (scene 3), prefix length (scene 4), longest prefix
  match (scene 5, after the viewer has felt the wrong reading fail).
- PREDICT with PAUSE (scene 5, and the check in scene 7).
- GUARDRAIL (scene 6) and MORAL (scene 7) last. Light moments: "nobody has the time" (1:10), the note to your
  neighbour through the national hub (3:20).

### Accuracy notes for the producer

- Client's table and its order come from the lesson's Try it output (`default via 10.10.1.1`, `10.10.0.0/16 via
  10.10.1.2`, `10.10.1.0/24 dev eth0`). That run also prints `10.10.2.0/24 via 10.10.1.2` from net-03's lab; the video
  follows the section's prose ("client already has 10.10.1.0/24 and the default") and shows three lines.
- 1.1.1.1 "fits only the default": from the same Try it.
- Router's table is drawn with the static route `10.10.4.0/24 via 10.10.3.3` that the section's prose adds by hand. In
  the Try it, router has no route for dc yet and sends ledger's packets to Docker's gateway; the later traceroute Try it
  relies on that. Router's connected lines and its default via 10.10.1.1 are as the lesson describes.
- "Around a million blocks" for a full BGP table: the lesson's figure. Big routers' special chips are left out.
- The bouncing packet is only previewed; TTL and ICMP are section 1.
- Spoken forms via `SAY`: dotted addresses as "dot", "/24" as "slash 24", router2 as "router two", BGP as "B G P".
