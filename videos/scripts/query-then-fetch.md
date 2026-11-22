# Three volumes, one search: why a search asks every shard

- Slug / scene: `query-then-fetch`, `videos/scenes/query_then_fetch.py:QueryThenFetch`
- Lesson: `shard-09`, section 2, "A write goes to the primary, a search to one copy of every shard"
- Audience / level: a complete newcomer. Has met the lesson's encyclopedia, shards and replicas (sections 0 and 1);
  doesn't know how a search is run across shards, or why deep pages are capped.
- Length: about 5 minutes (~800 words of narration, two pauses and silent builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: a new shop goes to one shard, so why does a search for "northwind bikes" have to ask
  all of them, and why won't a site let you jump to page 1,000?
- Misconception to steelman and break: "a search is like a lookup: find the right shard and ask it" (broken: no shard
  knows what the others hold); "asking every shard for the whole answer is fine" (broken by deep paging, 50,000
  hits sorted to return 10).
- Concept chain: a write follows the id's hash to one shard → a word has no key, so the search asks one copy of
  every shard → query phase (ids and scores only), then fetch phase (the page's documents) → deep pages cost every
  shard; the slowest shard sets the pace; each shard counts rare words on its own (hardest last)
- Analogy family: the lesson's encyclopedia in three volumes, each with its own index at the back, and photocopies on
  other shelves. Looking up "bicycles" means opening all three indexes.
- Open loops: "why can't you jump to page 1,000?" planted in scene 1 → paid off in scene 6.
- Assumptions: all numbers and outputs are the lesson's (M-0054 hashes to shard 2, `"total":2,"successful":2`;
  `from: 9990, size: 10` on 5 shards = 50,000 hits; `max_result_window` 10,000; 0.99 to the power 10, about 90%;
  the "northwind bikes" hits and scores, plain and with `dfs_query_then_fetch`). Which shard each hit came from is
  not in the lesson, so the per-shard return chips carry no ids.

## The one picture

Top centre: the coordinating node (purple). Top left: the request chip. Top right: the merged hit list. Middle: three
shard columns, each a primary (blue) over its replica (grey, "copy"); first drawn as three gold encyclopedia volumes
with photocopies. Small chips under each column are what a shard sends back. Yellow dots are requests; red marks a
cost. Five columns replace three for the deep-paging scene.

## Scene 1 · The question · 0:00–0:25 · [QUESTION] [LOOP-PLANT]

VO: Support types "northwind bikes" into the shop search. The search index is split over three machines. When we look
up one shop by its id, we know exactly which machine to ask. But a word isn't an id. So how does the search find the
ten best shops? And why won't most sites let you jump straight to page 1,000? Hold both questions.

## Scene 2 · The encyclopedia · 0:25–1:10 · [FAMILIAR] [ANALOGY] [MAP]

VO: Picture an encyclopedia in three volumes, each with its own index at the back. To find every page about bicycles,
you open all three indexes and put the pages together. No volume can tell you what the others hold. And a careful
librarian keeps a photocopy of every volume on a different shelf.

OpenSearch, a free search program, works the same way. Each volume is a shard, a piece of the search index. Its index
at the back is the shard's inverted index, a list of every word with the documents that contain it. And each
photocopy is a replica, a copy of the shard kept on another machine.

## Scene 3 · A write goes to one shard · 1:10–1:45 · [SHOW]

VO: First, a write. A new shop, M-0054, can arrive at any node, which coordinates the request. It hashes the id, and
the hash says shard 2. So it sends the shop to shard 2's primary copy, which passes it on to the replica. Only when
both have it does the answer come back: total 2, successful 2. One shard, two copies, nobody else bothered.

## Scene 4 · A search asks everyone · 1:45–2:15 · [BREAK]

VO: Now the search. You might think it works the same way: find the right shard and ask it. But which shard holds
northwind? Each shard's index covers only its own shops, like the index at the back of one volume. No shard can say
which other shards hold matches. So the coordinator asks them all. It sends the query to one copy of every shard,
primary or replica, picking the copy that has answered fastest lately.

## Scene 5 · Query, then fetch · 2:15–3:05 · [SHOW] [NAME]

VO: Here's the trick that keeps it cheap. In the first round, each shard scores its own shops with BM25, the ranking
formula, and sends back only ids and scores, for the best few it has. No documents yet. That's the query phase. The
coordinator merges those short lists into one ranking. Then the second round asks for the full documents of the page
it will show, and nothing else. That's the fetch phase. Query, then fetch. Like jotting page numbers from each
volume's index before you carry any book to the desk.

## Scene 6 · Page 1,000 · 3:05–4:00 · [PREDICT] [PAUSE] [SHOW] [LOOP-PAYOFF] [JOKE:amplify] [GUARDRAIL]

VO: Now ask for a deep page: skip 9,990 hits and show 10, on an index with five shards. How many hits does the
coordinator have to sort? Pause and guess.

50,000. No shard knows where its hits fall in the overall order, so each must send its own top 10,000, and the
coordinator sorts all 50,000 to return 10. That's five librarians each copying out ten thousand page numbers so you
can read the last ten. So OpenSearch stops skip plus size at 10,000 by default, with a setting called max result
window. To go deeper, search after carries on from the last hit of the page before. And that's why page 1,000 is out
of reach.

## Scene 7 · The slowest shard · 4:00–4:25 · [GUARDRAIL]

VO: There's a second cost. A search is as slow as its slowest shard. Say each shard answers in time 99% of the time.
Then all 10 shards of a search answer in time only 0.99 to the power 10, about 90% of the time.

## Scene 8 · Each volume counts on its own · 4:25–5:05 · [BREAK] [SHOW]

VO: One more surprise. BM25 counts how rare a word is, and each shard counts only its own shops. With millions per
shard, they agree. With a handful, they don't. In the lesson's lab, the plain search ranks M-0045 first. Ask for D F S
query then fetch, which adds a first round to collect those counts from every shard, and M-0042, which has both words,
comes first again.

## Scene 9 · The moral, and a check · 5:05–5:40 · [MORAL] [PREDICT] [PAUSE]

VO: So the moral of the story: a search asks every shard, and more shards add work to every search. One quick check.
Support fetches shop M-0054 by its id. How many shards get asked? Pause and think.

Just one. The id hashes to shard 2, so it goes straight there. Words make you ask everyone; ids don't.

---

### Beat check

- QUESTION (1) → FAMILIAR + ANALOGY + MAP (2) → SHOW the write (3) → BREAK the lookup model (4) → SHOW + NAME
  query then fetch (5) → PREDICT + PAUSE, LOOP-PAYOFF, GUARDRAIL (6) → GUARDRAIL (7) → BREAK one-shard counting (8)
  → MORAL and check (9).
- Light moments: jotting page numbers (3:00), five librarians copying 10,000 page numbers (3:40).

### Accuracy notes for the producer

- The write path leaves out the translog, fsync, sequence numbers and primary terms, and the one-second refresh
  before a new shop is searchable (the lesson covers them).
- "The best few": each shard returns its top `from + size`; with the default `size` of 10 that's 10 per shard.
- The lab's "northwind bikes" search returns 4 hits: plain M-0045 0.769, M-0042 0.566, M-0043 0.284, M-0054 0.284;
  with dfs M-0042 0.929, M-0045 0.850, M-0043 0.735, M-0054 0.735.
- The 99% / 10 shards figure is the lesson's illustration (0.99^10 = 0.904).
- "Picking the copy that has answered fastest lately" is adaptive replica selection.
