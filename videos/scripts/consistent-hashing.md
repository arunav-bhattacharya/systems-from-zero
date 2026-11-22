# Who gets the biggest slice? A ring of hash values, and many cuts each

- Slug / scene: `consistent-hashing`, `videos/scenes/consistent_hashing.py:ConsistentHashing`
- Lesson: `shard-02`, section 0, "A ring of hash values, and why one place per machine is unfair"
- Audience / level: a complete newcomer who has seen the previous lesson's hash and remainder; no ring, no tokens.
- Length: 4:46 (~900 words of narration, two 3-second pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: six machines on the ring, one token each, shares 44.0% down to 1.6% against the fair line (`POSTER=150`)
- The learner's real question: why can't we just keep dividing by the number of machines, and if a ring fixes that,
  is a ring fair?
- Misconception to steelman and break: "a hash is fair, so one random place per machine is fair". Six tokens give
  44.0% to E and 1.6% to C.
- Concept chain: hash mod S moves 80% from 4 to 5 → the ring: tokens, first token clockwise, a node owns the arc
  ending at its token → a new node takes keys from one neighbour only (consistent hashing) → one token each is
  unfair → many tokens each (virtual nodes) bring shares near fair → not smooth with few random tokens (Cassandra's
  allocator), and bigger machines take more tokens
- Analogy family: the lesson's six friends cutting a pizza at random, each taking the slice ending at their own cut;
  later sixteen thin cuts each.
- Open loops: "keep that pizza in mind" planted in scene 1 → paid off in scene 5 ("E got the pizza") and scene 8.
- Assumptions: every ring position is computed, not drawn by hand: tokens are MD5 of `node-A#0` etc. read as a 128-bit
  fraction, which reproduces the lesson's shares exactly (A 13.6, B 26.1, C 1.6, D 7.9, E 44.0, F 6.8; 16 tokens
  biggest 24.3, 64 → 18.6, 256 → 17.4, 4 → 23.4). A-1001's place is MD5 of "A-1001". The pizza's six cuts and
  machine G's place in the check are made up for the picture.

## The one picture

Left: the ring, each arc coloured by the machine that owns it, token dots with letters outside. Right: a share bar per
machine with its percentage, a dashed "fair: 16.7%" line, and later a small table of tokens per machine against the
biggest share. Captions at the bottom. The hash-mod row of twenty values appears once, before the ring.

## Scene 1 · The pizza · [QUESTION] [ANALOGY] [LOOP-PLANT]

VO: Six friends share a round pizza. Each one makes a single cut wherever they like, and takes the slice that ends at
their own cut. Random cuts sound fair, since nobody chose where anyone else would cut. Then the slices come out, and
they're nothing like equal. Keep that pizza in mind.

## Scene 2 · Hash mod the number of machines · [FAMILIAR] [PREDICT] [PAUSE] [SHOW] [PAIN] [WISH]

VO: Now the payments company. It spreads payments over its machines with a hash: a formula that turns a key into a big
random-looking number. It divides that number by the number of machines, and keeps the remainder. With four machines,
the remainder picks machine 0, 1, 2 or 3. That spreads keys evenly. Until the day a fifth machine arrives. Here are
twenty hash values in a row, with their remainder for four machines and for five. How many keep the same machine?
Pause and guess.

(three seconds)

Only four. Zero, one, two and three. Every other key moves, so going from four machines to five moves 80% of the keys.
That's 80% of the data copied across the network, while the machines are still taking card payments. All that, to add
one machine. What we'd like is for the new machine to take its fair share, and for every other key to stay put.

SCREEN: Twenty cells 0 to 19, rows "mod 4" and "mod 5"; green boxes round 0 to 3, the other sixteen red.

## Scene 3 · The ring · [ANALOGY] [MAP]

VO: Here's the idea. Lay every possible hash value around a circle, like the edge of the pizza. That circle is the
ring. Each machine sits at the hash of its own name. That place is its token: the machine's cut in the pizza. A key
sits at the hash of the key, and belongs to the first machine you meet walking clockwise. Take key A-1001. Walk
clockwise, and the first token is D's. So each machine owns the arc that ends at its token. That arc is its slice.

SCREEN: The ring draws; four tokens A to D; A-1001 inside the ring with a white arc walking to D; arcs coloured by
owner; the share bars appear (D 58.7%).

## Scene 4 · A machine joins · [SHOW] [NAME]

VO: Now a fifth machine joins, E. Its token lands inside D's arc. Which keys move? Only the ones on the arc just before
E's token, and all of them come from D. A-1001 is one of them, so it moves to E. A, B and C don't lose a single key.
That's consistent hashing. Consistent here means most keys stay where they were when the machines change. It has
nothing to do with consistent data. Cassandra, a free database built to spread over many machines, is built on it.

SCREEN: E's token appears; a thick gold arc marks what moves; the ring recolours; D's bar shrinks, E's appears, A, B,
C unchanged.

## Scene 5 · Is a hash fair? · [BREAK] [JOKE:reward] [LOOP-PAYOFF]

VO: So far so good. Now add a sixth machine, F, and look at the slices. E owns 44% of the ring. C owns 1.6%. A fair
share for six is 16.7%. Well... E got the pizza, and C got a crumb. And it wasn't bad luck. A good hash is as good as
random, and random points on a circle clump. For six machines, the biggest gap averages about 41%. Thousands of keys
average out. Six places don't. The machine with 44% stores 44% of the data and answers 44% of the requests, while its
neighbour sits nearly idle. And buying a seventh machine doesn't fix it, because its token lands at random too.

## Scene 6 · Many cuts each · [ANALOGY] [SHOW] [NAME]

VO: The fix comes straight from the pizza. Instead of one cut each, every friend makes sixteen thin cuts. Each machine
gets sixteen tokens, at the hashes of node A number 0, node A number 1, and so on. Now a machine's share is the sum of
many small arcs, and a sum of many random pieces lands much closer to its average than one piece does. These extra
tokens are called virtual nodes. With sixteen each, the biggest share drops from 44% to 24.3%. With 64, it's 18.6%, and
with 256, 17.4%.

SCREEN: The ring becomes many thin coloured arcs (16 per machine, then 64); bars move toward the fair line; the table
fills in: 1 → 44.0%, 16 → 24.3%, 64 → 18.6%, 256 → 17.4%.

## Scene 7 · Guardrail · [GUARDRAIL]

VO: But notice, it isn't smooth. Four tokens each gave 23.4%, a little better than sixteen. With only a few random
tokens, luck still matters. That's why Cassandra doesn't place its sixteen tokens at random. It uses a token
allocator, which this lesson comes back to. And tokens fix one more thing. A machine twice as big can take twice as
many tokens.

## Scene 8 · Moral and a check · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So, the pizza. One random cut each gives slices nothing like equal. Many thin cuts each, and everyone gets about a
fair slice. And whenever a machine joins, only the keys just before its tokens move. One quick check. Back to one
token each. A seventh machine, G, joins, and its token lands inside B's arc. Which machines give it keys? Pause and
think.

(three seconds)

Only B. The new machine takes the arc just before its token, and that arc belonged to B. Every other key stays put.

SCREEN: One token each again; G's red token in B's arc; countdown; the red arc from A's token to G's.

---

### Beat check

- QUESTION as a story (the pizza), FAMILIAR (hash mod from the last lesson) with PREDICT + PAUSE and the 80% PAIN.
- ANALOGY + MAP (edge = ring, cut = token, slice = arc) before NAME (consistent hashing, token, virtual nodes).
- BREAK: "a hash is fair" run on the real six tokens (44.0% vs 1.6%).
- GUARDRAIL (not smooth with few random tokens; Cassandra's allocator; bigger machines, more tokens), MORAL, check.
- Light moments: "keep that pizza in mind"; "E got the pizza, and C got a crumb".

### Accuracy notes for the producer

- The lesson writes S for the number of machines; the video says "the number of machines" and never uses N.
- The 80% is the lesson's (4 of any 20 consecutive values keep their remainder); its Try it measures 80,221 of 100,000.
- The join of E into four machines is the lesson's section 1 demo (43,894 of 100,000 keys, all from D); the video
  shows the arc but no key count.
- "The biggest gap averages about 41%" is the lesson's formula (1 + 1/2 + ... + 1/S) / S for S = 6.
- What a dead node does to its neighbour, copies on the ring, rendezvous and jump hashing, Murmur3 and Cassandra's
  allocator are left to the rest of the lesson. The ring balances keys, not requests (the lesson's last section).
