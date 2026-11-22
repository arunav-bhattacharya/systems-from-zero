# Nearest by meaning: walking a graph from the top layer down

- Slug / scene: `hnsw-search`, `videos/scenes/hnsw_search.py:HnswSearch`
- Lesson: `store-08`, section 3, "Finding by meaning: walk a graph to the nearest neighbours, approximately"
- Audience / level: a complete newcomer. Has never heard of an embedding, a vector index or recall.
- Length: 4:50 (~770 words of narration at Kokoro's ~175 words a minute, plus two pauses and silent builds)
- Poster: `POSTER=153.5` (the walk done: the green beam of four, "distances worked out: 10")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: support wants past complaints that mean the same as a new one, with no shared words.
  How does a database find "similar" among millions, fast?
- Misconception to steelman and break: (1) "a sorted index will do", broken by one order against hundreds of
  directions; (2) "the search returns the true nearest neighbours", broken by recall (0.89 at a beam of 10);
  (3) "a filter just narrows the answer", broken by LIMIT 10 coming back with 4 rows.
- Concept chain: text becomes a vector, close means similar → exact search measures every vector → a layered graph:
  long links on top, every vector at the bottom → the walk (greedy on top, a beam at the bottom) → it's approximate:
  recall, and the filter trap (hardest last)
- Analogy family: the lesson's motorways above town roads, told as a drive to a friend's house: motorway with exits
  far apart, then a main road, then the streets. In the filter scene, a sat-nav that finds 40 shops, throws away the
  closed ones and hands you 4.
- Open loops: "among millions, fast?" planted in scene 1 → 10 distances instead of 16, and 654 pages instead of 2,138
  (scenes 4 and 5); the beam (scene 4) → recall (scene 6) → the check (scene 9).
- Assumptions: the walk is the lesson's stepper exactly (16 vectors at 90 to 610, layer 2 at 120, 330, 570; layer 1 at
  120, 220, 330, 440, 500, 570; the query at 515; ef = 4; distances 2, 3, 5, 10; answer 470, 500, 530, 570). Lab numbers
  are the Try it's (100,000 vectors of 32 numbers, 2,138 pages, about 8 ms; 654 pages, under 1 ms; recall 0.89 at 10 and
  1.0 at 40; 4.0 rows of 10 with the filter, 10.0 with relaxed_order; 41 MB index for 17 MB of vectors). The 2D scatter,
  the vector `[0.12, -0.80, 0.33, ...]`, and which 4 of the 40 candidates pass the filter are made up for the picture.

## The one picture

Three long bands stacked, layer 2 on top ("motorway", then "layer 2"), layer 1 ("main roads"), layer 0 ("streets"):
16 vectors as circles at the stepper's positions, grey links between neighbours, dashed drops between the same vector
on two layers. A yellow dot marks the query on each layer. Blue: where the search stands; grey: looked at and left;
green: the answer. "distances worked out: n" at the top left. Under the bands: a strip of 40 candidates for the filter
scene, one counter line, and captions.

## Scene 1 · The question · 0:00–0:21 · [QUESTION] [LOOP-PLANT]

VO: A customer writes to support: charged twice for one bike rental. Support wants past complaints like it, by
meaning, not by shared words. So duplicate charge, scooter hire should match, though it shares no word with the first.
How does a database find complaints that mean the same thing, among millions, fast?

SCREEN: Title card. Yellow chip "charged twice for one bike rental"; green chip "duplicate charge, scooter hire";
captions "not one word in common", "among millions, fast?".

## Scene 2 · Vectors, and the plain way · 0:21–1:17 · [FAMILIAR] [NAME] [SHOW] [PAIN] [BREAK]

VO: First, meaning has to become something a computer can measure. A model, a program trained on huge amounts of
text, turns each text into a vector: a list of a few hundred to a few thousand numbers. Texts with similar meanings
land close together, like points on a map. Only this map has hundreds of directions instead of two. So finding similar
complaints means finding the nearest points to the new one. The plain way: measure the distance from the query to every
vector, and keep the closest. In the lab, that's 100,000 vectors of 32 numbers, 2,138 pages, about 8 milliseconds. Now
picture 50 million complaints of 1,536 numbers each: 77 billion multiplications and additions for every question. And a
sorted index can't help. It has one order, and this map has hundreds of directions.

SCREEN: The query chip moves up; a mono caption of a vector. A scatter of grey points and the yellow query; its four
nearest turn green. Lines from the query to every point. Counter lines with the lab's and the lesson's numbers.

## Scene 3 · The drive · 1:17–1:41 · [ANALOGY] [MAP]

VO: So think how you drive to a friend's house in another city. Motorway first, with exits far apart, to the exit
nearest their town. Then a main road. Then the streets, to the door. Map it. Every vector is a house on the streets,
linked to its nearest neighbours. A random few are also on main roads, and fewer still on the motorway, with longer
links between them.

SCREEN: The bands build top-down as "motorway", "main roads", "streets", with their vectors and links. The 16 street
vectors pulse; dashed drops appear; the labels become "layer 2", "layer 1", "layer 0".

## Scene 4 · The walk · 1:41–2:34 · [SHRINK] [SHOW] [NAME]

VO: Here's a small one, drawn in one direction so it fits: 16 vectors, three layers, and the query, the yellow dot. The
search starts at the single entry point on the motorway. It measures the distance to each neighbour, and moves to any
that is closer. 330 is closer: move. Then 570, closer still. From 570, no neighbour on this layer is closer. So it
drops to the same vector, one layer down. There, 500 is closer: move. Nothing next to 500 is. On the streets, it stops
taking the first better step, and keeps a beam: the 4 best vectors seen so far. It explores around them until nothing
left can beat the worst one it holds. The beam is the answer: the four closest vectors, found with 10 distance
calculations, where measuring every vector takes 16.

SCREEN: The stepper's frames. Blue rings move 120 → 330 → 570 on layer 2 ("distances worked out: 2", "3"), drop to
570 on layer 1, move to 500, check 440 ("5"), drop to 500 on layer 0; the beam spreads to 470 and 530, looks at 440
and 570, then 610 ("10"); 470, 500, 530 and 570 turn green; the used links turn blue.

NOTE: Clean walkthrough, no jokes.

## Scene 5 · The name · 2:34–3:02 · [NAME] [LOOP-PAYOFF]

VO: This is called HNSW, hierarchical navigable small world, from a 2016 paper by Malkov and Yashunin. pgvector, an
add-on that stores vectors in PostgreSQL, builds it, with 16 links per vector and a beam of 40 by default. In the lab,
the walk read 654 pages, where measuring every vector read 2,138, and it answered in under a millisecond.

SCREEN: Caption with the name; `pgvector defaults: m = 16 links, hnsw.ef_search = 40`; "HNSW: 654 pages, under 1 ms /
exact: 2,138 pages, about 8 ms".

## Scene 6 · Approximately · 3:02–3:25 · [BREAK] [NAME]

VO: That's great, but there's a catch in the word walk. The search only goes where links lead. A true neighbour behind
a poor link can be missed. The share of the true nearest neighbours that comes back is called recall. In the lab, with
a beam of 10, the walk found 89 percent of the true top 10. With the default beam of 40, all of them. A bigger beam
finds more, and does more work.

SCREEN: Captions; "beam 10: recall 0.89", then "beam 40: recall 1.00".

## Scene 7 · The filter trap · 3:25–4:04 · [PREDICT] [PAUSE] [BREAK] [JOKE:is-the-explanation]

VO: Now a trap. Support adds a filter that keeps about 1 complaint in 11, and asks for 10 results. How many come back?
Pause and guess.

(three seconds)

4, on average. pgvector applies the filter after the walk. The walk collected its 40 candidates, and the filter kept
about 4. Nothing fails, and nothing warns you. It's a sat-nav that finds 40 shops near you, throws away the closed
ones, and proudly hands you 4. Since pgvector 0.8.0, an iterative scan keeps walking until enough rows pass: 10 of 10.

SCREEN: Countdown. "asked for 10, got 4 on average"; a strip of 40 teal candidates, 36 go dark, 4 turn green.
`SET hnsw.iterative_scan = relaxed_order`; "iterative scan: 10 of 10".

NOTE: The sat-nav line restates the trap in one picture: the answer is quietly short.

## Scene 8 · Memory · 4:04–4:15 · [GUARDRAIL]

VO: And a cost: the index took 41 MB for 17 MB of vectors. Every hop jumps to a random place, so HNSW wants its whole
graph in memory.

SCREEN: "the index: 41 MB, for 17 MB of vectors"; two long hops; caption.

## Scene 9 · The moral, and a check · 4:15–4:50 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So the moral of the story: to find nearest by meaning, walk the graph, big jumps on top and small steps at the
bottom, and keep a short list of the best. You trade a little recall for a lot of speed, so measure it. One quick
check. Your search returns 89 percent of the true top 10. What do you turn up? Pause and think.

(three seconds)

The beam, ef_search. In the lab, raising it from 10 to 40 found all 10, for a little more work.

SCREEN: The top links, then the bottom links pulse; moral captions. "recall 0.89"; countdown; "hnsw.ef_search: 10 ->
40, recall 0.89 -> 1.00".

---

### Beat check

- Opens with QUESTION (scene 1). FAMILIAR (points on a map) before any index term.
- PAIN (77 billion), BREAK of the sorted index (scene 2); ANALOGY and MAP (scene 3).
- SHOW: the stepper's walk (scene 4); NAME after it: HNSW (scene 5), recall (scene 6).
- BREAK: approximate (scene 6), the filter (scene 7). PREDICT with PAUSE twice (scenes 7 and 9).
- GUARDRAIL (scenes 7 and 8), MORAL and check (scene 9). Light moment: the sat-nav (3:55); "a catch in the word
  walk" (3:02) is the mild one.

### Accuracy notes for the producer

- The stepper draws one dimension; real embeddings have hundreds. The distances counter shows only the stepper's
  values (2, 3, 5, 10).
- The filter in the Try it is `id % 11 = 0` (about 1 item in 11 in every cluster); "a filter that keeps about 1
  complaint in 11" stands for it. The 4.0 and 10.0 are its averages over 20 queries at `ef_search = 40`.
- Recall moves from build to build because HNSW picks layers at random (the lesson saw 0.955 on another run at 10).
- `m = 16` and `ef_search = 40` are pgvector's defaults; `ef_construction = 64` is left to the lesson.
- DiskANN, quantization and re-ranking, for a billion vectors, are left to the lesson.
