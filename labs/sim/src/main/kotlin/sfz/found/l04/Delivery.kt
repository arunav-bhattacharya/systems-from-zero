package sfz.found.l04

// How long until a post reaches the last follower, in virtual time (no clocks, no sleeping).

/** A post that enters the fan-out queue at [atSecond] and needs [writes] timeline writes. */
data class QueuedPost(val atSecond: Double, val writes: Long)

/**
 * Fan-out workers take posts from ONE queue in arrival order and together do [writesPerSecond]
 * timeline writes a second. A post starts when it has arrived and the post before it has finished;
 * it finishes `writes / writesPerSecond` seconds after it starts.
 *
 * Returns, for each post in the order given, its delivery time: finish minus arrival, in seconds.
 * [posts] are sorted by `atSecond`.
 */
fun deliverySeconds(posts: List<QueuedPost>, writesPerSecond: Double): List<Double> {
    TODO("walk the posts in order, keeping the time at which the queue is next free")
}

/**
 * The most followers a post can have and still reach all of them within [deadlineSeconds], when it has
 * the fan-out workers to itself. Accounts above this are the ones a hybrid should merge at read time.
 */
fun celebrityThreshold(writesPerSecond: Double, deadlineSeconds: Double): Long {
    TODO("throughput times deadline, rounded down")
}
