# Nobody in charge: how a Cassandra cluster spreads news by gossip

- Slug / scene: `cassandra-gossip`, `videos/scenes/cassandra_gossip.py:CassandraGossip`
- Lesson: `shard-05`, section 2, "Gossip: once a second, each node compares notes with one random peer"
- Audience / level: a complete newcomer. Knows a cluster is several machines working as one store; doesn't know
  Cassandra, heartbeats, gossip, digests, generations or seeds.
- Length: about 4:45 (~800 words of narration, plus a pause and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: round 2 of the spread: cass6, cass2, cass1 and cass3 green with "cass6: v412", two exchange lines lit,
  "knows the news: 4 of 6".
- The learner's real question: with no machine in charge, how does every machine hear that something changed, and
  keep hearing that the others are alive?
- Misconception to steelman and break: "somebody has to tell everyone", so whoever changes tells everyone and
  everyone sends a heartbeat to everyone. Broken by the count (30 messages a second for 6 nodes, 870 for 30, about a
  million for 1,000) and by the node that was restarting and never hears that news again.
- Concept chain: a change and a heartbeat must reach every node → telling everyone costs N × (N − 1) and loses news
  → tell one random peer a second: news doubles, about log2 N rounds → send digests of versions so only new state
  travels (Syn, Ack, Ack2) → generations for restarts, seeds for strangers (hardest last)
- Analogy family: the lesson's office with six clerks and no manager. Each clerk keeps a copy of the staff list; every
  few minutes each rings one colleague at random and they compare lists. Later: comparing the dates at the top of the
  lists before reading them (digests).
- Open loops: "how does everyone hear?" planted in scene 1 → scene 4; "a dead node says nothing" planted in scene 8 →
  the next section (failure detection).
- Assumptions: the six nodes, versions and rounds are the lesson's stepper (cass6 sets STATUS LEAVING at version 412,
  its heartbeat was 411, everyone else last heard 410; round 1 cass6 → cass2; round 2 cass6 → cass1 and cass2 → cass3;
  round 3 cass5 starts an exchange with cass1 and pulls the news; all six after 3 rounds). Which exchange tells cass4
  in round 3 isn't in the stepper; the picture uses cass3 → cass4. Counts are the lesson's: 870 for 30 nodes, about a
  million for 1,000; median 2 rounds for 6 nodes, 8 for 6,000 (demo), about 10 for 1,000 (log2); 3 × N messages a
  round. Restart: cass3 came back with a larger generation and heartbeat 32.

## The one picture

Six node boxes (cass1 to cass6) on an oval, each with one line of its map: "cass6: v410". A node that has heard the
news turns green and its line reads "v412". Exchanges are short-lived lines between two nodes with dots running both
ways. Right panel: the round counter and "knows the news: n of 6". Left panel: the three messages of one exchange as
small cards. Captions at the bottom; a cost line above them.

## Scene 1 · The office with no manager · 0:00–0:45 · [QUESTION] [FAMILIAR] [ANALOGY] [JOKE:warmup]

VO: Cassandra is a database program that spreads its data over many equal computers. No computer is in charge. That
sounds odd, because most offices and most programs have a boss somewhere. A boss is simple, right up to the day the
boss is the one that fails.

So how does every machine hear that something changed? Picture an office with six clerks and no manager. Each clerk
keeps a copy of the staff list. A new clerk arrives in the morning, and by lunch every list has her name on it. Nobody
sent an email. Every few minutes, each clerk rang one colleague at random, and the two compared lists.

SCREEN: Title card. Six boxes on an oval, "clerk" under each, a small list icon in each. A crown appears over the
centre and is crossed out on "no computer is in charge". Phone lines flicker between random pairs; a green name
spreads.

## Scene 2 · The map and the heartbeat · 0:45–1:15 · [MAP] [SHRINK]

VO: Map it. Each clerk is a node, one machine. The staff list is the node's map of the cluster: who's in it, and what
each one says about itself. Every node has two jobs. Hear each change, like a node that's leaving. And keep hearing
that every other node is alive. For that, each node raises a counter once a second, its heartbeat, that just says
"still here".

SCREEN: The labels become cass1 … cass6; each box gets its map line "cass6: v410". Captions: "clerk = node", "staff
list = the node's map of the cluster". A small heartbeat counter ticks on cass6.

## Scene 3 · Tell everyone · 1:15–1:55 · [PAIN] [BREAK] [JOKE:amplify]

VO: The obvious way: whoever changes tells everyone, and every node sends its heartbeat to every other node, once a
second. For six nodes, that's 6 times 5, 30 messages a second. Fine. For 30 nodes, 870. For a thousand, about a
million, every second. The machines would spend more time on the phone than at their desks.

And there's a quieter problem. A node that was restarting when the news went out never hears it again. Nobody calls
back.

SCREEN: All 15 pairs light up with dots both ways; right panel "6 × 5 = 30 a second", then "30 nodes: 870", "1,000
nodes: about 1,000,000" in red. cass4 greys out ("restarting"), cass6's news goes to everyone else; cass4 comes back
still saying v410, with a red "missed it".

## Scene 4 · One random call a second · 1:55–3:05 · [WISH] [PREDICT] [PAUSE] [SHOW]

VO: So do what the clerks did. Once a second, each node tells one random peer what it knows, and that peer passes it on
in its own rounds. cass6 has news: it's leaving, version 412. How many rounds until all six know? Pause and guess.

(three seconds)

Round one. cass6 rings cass2. Now two know. Round two. Both of them ring someone: cass6 picks cass1, cass2 picks cass3.
Four know. It doubled. Round three. This time cass5, who hasn't heard, rings cass1, and gets the news in the answer.
News flows both ways, pushed and pulled. All six know, after three rounds.

The number that knows roughly doubles every round, so it reaches N nodes in about log2 of N rounds: the number of
doublings to get there. About ten for a thousand nodes. The lesson's demo counts 8 rounds for 6,000. And a round costs
about three small messages per node, not a million. A node that missed the news just hears it at its next call.

SCREEN: Round counter and "knows the news: 1 of 6"; yellow "?" and countdown. Each exchange is a line between two
boxes with dots both ways; the receiver turns green and its line becomes "cass6: v412". Counts 2, 4, 6 of 6. Then the
right panel: "1 → 2 → 4 → 8 …", "1,000 nodes: about 10 rounds", "6,000 nodes: 8 rounds (demo)", "per round: about 3 ×
N messages".

## Scene 5 · Compare the dates first · 3:05–3:45 · [SHRINK] [SHOW] [NAME]

VO: One more saving. Sending your whole map every second is a waste when almost nothing changed. So each node numbers
every change to its own state: its heartbeat took 411, leaving took 412. That number is the version. Two nodes first
swap short summaries, called digests: for each node, just its highest version. cass2's copy says 410, so it answers:
send me what's newer than 410. And only those two states travel. Three messages: Syn, Ack, Ack2. That's gossip.

SCREEN: Left panel, one card at a time, while a dot runs cass6 → cass2 → cass6 → cass2: "Syn: cass6 is at v412",
"Ack: I have v410, send newer", "Ack2: heartbeat 411, LEAVING 412". Caption "gossip: once a second, compare notes with
one random peer".

## Scene 6 · Restarts and strangers · 3:45–4:25 · [GUARDRAIL]

VO: Two details keep it honest. A restarted node starts counting from zero again, so its versions look older than what
the cluster remembers. So each node also carries a generation, its start time, and a higher generation wins first. In
the lab, cass3 came back with a bigger generation and heartbeat 32, and everyone took the new state.

And a brand-new node knows nobody. So its settings list a few seeds, nodes to ask for the map. One rule: never list a
new node as its own seed, or it skips copying its data and answers reads with empty rows.

SCREEN: cass3 greys out and returns with "gen ↑, heartbeat 32"; green ticks as the others take it. Caption "a higher
generation wins first". A dashed seventh box "new node" asks cass1 ("seed") for the map. Caption "a new node must never
list itself as a seed" (red).

## Scene 7 · Moral, a loop and a check · 4:25–5:00 · [MORAL] [RECAP] [LOOP-PLANT] [PREDICT] [PAUSE]

VO: So nobody is in charge, and nobody needs to be. Each node rings one random peer a second, the news doubles, and only
what's new travels. But gossip only carries what each node says about itself. A dead node says nothing at all. How the
others read that silence is next.

One quick check. A cluster of 1,000 nodes, and one of them changes. Roughly how many rounds until everyone knows?
Pause and think.

(three seconds)

About ten. A thousand is about two, doubled ten times.

SCREEN: Every box pulses green in turn. Caption "one random call a second; the news doubles; only what's new
travels" (yellow). Then the check caption; countdown; "about 10 rounds: 2 doubled 10 times is 1,024" (green).

---

### Beat check

- QUESTION + FAMILIAR + ANALOGY (scene 1), MAP (scene 2) before any protocol word.
- PAIN and BREAK of the obvious fix (scene 3), with the count and the missed message.
- PREDICT with PAUSE (scene 4 and the check), SHOW right after.
- NAME after SHOW: heartbeat (scene 2, plain), digest, version and gossip (scene 5), generation and seeds (scene 6).
- GUARDRAIL (scene 6) and MORAL (scene 7) last. Light moments: the boss who fails (0:15), more time on the phone than
  at their desks (1:40), nobody calls back (1:50).

### Accuracy notes for the producer

- "Each node numbers every change" is per node: one counter, and heartbeats and state changes take the next number.
- The digest carries three numbers per node (node, generation, highest version); the video shows the version.
- Round 3's cass3 → cass4 exchange is a picture choice; the stepper only says all six know after 3 rounds.
- "About ten for a thousand" is log2 1,000 ≈ 10; the demo's medians are 2 rounds for 6 nodes and 8 for 6,000.
- Failure detection (phi) is the next section.
