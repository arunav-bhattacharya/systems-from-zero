package sfz.found.l04

// Finished: read it, don't change it. The same file is in src/solution.

/**
 * The work a timeline design does, counted in two units:
 * a write stores one post id in one list; a lookup fetches one list.
 */
class Work {
    var writes = 0L
    var lookups = 0L
}

/** A home-timeline service. Post ids grow with time, so a bigger id is a newer post. */
interface Timelines {
    val work: Work

    /** [author] publishes the post [postId]. */
    fun post(author: Int, postId: Long)

    /** The newest [limit] post ids by the accounts [user] follows, newest first. */
    fun homeTimeline(user: Int, limit: Int): List<Long>
}

/**
 * Fan-out on read, the simplest design: every post goes into its author's own list, and a read
 * fetches the list of every account the reader follows and merges them. Cheap posts, expensive reads.
 * This is the design the lab's tests use as the reference for what a timeline should contain.
 */
class FanOutOnRead(private val graph: FollowGraph) : Timelines {
    override val work = Work()
    private val postsBy = Array(graph.size) { ArrayList<Long>() }

    override fun post(author: Int, postId: Long) {
        postsBy[author] += postId          // one write, whoever the author is
        work.writes++
    }

    override fun homeTimeline(user: Int, limit: Int): List<Long> {
        val merged = ArrayList<Long>()
        for (followee in graph.followees(user)) {
            work.lookups++                 // one lookup per account followed
            merged += recent(postsBy[followee], limit)
        }
        return merged.sortedDescending().take(limit)
    }
}

/** The newest [limit] ids of a list that grows at the end (oldest first). */
fun recent(oldestFirst: List<Long>, limit: Int): List<Long> =
    oldestFirst.subList(maxOf(0, oldestFirst.size - limit), oldestFirst.size)

/**
 * A fixed pseudo-random number in [0, 1) for one (post, follower) pair, so that dropping writes on
 * purpose is repeatable: the same pair always gets the same number. (SplitMix64's mixing steps.)
 */
fun sample(postId: Long, follower: Int): Double {
    var z = postId * 0x9E3779B97F4A7C15uL.toLong() + follower
    z = (z xor (z ushr 30)) * -0x40a7b892e31b1a47L
    z = (z xor (z ushr 27)) * -0x6b2fb644ecceee15L
    z = z xor (z ushr 31)
    return (z ushr 11).toDouble() / (1L shl 53).toDouble()
}
