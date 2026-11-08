package sfz.found.l04

// Reference answers for Designs.kt.

class FanOutOnWrite(private val graph: FollowGraph, private val cap: Int = 800) : Timelines {
    override val work = Work()
    // one precomputed timeline per user, newest first: this is the materialized view
    private val timelines = Array(graph.size) { ArrayDeque<Long>() }

    override fun post(author: Int, postId: Long) {
        for (follower in graph.followers(author)) {
            val timeline = timelines[follower]
            timeline.addFirst(postId)                       // newest at the front
            if (timeline.size > cap) timeline.removeLast()  // keep only the newest `cap`
            work.writes++                                   // one write per follower
        }
    }

    override fun homeTimeline(user: Int, limit: Int): List<Long> {
        work.lookups++                                      // the read is one list fetch
        return timelines[user].take(limit)
    }
}

fun lossFactor(follows: Int, reasonableLimit: Int = 2_000): Double =
    if (follows <= 0) 1.0 else minOf(reasonableLimit.toDouble() / follows, 1.0)

class Hybrid(
    private val graph: FollowGraph,
    private val celebrityFollowers: Int,
    private val cap: Int = 800,
    private val reasonableLimit: Int = 2_000,
) : Timelines {
    override val work = Work()
    private val timelines = Array(graph.size) { ArrayDeque<Long>() }
    private val celebrityPosts = HashMap<Int, ArrayList<Long>>()

    // the extreme on the write side: too many followers to fan out in time
    private fun isCelebrity(author: Int) = graph.followerCount(author) > celebrityFollowers

    // per reader, the celebrities they follow: the only lists a read has to merge in
    private val celebritiesFollowed: Array<IntArray> =
        Array(graph.size) { user -> graph.followees(user).filter(::isCelebrity).toIntArray() }

    // the extreme on the read side: follows so many accounts that they can't read it all anyway
    private val keepShare = DoubleArray(graph.size) { lossFactor(graph.followeeCount(it), reasonableLimit) }

    override fun post(author: Int, postId: Long) {
        if (isCelebrity(author)) {
            celebrityPosts.getOrPut(author) { ArrayList() } += postId
            work.writes++                                   // stored once, merged at read time
            return
        }
        for (follower in graph.followers(author)) {
            if (sample(postId, follower) >= keepShare[follower]) continue   // dropped on purpose
            val timeline = timelines[follower]
            timeline.addFirst(postId)
            if (timeline.size > cap) timeline.removeLast()
            work.writes++
        }
    }

    override fun homeTimeline(user: Int, limit: Int): List<Long> {
        work.lookups++                                      // the precomputed part
        val merged = ArrayList<Long>(timelines[user].take(limit))
        for (celebrity in celebritiesFollowed[user]) {
            work.lookups++                                  // one list per celebrity followed
            merged += recent(celebrityPosts[celebrity] ?: emptyList(), limit)
        }
        return merged.sortedDescending().take(limit)
    }
}
