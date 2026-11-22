# Ask the wrong server, and it tells you where to go

- Slug / scene: `cluster-slots`, `videos/scenes/cluster_slots.py:ClusterSlots`
- Lesson: `cache-10`, section 1, "A node that doesn't own the slot sends you to the one that does"
- Audience / level: a complete newcomer. Has met Redis in earlier lessons as "a program that holds data in memory";
  doesn't know what a cluster, a slot, a redirect or a round trip is.
- Length: 5:16 (~800 words of narration, three pauses, silent builds)
- Poster: `POSTER=200` (the client's table just reloaded after the stale MOVED: bar, three nodes, table)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: once the keys are split over three servers, which one does my program ask for
  `payment:42`, and what happens if it asks the wrong one?
- Misconception to steelman and break: "the server I'm connected to will fetch it for me, like any helpful
  attendant". Broken by node 1's MOVED reply; then a second wrong model, "once the client has the table it never
  gets redirected", broken by moving slot 9055.
- Concept chain: key → slot (checksum mod 16,384) → slot table names the node → a node never forwards, it answers
  MOVED → a plain client pays an extra trip for two keys in three → a cluster-aware client keeps its own copy of the
  table → the copy goes stale when a slot moves, and MOVED fixes it (hardest last)
- Analogy family: the lesson's cloakroom. 16,384 numbered hooks, three attendants, a board by the door that says who
  looks after which hooks, a guest's photo of the board, and a board that sends guests down the staff corridor.
- Open loops: "what if you ask the wrong one?" planted in scene 1 → scene 3 and the moral; "a transaction can't be
  split across nodes" planted in scene 7 → the next section (hash tags).
- Assumptions: every number is the lesson's (40 GB, 300,000 commands a second; slot ranges 0-5460, 5461-10922,
  10923-16383 on ports 7001 to 7003; `payment:42` in slot 9055, `payment:43` in slot 13182; `MOVED 9055
  127.0.0.1:7002`, then `MOVED 9055 127.0.0.1:7003` after the move; about two keys in three redirected for a plain
  client; the demo's line `payment:42 slot 9055 on 127.0.0.1:7002`). The six dots in the "two in three" beat are a
  picture of the ratio.

## The one picture

Top: a bar of 16,384 hooks, later "hash slots", in three coloured ranges (blue, teal, purple), the board. Right: three
boxes, the attendants, later node 1, 2 and 3 with their address and range. Left: the client ("your program"), with
the request it is sending above it, and later its own copy of the slot table under it. Middle: three arrows from the
client to the nodes; gold dots are requests, red dots and red labels are MOVED, green is an answer. Captions at the
bottom. Same places and colours from start to end.

## Scene 1 · The question · 0:00–0:25 · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: The payments program keeps its notes and counters in Redis, a program that holds data in memory and answers very
fast. It has grown to 40 GB and 300,000 commands a second, and one Redis runs every command one at a time.

So the keys get split over three servers, and each one owns a part. Now your program wants payment:42. Which server
do you ask? And what happens if you ask the wrong one?

SCREEN: Title card. "your program" on the left, one red-outlined Redis box on the right with "40 GB",
"300,000 commands a second", "one command at a time". The box splits into three server boxes. A chip
"GET payment:42" above the program, then a "?".

## Scene 2 · The cloakroom · 0:25–1:05 · [ANALOGY] [MAP] [NAME]

VO: Picture a cloakroom with 16,384 numbered hooks and three attendants. Your ticket always picks the same hook. And a
board by the door says which attendant looks after which hooks.

Redis Cluster works the same way. The hooks are called hash slots. A key's slot is a checksum of the key, mod 16,384,
so payment:42 always lands in slot 9055.

The attendants are the servers, called nodes, each with its own address. And the board is the slot table. Node two
looks after slots 5461 to 10922, so payment:42 lives on node two.

SCREEN: The bar "16,384 hooks" draws in; the servers become "attendant 1, 2, 3"; the bar splits into three coloured
ranges with their numbers (the board). A marker drops on one hook. Then "hooks" becomes "hash slots", the line
"CRC16(payment:42) mod 16384 = 9055" appears and the marker is labelled "slot 9055". The attendants become node 1, 2,
3 with addresses 127.0.0.1:7001 to 7003 and ranges; an arrow from slot 9055 to node 2.

NOTE: Each mapping said out loud as its label changes: hooks = slots, attendants = nodes, board = slot table.

## Scene 3 · Ask the wrong node · 1:05–1:50 · [PREDICT] [PAUSE] [BREAK] [JOKE:soften]

VO: Now take the simplest client, a program that knows one address and treats it as one Redis. Ours knows node one. It
sends GET payment:42 to node one, and node one doesn't own slot 9055. What does node one do? Pause and guess.

(three seconds)

A kind attendant would walk to the next counter and fetch your coat. A Redis node never does. Node one answers with an
error: MOVED, slot 9055, and node two's address. It lives over there, so ask there.

The client asks again, at node two, and gets its answer. Rude? A little. But that rudeness is why the cluster can
grow. Each node only ever works on its own slots, never on errands for the others.

SCREEN: The program becomes "plain client: knows node 1". An arrow to node 1; a gold dot runs along it. Countdown.
A dashed arrow from node 1 to node 2 appears and is crossed out ("never forwards"). A red dot runs back with
"MOVED 9055 127.0.0.1:7002". Then an arrow to node 2: gold dot there, green dot back, "approved".

## Scene 4 · The extra trip · 1:50–2:25 · [PAIN] [PREDICT] [PAUSE] [SHOW] [WISH]

VO: Following every MOVED works, but each one costs an extra round trip: a message there, and an answer back. So if
the plain client sends all its commands to node one, how many come back MOVED? Pause and guess.

(three seconds)

About two in three. Node one owns a third of the slots, so two keys in three belong to someone else, and each of those
makes two trips instead of one. Wouldn't it be nice if the client could read the board before it asked?

SCREEN: Caption "round trip: a message there, and an answer back". Countdown. Six dots go to node 1: two come back
green, four come back red and go on to node 2 or node 3. Caption "about 2 in 3: MOVED, then a second trip".

## Scene 5 · A photo of the board · 2:25–2:55 · [NAME] [SHOW]

VO: That's exactly what a cluster-aware client does. When it starts, it asks any node for the whole slot table, its
own photo of the board. And it opens a connection to every node.

Then it works out each key's slot itself. payment:42 is slot 9055: straight to node two. payment:43 is slot 13182:
straight to node three. One round trip each, and no MOVED.

SCREEN: The client becomes "cluster-aware client". A copy of the bar shrinks into a small table under it ("its slot
table": three ranges with ports). Arrows to all three nodes. payment:42: marker at 9055, the table's middle row lights,
a dot to node 2 and back green. payment:43: marker at 13182, the bottom row lights, a dot to node 3 and back green.

## Scene 6 · The photo goes stale · 2:55–3:35 · [BREAK] [SHOW]

VO: So far so good. But a photo can go out of date. Say someone running the cluster moves slot 9055 to node three. The
client's table still says node two.

So its next GET goes to node two, which answers MOVED, slot 9055, with node three's address. The client fixes its
table, usually by loading all of it again, because slots rarely move alone. Then it asks node three, and from then on,
it goes straight there.

With a cluster-aware client, a MOVED is rare, and it means one thing: the table changed. A slot moved, or a replica took
over from a dead primary.

SCREEN: The 9055 marker turns purple and moves into node 3's keeping: node 2 reads "5461 to 10922, not 9055", node 3
"10923 to 16383 + 9055". The client's table glows unchanged ("still says :7002"). A dot to node 2, a red dot back with
"MOVED 9055 127.0.0.1:7003". The table gains the row "9055 → :7003" and reloads. A dot to node 3, green back. Caption
"MOVED: the table changed (a slot moved, or a replica took over)".

## Scene 7 · The address, and a rule to keep · 3:35–4:15 · [GUARDRAIL] [JOKE:is-the-explanation] [LOOP-PLANT]

VO: One trap. The client does the routing, so the address inside a MOVED must work from wherever the client runs. Each
node announces just one address.

Run the cluster in Docker, a tool that runs each server as a small separate machine on your laptop, and the nodes may
announce addresses that only exist inside Docker. That's a board that sends guests down the staff corridor. The lab
makes every node announce 127.0.0.1, which works from both sides.

And one rule to carry into the next section. A cluster client splits a batch of commands into one batch per node. But
a transaction, a group of commands that runs as one step, can't be split across nodes. Keep that in your pocket.

SCREEN: The node addresses turn red, "inside Docker only"; a dot from the client stops halfway at a red cross. Caption
"a board that sends guests down the staff corridor". The addresses come back as 127.0.0.1 (green), caption
"the lab: cluster-announce-ip 127.0.0.1". Then three dots fan out to the three nodes ("a batch: one per node", tick),
and a bracketed pair of dots towards node 2 and node 3 with a red cross ("a transaction: one step, can't be split").

## Scene 8 · The code · 4:15–4:30 · [SHOW]

VO: In Java and Kotlin, you give the cluster client one address, the seed. It loads the table from there and sends each
command to its owner. Both print the same line: payment:42, slot 9055, on node two.

SCREEN: The diagram dims. Two panels: Java (Jedis `RedisClusterClient` built with one `HostAndPort` and
`cluster.set("payment:42", ...)`) and Kotlin (Lettuce `RedisClusterClient.create("redis://127.0.0.1:7001")`, coroutines
`set`). Under both: "both print: payment:42  slot 9055  on 127.0.0.1:7002".

## Scene 9 · The moral, and a check · 4:30–5:05 · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So, which server do you ask? The one the table names. A key hashes to a slot, the table names the slot's node, and
a node never fetches for you. It tells you where to go.

Ask the wrong one, and it costs you one extra trip, and a fresh copy of the board.

One quick check. A plain client sends GET payment:43 to node one. What comes back? Pause and think.

(three seconds)

MOVED, slot 13182, with node three's address. Slot 13182 is in node three's range, so the client asks again there.

SCREEN: Captions "key → slot → the table's node", "a node never fetches: it tells you where to go". For the check, the
client's table dims ("plain client"), a dot to node 1, countdown, then a red "MOVED 13182 127.0.0.1:7003", the marker at
13182 in node 3's range, and a green trip to node 3.

---

### Beat check

- Opens with QUESTION (scene 1) on a felt problem (one server can't keep up, so where does a key live now?).
- ANALOGY + MAP (scene 2) before any Redis word beyond "server"; each part mapped out loud; names (hash slot, node,
  slot table) come as the mapping lands.
- PREDICT with PAUSE: scene 3 (what does node 1 do?), scene 4 (how many come back MOVED?), scene 9 (the check).
- BREAK: the kind attendant (scene 3, where the cloakroom stops matching), and the client whose table never goes
  stale (scene 6).
- NAME after SHOW: MOVED (scene 3), round trip (scene 4), cluster-aware client (scene 5).
- GUARDRAIL (scene 7) and MORAL (scene 9) come last. Light moments: the rude attendant (1:35), the staff corridor
  (3:55), the photo of the board (2:30, 3:00).
- Open loop "what if you ask the wrong one?" paid off by name in scene 9. The transaction loop is paid off by the
  lesson's next section.

### Accuracy notes for the producer

- The lesson's cloakroom says the analogy breaks because an attendant can walk over and fetch a coat, and a node never
  does; the video uses the same break.
- "A checksum of the key" is CRC16 (the XMODEM variant) mod 16,384; hash tags, which hash only part of a key, are left to
  the next section.
- "About two in three" is the lesson's figure for three equal ranges; the six dots are a picture of it.
- A cluster-aware client loads the table with `CLUSTER SHARDS` (or the older `CLUSTER SLOTS`) and usually reloads all of
  it on MOVED; Lettuce 7 also reloads when it notices redirects. The video says "usually".
- The Docker trap: the lab's Compose file shares one network setup and sets `cluster-announce-ip 127.0.0.1`. The video
  doesn't show the addresses Docker would announce, only that they don't work from the laptop.
- ASK, the reply while a slot is half moved, and CROSSSLOT are in later sections; the video doesn't show them.
- The code is shortened from the lesson's `ClusterDemo` (Jedis) and `ClusterDemo.kt` (Lettuce coroutines); the printed
  line is the demos' output for `payment:42`.
