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
