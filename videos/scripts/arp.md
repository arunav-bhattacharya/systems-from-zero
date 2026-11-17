# Who has 10.10.1.20? Asking the room for a card's name

- Slug / scene: `arp`, `videos/scenes/arp.py:Arp`
- Lesson: `net-02`, section 2, "ARP: asking the whole link who owns an IP address"
- Audience / level: a complete newcomer. Knows nothing about network cards, switches or frames.
- Length: 4:04 (~620 words of narration at the Kokoro voice's ~180 wpm, plus two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: my computer knows the neighbour's IP address, but a frame needs the neighbour's card
  name (MAC). Where does it get that, if nobody told it?
- Misconception to steelman and break: "a list of every card's address sits somewhere": in the switch (it never reads
  IP addresses) or in a file on every computer (out of date the first time anything changes).
- Concept chain: a frame needs the next card's MAC → no list can stay right → ask the whole link (broadcast), answer
  the asker alone → remember the answer (cache), and the owner learns the asker from the question → ARP trusts every
  answer and reaches one link only (hardest last)
- Analogy family: a barista at lunchtime calling "flat white for Sam!". Barista = client, Sam's name = the IP
  address, Sam's face = the MAC, calling to the whole room = a broadcast, remembering Sam = the cache. Breaks on
  trust: a barista might notice a stranger grabbing Sam's coffee; ARP checks nothing.
- Open loops: "where does it get it?" planted in scene 1 → answered in scene 8; the file planted in scene 2 → its
  place taken by the cache in scene 5.
- Assumptions: the lesson's lab link: client 10.10.1.10 (ee:02:07:41:4d:8c), peer 10.10.1.20 (4a:9d:40:b1:a5:9e),
  router 10.10.1.2 (its MAC is never shown), joined by Docker's software switch; client is on port 1.

## The one picture

Top row: client (left), router (middle), peer (right), each a box with its IP address and MAC. Below them, the
switch, wired to all three, ports 1 to 3. Under client and under peer, a small card: their ARP cache. In the centre at
the bottom, a panel shows the frame on the wire. Yellow dots are frames moving along the wires; a yellow panel is a
broadcast, a white one goes to one card; green means stored and true; red means wrong. Grey tags over the boxes carry
the café mapping. Same places and colours throughout.

## Scene 1 · The missing name · 0:00–0:40 · [QUESTION] [FAMILIAR]

VO: Three computers share one link, plugged into a switch, the box that joins their cables. Client wants to ping peer,
at 10.10.1.20. A ping is a small test message: are you there? Every network card has a name, its MAC address: six
bytes, like this one. And every frame, each chunk of data sent across the link, must carry the MAC of the card it's
for. Client knows peer's IP address. But peer's MAC? Nothing has told it. So where does client get it?

SCREEN: The three boxes and the switch draw in, wires grow. Client's MAC glows. The panel shows a ping waiting:
"to ??:??:??:??:??:??", "ping 10.10.1.20: are you there?". A yellow "?" over the panel.

## Scene 2 · A list somewhere? · 0:40–1:20 · [PAIN] [BREAK] [WISH]

VO: The tempting answer is a list. Surely something keeps every card's address. The switch, perhaps? But a switch
knows only MAC addresses, and which port each one sits behind. It never reads an IP address. Then give every computer
a file of its neighbours. It breaks the first time anything changes. A broken card gets replaced. Tomorrow,
10.10.1.20 goes to a different laptop. And Docker, which runs these little lab computers, gives each one a new random
MAC every time it starts. Nobody could keep that file right.

SCREEN: The switch glows; caption "a switch knows MACs and ports, never IP addresses". A card under client, "a file
of neighbours: 10.10.1.20 → last week's card". On each change, a red strike; the card turns red, "out of date".

## Scene 3 · The barista · 1:20–2:05 · [ANALOGY] [MAP] [JOKE:pivot]

VO: So let's borrow a trick from a café at lunchtime. The barista calls out, "Flat white for Sam!" Everyone hears it.
One person stands up and gets the cup. Next time, she'll remember Sam. Notice what she doesn't do: keep a photo album
of every customer's face. It would be out of date by Tuesday. Let's map it. The barista is client. Sam's name is the IP
address, and Sam's face is the MAC. Calling to the whole room is a broadcast: a frame to an address that every card
accepts. And remembering Sam is a cache.

SCREEN: Grey tags: "the barista" over client, "Sam" over peer, "another customer" over router. The file card fades.
Captions, one per mapping: "Sam's name = the IP address", "Sam's face = the MAC", "calling to the room = a broadcast,
to ff:ff:ff:ff:ff:ff", "remembering Sam = a cache".

## Scene 4 · Ask the room · 2:05–3:05 · [SHRINK] [PREDICT] [PAUSE] [SHOW]

VO: So client asks. It broadcasts one question: who has 10.10.1.20? Tell 10.10.1.10. Inside, the target's MAC is all
zeros. That empty field is the question. Who will hear it, and who will answer? Pause and guess.

(three seconds)

The switch sends a broadcast out of every port, so everyone hears it. Router isn't 10.10.1.20, and it has never met
client, so it drops the question. Peer is 10.10.1.20. It writes client down, and answers: 10.10.1.20 is at this card.
The answer goes to client's card alone. The switch learned client's port from the question, so router never even hears
it. Only the question needed the whole room.

SCREEN: The panel turns yellow: "to ff:ff:ff:ff:ff:ff", "who has 10.10.1.20? tell 10.10.1.10", "target MAC
00:00:00:00:00:00" (the zeros glow). "?" marks over router and peer; countdown. Dots run client → switch → router and
peer. Router dims with "not me". Peer's cache card fills: "10.10.1.10 → ee:02:07:41:4d:8c". The panel turns white:
"to ee:02:07:41:4d:8c", "10.10.1.20 is at 4a:9d:40:b1:a5:9e"; one dot runs peer → switch → client only.

## Scene 5 · The name, and the memory · 3:05–3:45 · [NAME] [SHOW] [LOOP-PAYOFF]

VO: This is ARP, the Address Resolution Protocol. It turns an IP address into a MAC, and it has done that job since
1982. Client keeps the answer in its ARP cache, a short list of recent answers. Now the ping leaves at once, addressed
to peer's card. And peer answers without asking anything back. It wrote client down from the question. Two ARP
messages, and from now on, every frame between them goes to one card only.

SCREEN: Caption "ARP, the Address Resolution Protocol: IP address in, MAC out". Client's card becomes "ARP cache" and
fills: "10.10.1.20 → 4a:9d:40:b1:a5:9e" (green). The ping panel: "to 4a:9d:40:b1:a5:9e"; a dot runs client → peer, then
the reply runs back. Router stays dim.

## Scene 6 · Where the café breaks · 3:45–4:15 · [BREAK of the analogy] [JOKE:is-the-explanation]

VO: Here the café picture breaks. A barista might notice a stranger grabbing Sam's coffee. ARP checks nothing. Any card
on the link can answer for any IP address, and the asker believes it. ARP trusts everyone: lovely in a friend,
worrying in a network. The lesson's Go deeper shows what an attacker does with that.

SCREEN: A red dot runs router → client with the panel "10.10.1.20 is at router's card" (red, dashed). Client's cache row
turns red. Then it's undone.

## Scene 7 · Two limits · 4:15–4:35 · [GUARDRAIL]

VO: Two more limits. ARP reaches one link only. For a computer on another network, client asks for the router's MAC
instead. And a remembered answer can go out of date, so entries are forgotten on purpose. The next section shows how.

SCREEN: Captions "limit 1: one link only; for anything further, ask for the router's MAC" and "limit 2: answers go out
of date, so the cache forgets on purpose".

## Scene 8 · The moral, and a check · 4:35–5:05 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So where did client get peer's MAC? It asked the room, once. Ask everyone, answer one, remember for a while. One
quick check. Now peer wants to ping client. Does peer have to ask the room first? Pause and think.

(three seconds)

No. Peer wrote client down from the question. It sends straight away.

SCREEN: Caption "ask everyone, answer one, remember for a while". For the check, peer's cache glows; countdown; then a
dot runs peer → client with no broadcast.

---

### Beat check

- QUESTION (scene 1) from the felt gap: an IP address in hand, a MAC needed.
- BREAK of the tempting list, twice, before the analogy (scene 2); ANALOGY + MAP said out loud (scene 3).
- PREDICT with PAUSE (scene 4, and the check in scene 8); SHOW right after each.
- NAME after the SHOW: broadcast, cache (scene 3), ARP (scene 5).
- BREAK of the analogy on trust (scene 6); GUARDRAIL (scene 7) and MORAL (scene 8) last.
- Light moments: the photo album out of date by Tuesday (1:45), "lovely in a friend, worrying in a network" (4:05).

### Accuracy notes for the producer

- Addresses are the lesson's lab: client 10.10.1.10 at ee:02:07:41:4d:8c, peer 10.10.1.20 at 4a:9d:40:b1:a5:9e; the
  router is 10.10.1.2 (from net-03). Router's MAC is never shown; "router's card" in scene 6 is a placeholder.
- The ARP message is 28 bytes inside an Ethernet frame with EtherType 0x0806; the video shows only the question, the
  sender, the target and the all-zeros target MAC.
- Router drops the question because it isn't the target and has no entry for client (RFC 826's refresh rule applies
  only to computers that already know the sender), as in the lesson's stepper.
- The switch learning and flooding is section 1; the video says it in one clause. Linux's REACHABLE, STALE, DELAY and
  PROBE states, and gratuitous ARP, are left to section 3 ("forgotten on purpose").
- "Since 1982": RFC 826.
- Spoken forms via `SAY`: dotted addresses as "dot"; MAC as "mac".
