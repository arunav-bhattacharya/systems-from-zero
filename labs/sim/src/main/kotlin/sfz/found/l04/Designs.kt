package sfz.found.l04

// Two more timeline designs. Read Timelines.kt first: FanOutOnRead is the finished reference,
// and Work is how every design reports what it cost. Count exactly as the KDoc says; the tests
// check the counts, not only the timelines.

/**
 * Fan-out on write: every user has a precomputed home timeline, newest first, holding at most [cap]
 * post ids (Twitter kept 800). A post is inserted into the timeline of every follower of its author,
 * one write per follower. A read is one lookup: return the first [limit] ids of the reader's timeline.
 */
class FanOutOnWrite(private val graph: FollowGraph, private val cap: Int = 800) : Timelines {
    override val work = Work()

    override fun post(author: Int, postId: Long) {
        TODO("add postId to the front of each follower's timeline, drop the oldest beyond cap, one write each")
    }

    override fun homeTimeline(user: Int, limit: Int): List<Long> {
        TODO("one lookup: the first `limit` ids of this user's timeline")
    }
}

/**
 * The share of timeline writes a user receives, from Bluesky's 2025 rule:
 * `min(reasonableLimit / follows, 1)`. A user who follows 4,000 accounts with a limit of 2,000 gets
 * half of the writes; one who follows 200 gets all of them.
 */
fun lossFactor(follows: Int, reasonableLimit: Int = 2_000): Double {
    TODO("reasonableLimit / follows, never more than 1.0 (and 1.0 for someone who follows nobody)")
}

/**
 * The hybrid that handles both extremes.
 *
 * Celebrities: an author with MORE than [celebrityFollowers] followers is not fanned out. Their post is
 * stored once in their own list (one write), like FanOutOnRead, and merged in when a follower reads.
 *
 * Everyone else is fanned out like FanOutOnWrite, with one change for heavy followers: a follower gets
 * the write only if `sample(postId, follower) < lossFactor(graph.followeeCount(follower), reasonableLimit)`.
 * Each write that is kept counts one write; a dropped one costs nothing.
 *
 * A read costs one lookup for the reader's own timeline plus one lookup for each celebrity the reader
 * follows. Merge them, newest first, and return the first [limit] ids.
 */
class Hybrid(
    private val graph: FollowGraph,
    private val celebrityFollowers: Int,
    private val cap: Int = 800,
    private val reasonableLimit: Int = 2_000,
) : Timelines {
    override val work = Work()

    override fun post(author: Int, postId: Long) {
        TODO("celebrity: one write to their own list; otherwise fan out, skipping the sampled-out writes")
    }

    override fun homeTimeline(user: Int, limit: Int): List<Long> {
        TODO("one lookup for the timeline, one per celebrity followed, merge newest first, take limit")
    }
}
