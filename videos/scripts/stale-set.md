# How did the old name get back? The stale set, and the lease that stops it

- Slug / scene: `stale-set`, `videos/scenes/stale_set.py:StaleSet`
- Lesson: `cache-07`, section 1, "The stale set: a slow reader puts the old name back after the delete" (the fix is the
  lease from section 2)
- Audience / level: a complete newcomer. Knows cache-aside and "commit, then delete the copy" from the last lesson;
  doesn't know what a fill, a lease or a Lua script is.
- Length: 5:15 (~880 words of narration plus two pauses and the walks)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=254.8` (the lease replay done: A's fill refused, B's fill of v2 stored, the timeline green)
- The learner's real question: every save deletes the cached copy. How can the old name come back an hour later?
- Misconception to steelman and break: "things happen in the order the code lists them" (broken by the slow reader);
  then the tempting fix "delete again a moment later" (shrinks the gap, doesn't close it).
- Concept chain: commit then delete → a slow reader reads v1 before the commit and fills after the delete (a stale
  set) → the gap is rare per request, common across millions → a delayed second delete only shrinks it → a lease a
  write can tear up, checked and filled in one script (hardest last)
- Analogy family: the lesson's shop window. The back-office list is the database, the window is Redis, a tag is the
  cached copy, taking it down is DEL, a slow clerk is reader A, a numbered ticket is the lease.
- Open loops: "how did the old name get back in?" planted in scene 1 → answered in scene 12.
- Assumptions: names and versions are the lesson's (Fietsen Utrecht v1, Velo Utrecht v2, `merchant:{m-17}`, EX 3600,
  `lease:{m-17}`, tokens t-A and t-B, NX PX 10000; DEL answering 0 keys, then 1 key, the lease). Meta's figures (one
  write in a million wrong after five minutes; TAO's quadrillion reads a day) are the lesson's.

## The one picture

Left: the database, "the back-office list", holding row m-17 (v1 white, v2 green). Right: Redis, "the shop window",
with `merchant:{m-17}` and a tag (or "(empty)"), and a yellow lease line under it. Between them three chips walk back
and forth: reader A (purple), the writer (blue), reader B (green), carrying gold tags. Under everything, a timeline of
six numbered steps with a label each. Yellow is a step done, red the stale result, green a refused or correct fill.

## Scene 1 · The question · [QUESTION] [LOOP-PLANT]

VO: A bike shop in Utrecht changes its name, from Fietsen Utrecht to Velo Utrecht. The save deletes the cached copy
right after, as it should. An hour later, a customer's receipt still says Fietsen Utrecht. If every save deletes the
copy, how did the old name get back in?

SCREEN: The database (v1, then v2 Velo Utrecht) and Redis (the tag deleted, "deleted after the save"). Then Redis
holds a red "v1 Fietsen Utrecht", "an hour later: the old name".

## Scene 2 · The rule · [FAMILIAR]

VO: The rule from the last lesson is simple. Commit the new row to the database, then delete the copy in Redis. The
next reader misses, loads the new row, and fills the cache. So far so good.

SCREEN: The writer walks to the database (v2), then to Redis (the tag goes). Reader B walks to Redis (miss), to the
database (picks up a green v2 tag) and fills the window.

## Scene 3 · The shop window · [ANALOGY] [MAP]

VO: Picture a shop window. The prices live on a list in the back office, and clerks copy them onto tags for the
window. When a price changes, someone takes the old tag down, and the next clerk copies a fresh one. The list is the
database. The window is Redis. A tag is the cached copy, and taking it down is the delete.

SCREEN: Each part glows as it is named; subtitles "the back-office list" and "the shop window" appear; caption "a tag:
the cached copy. taking it down: DEL".

## Scene 4 · The slow clerk · [SHOW] [PREDICT] [PAUSE] [BREAK]

VO: Now picture a slow clerk. Start again: version 1 in the database, and nothing in Redis. Reader A, a server
checking a payment, misses on the shop's key. It reads the row: version 1, Fietsen Utrecht. Then it stalls before it
can store it: a pause to clean up memory, or a wait for a database connection. Meanwhile, the writer renames the shop
and commits version 2. Then it deletes the copy. But the window is empty, so the delete removes nothing: zero keys
deleted. Now reader A wakes up and sends its SET: Fietsen Utrecht, for an hour. Will Redis take it? Pause and guess.
It does. Redis keeps no record of the delete, and no versions, so it stores the old name for an hour. Reader B, and
every reader after it, gets Fietsen Utrecht. And no save is coming to delete it: the save that should have deleted it
was already over.

SCREEN: The six-step timeline appears. Reader A misses (step 1), picks up v1 (step 2) and shows a yellow pause sign.
The writer commits v2 (step 3) and finds the window empty: "DEL: 0 keys deleted" (step 4). A wakes, the countdown runs,
A pins its tag: "SET v1 EX 3600: OK" in red (step 5). B gets a red v1 tag (step 6).

## Scene 5 · The name · [NAME]

VO: Storing a copy after a miss is called a fill. A fill that stores a value already out of date when it arrives is
called a stale set. Meta, the company behind Facebook, named it in a paper about its cache, memcache.

SCREEN: "a stale set: a fill that was out of date when it arrived"; step 5 pulses; "the name: Meta's memcache paper".

## Scene 6 · The gap, and what it costs · [GUARDRAIL] [JOKE:is-the-explanation]

VO: The race needs two things: A's read comes before the commit, and A's fill comes after the delete. Between a read
and its fill there's usually a millisecond or two. A pause can stretch it to hundreds. So it's rare for one request,
and frequent across millions. When Meta measured its own cache, about one write in a million was still wrong five
minutes later. One in a million sounds safe, until you serve a quadrillion reads a day. At that volume, it's a steady
stream of wrong answers. Here the TTL caps the damage at an hour. For a shop's name, that's a nuisance. For a flag
that says the shop is suspended for fraud, it's an hour of payments that should have been refused.

SCREEN: A yellow frame around steps 2 to 5, "the gap"; it stretches on "hundreds". Captions with Meta's figures; "TTL:
1 hour"; the suspended-flag caption in red.

NOTE: The quadrillion line is the light moment, cashed back at once ("a steady stream of wrong answers").

## Scene 7 · The tempting fix · [BREAK]

VO: The tempting fix is to delete the key again, a moment later. It helps, since most slow readers finish within the
wait. But a reader that pauses longer still gets in. It shrinks the gap without closing it, and you have to guess how
slow your slowest reader can be.

SCREEN: The writer deletes again ("second DEL: 1 key deleted", green); then reader A, paused longer, pins its old tag
again ("a later SET: the old name again", red).

## Scene 8 · The ticket · [ANALOGY] [NAME]

VO: Back to the window. Before a clerk copies a price, he takes a numbered ticket from the office. A price change
tears up every ticket for that item, and the window takes a tag only with a ticket that's still valid. That ticket is
called a lease. In Redis, the reader takes it on a miss: SET lease, a random token, NX, PX 10000. NX means only if
nobody holds it, and PX 10000 lets it vanish after ten seconds if the reader crashes. After its commit, the writer
deletes the copy and the lease, in one command. And the fill runs as a small script inside Redis: if the lease still
holds my token, store the name, otherwise store nothing. A script runs as one command, so no delete can land between
the check and the store.

SCREEN: A yellow "ticket 41" under the window, which wiggles on "tears up"; it becomes "lease:{m-17} = t-A". Captions
spell `SET lease:{m-17} <random token> NX PX 10000`, the writer's two-key DEL, and the script's rule.

## Scene 9 · The replay · [SHOW]

VO: Replay the race. A misses, takes lease t-A, reads version 1, and stalls. The writer commits version 2 and deletes
both keys: one key deleted, the lease. A wakes up, and its fill is refused: the lease is gone. The old name never
reaches the window. Reader B misses, takes lease t-B, reads version 2, and fills Velo Utrecht.

SCREEN: The timeline relabels: "A: miss, lease t-A", "A: SELECT v1", "W: UPDATE v2", "W: DEL copy + lease", "A: fill
refused", "B: lease t-B, fills v2". The lease line appears, goes with the writer's DEL ("1 key deleted (the lease)"),
A's tag gets a cross and falls, B fills a green v2 ("fill with t-B: stored").

## Scene 10 · Two notes · [GUARDRAIL]

VO: Two notes. A lease works only when every fill starts with a miss; the lesson's next fix, a version number, covers
the rest. And keep the TTL: it caps whatever still slips through.

SCREEN: Captions only, over the finished replay.

## Scene 11 · The code, in Java and Kotlin · [SHOW]

VO: In Java and Kotlin, the reader takes the lease with SET, NX and PX, and fills with one EVAL of the script. The
writer sends one DEL with both keys.

SCREEN: The diagram dims; Java and Kotlin side by side: the `SET ... nx().px(10_000)` lines, the `eval(FILL_WITH_LEASE,
...)` lines and `redis.del(KEY, LEASE)` glow in turn.

## Scene 12 · The moral, and a check · [MORAL] [RECAP] [LOOP-PAYOFF] [PREDICT] [PAUSE]

VO: So how did the old name get back in? A slow reader put it there after the delete. On a busy system, things don't
happen in the order your code lists them, so a late copy must show a ticket that's still valid. One quick check.
Reader A takes the lease and stalls for three seconds, but nobody renames the shop. Is A's fill stored or refused?
Pause and think. Stored. Nothing tore up its ticket, and version 1 is still true. A lease refuses only copies that a
write has made old.

SCREEN: The diagram returns. For the check: a fresh timeline, the lease t-A, A with a v1 tag and a pause sign, the
writer idle; countdown; A's fill stored ("fill with t-A: stored"). Last caption "a lease refuses only copies a write
has made old".

---

### Beat check

- QUESTION (scene 1), FAMILIAR (scene 2), ANALOGY and MAP (scene 3) before any new term.
- PREDICT with PAUSE in scene 4 and in the check (scene 12); SHOW right after each.
- BREAK: the order the code lists (scene 4) and the second delete (scene 7).
- NAME after SHOW: fill and stale set (scene 5), lease (scene 8).
- GUARDRAIL (scenes 6, 10), MORAL and the check (scene 12). Light moments: the quadrillion reads (about 2:30), the
  ticket torn up (3:20), the check's twist that a lease is no enemy of correct fills.

### Accuracy notes for the producer

- The race and its outputs are the lesson's stepper and `StaleSetDemo`: `W  DEL: 0 keys deleted`, `A  SET Fietsen
  Utrecht EX 3600: OK`, B reads the stale name; in the lease race, `DEL value and lease: 1 keys deleted`, A's fill
  `refused, the lease is gone`, B takes `t-B` and gets `Velo Utrecht (fresh)`.
- The video's "pause" stands for the lab's latch; the lesson names a garbage-collection pause and a wait for a
  database connection as real causes.
- "One write in a million wrong after five minutes" and "more than a quadrillion reads a day" are Meta's TAO figures
  as the lesson reports them.
- The lease's fill script (GET the lease, compare, SET with EX 3600, DEL the lease) is shown only as its rule; the
  lesson prints the four Lua lines. A reader that waits too long for someone else's lease reads the database and never
  fills; the video leaves that to the lesson.
- The check's answer follows from the script: nothing deleted the lease within its 10 seconds, so the token still
  matches and the fill is stored.
- Versions with tombstones (section 3) and the database's log (section 4) are only named as "the next fix".
