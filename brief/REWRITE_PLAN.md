# The newcomer rewrite (started 2026-11-16)

The user asked: rewrite the whole site the way JVM Workbench rewrote its first tracks, with the venkat-voice
skill for the text and the venkat-style-video skill for every video, explaining each concept for a complete
novice who has none of the user's background. Videos render at 1440p (2560x1440) by default.

- Text rules: `brief/VOICE.md`. Video rules: `videos/REMAKE_BRIEF.md`.
- Site support added: lessons may carry `opening`, `closing` and one section `aside`; with an `opening`, the
  `analogy`, `in_your_world` and `mistake` callouts become optional (validator, build and app).
- Usage rule (user, 2026-11-08): check weekly usage before each batch; at 60% ship what is finished and park
  the rest for the next week. On 2026-11-16 the week was already at 68% when this started, so only the pilot
  ran; the rest waits for the reset (2026-11-21, 21:00 UTC) unless the user says otherwise.

## Order and batches

One batch is one track: rewrite its lessons (about 3 lessons per writer), validate, ship; then remake its
videos (2 or 3 per maker, one render at a time per maker), ship. Course order:

| Track | Lessons | Videos |
|---|---|---|
| found | 6 | 5 |
| net | 12 | 10 |
| os | 12 | 11 |
| sql | 10 | 9 |
| model | 9 | 5 |
| store | 14 | 13 |
| cache | 10 | 10 |
| enc | 5 | 5 |
| repl | 8 | 8 |
| shard | 9 | 9 |
| txn | 8 | 8 |
| dist | 8 | 7 |
| cons | 6 | 6 |
| msg | 12 | 12 |
| stream | 8 | 7 |
| batch | 15 | 11 |
| derive | 6 | 4 |
| **Total** | **158** | **140** |

Track pages (`content/tracks/<id>.json`) get the same treatment with their track's batch.

## Progress log

- 2026-11-16: briefs written, site support added. Pilot lesson found-01 rewritten and shipped (opening 177 words,
  closing 117, sections 2,698). Weekly usage reached 73%, so the pilot video (derived-data) and every other
  batch are parked for the reset. Next: remake derived-data at 1440p as the video pilot, then batch found.
- 2026-11-16 (later): the user chose to continue past the cap. Wave 1 shipped: found-02, 03, 05, 06 and all of
  net-01 to net-12 (17 of the 18 lessons in the two tracks). Usage went 73% to about 90%, so writers were stopped
  after their current lesson. Still to do in these tracks: found-04 (an unreviewed draft script is in
  `brief/drafts/found-04-unreviewed.py`), the track pages `content/tracks/found.json` and `net.json`, and every
  video. The pilot video (derived-data) was in progress.
- 2026-11-16 (end of day): found-04 and the track pages `found.json` and `net.json` rewritten, so the text of
  Foundations and Computer networking is complete. Pilot video derived-data remade (5:02 at 1440p, script in
  `videos/scripts/derived-data.md`) and shipped. Usage about 90%: stopped for the week.
  **Next (after the reset):** remake the other 4 Foundations videos and the 10 networking videos (they still
  tell the old story), then text for os, sql, model and onward in course order.
- Weekly usage was refreshed to 0% (user: "Try now"). Wave 2 started: remakes of the 14 Foundations and networking
  videos (4 makers) and the os and sql text (8 writers, task sheet `brief/WRITER_TASK.md`). Cost seen in wave 1:
  roughly 0.7% of a week per lesson and 2% per remade video.
- Shipped: SQL (10 lessons and track page) and Operating systems (12 lessons and track page). Usage 9%.
  Shipping now builds and deploys from a clean worktree at the committed state (`git worktree add --detach`),
  then fast-forwards main, so half-edited lessons and half-rendered videos in the main checkout never go live.
  Running: the 14 found and net video remakes, model and store text, cache and enc text.
- Shipped text: Data models, Storage engines, Encoding, Caching (all lessons and track pages). Text is now done for
  found, net, os, sql, model, store, cache and enc (83 lessons + 8 track pages). Part III text is being written.
- Shipped videos: derived-data plus 8 more (tail-fanout, retry-storm, home-timeline, storage-compute,
  net-encapsulation, arp, nat, routing), each 4 to 5 minutes at 1440p. Usage 19%.
- Video queue (at most 4 makers at once: this 12-core machine hit a load of 50 with 4 makers and 14 writers):
  running: net-07..12 (2 makers), os videos 1-4 and 5-8 (2 makers). Next: inodes-links, epoll, namespaces-cgroups;
  then sql (9), model (5), store (13), cache (10), enc (5), then Part III and Part IV as their text lands.
  Ship script: build and deploy from a clean worktree (see the note above).
- The session runs at most 20 agents at once. Part IV writers started: msg-01..03, msg-04..06, msg-07..09,
  msg-10..12 + track, stream-01..03. Queued (start one per free slot, in this order): stream-04..06,
  stream-07..08 + track, batch-01..03, batch-04..06, batch-07..09, batch-10..12, batch-13..15 + track,
  derive-01..03, derive-04..06 + track. Video makers keep 4 of the 20 slots.
- Shipped videos so far: all 5 Foundations and all 10 networking videos.
- Part III shipped: Replication, Partitioning, Transactions, Faults time and truth, Consistency and consensus
  (39 lessons and 5 track pages). Text is live for 13 of 17 tracks (117 lessons). All 14 Part IV writers running.
- TEXT DONE: all 158 lessons and 17 track pages rewritten and live (usage 40%). A jargon review of the 89
  remaining working-world terms in main prose (`brief/jargon_sweep.md`) is running.
- Videos: 15 of 140 remade and live (found, net). In progress: os 1-4, os 5-8, os 10-12 + sql-01, sql 2-5.
  Next in the queue: sql 6-9 (window-functions, gaps-islands, keyset-pagination, upsert-race), model (5),
  store (13), cache (10), enc (5), repl (8), shard (9), txn (8), dist (7), cons (6), msg (12), stream (7),
  batch (11), derive (4). Pause and ask the user at 60% weekly usage.
- User rule (2026-11-16): when weekly usage reaches 60%, stop until the weekly reset (next: 2026-11-21 21:00 UTC).
  Don't ask to continue. Ship what is complete; resume the video queue after the reset.
- Videos live: 31 (found 5, net 10, os 11, sql 5). Cloudflare Workers refuses assets over 25 MiB; one 28.9 MiB
  render failed a whole deploy silently, so the ship script now checks sizes and fails loudly. Running at 44%:
  sql 6-9, model (5), store 1-4, store 5-8. Next after the reset: store 9-13, cache, enc, repl, shard, txn, dist,
  cons, msg, stream, batch, derive.
- 2026-11-17: usage reached 57%, so the wind-down started: makers finish their current video and stop.
  Data models: 4 of 5 shipped. graph-hops is half done: new script and scene are written (uncommitted) and a
  QUICK draft is at `videos/media/graph-hops-draft.mp4`; it still needs a contact-sheet review, the 1440p render
  with POSTER=, check_audio and ffprobe. Title: "Follow the strings".
- hnsw-search is rendered (1440p, 13.1 MiB, script and scene in place, uncommitted) but held back: check_audio
  heard "bike rental" in the first line as "by grantal" and "PostgreSQL" once as "posters". Listen to both, add
  SAY rules if they're real, re-render, then ship. Title: "Nearest by meaning: walking a graph from the top layer down".

## Parked at the 60% stop (2026-11-17, weekly usage 58%)

Done and live: all 158 lessons and 17 track pages; 46 of 140 videos remade at 1440p
(found 5/5, net 10/10, os 11/11, sql 9/9, model 4/5, store 7/13).

Resume after the weekly reset (2026-11-21 21:00 UTC), in this order:
1. graph-hops (model-08): finish from its QUICK draft (see the note above).
2. hnsw-search (store-08): rendered; check the two flagged words, then ship (see the note above).
3. store-09..13: volcano-vs-vector, join-order, column-compression, view-maintenance, graph-records.
4. Then cache (10), enc (5), repl (8), shard (9), txn (8), dist (7), cons (6), msg (12), stream (7), batch (11),
   derive (4): 87 videos. At most 4 makers at once; each maker takes 4 videos (about an hour each batch).
Ship with the clean-worktree script: it uploads each shipped mp4 to the GitHub release `videos` (--clobber) and
deploys the rest. Since 2026-11-17 the repo is public and every MP4 is served from that release through
site/worker.js; Cloudflare holds no videos. Check live byte sizes after shipping.

## Resumed after the reset (2026-11-22, weekly usage 5%)

Pending: 94 videos. Makers follow `videos/MAKER_TASK.md`. Round 1 running: graph-hops (finish) + hnsw-search
(verify) + store-09, store-10; store-11..13 + cache-01; cache-02..05; cache-06..09. The 60% weekly stop still
applies: at 60%, ship what's finished and stop until the next reset.
