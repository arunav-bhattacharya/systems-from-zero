package sfz.found.l02

import kotlin.random.Random

/**
 * One call from the root to one leaf. The first copy answers after [first] µs. If a hedge is sent,
 * the second copy goes to another replica and answers [second] µs after it was sent.
 */
data class LeafCall(val first: Long, val second: Long)

/**
 * The root sends one call to each leaf and must wait for all of them. Without hedging
 * ([hedgeAfter] = null) a leaf's latency is its [LeafCall.first].
 *
 * With hedging, any leaf that has not answered by [hedgeAfter] µs gets a second copy sent at that
 * moment; the leaf's latency is then whichever copy answers first: min(first, hedgeAfter + second).
 * A leaf that answers at or before [hedgeAfter] is never hedged.
 *
 * Returns the root's latency (the slowest leaf) and how many hedges were sent.
 */
fun rootLatency(calls: List<LeafCall>, hedgeAfter: Long?): Pair<Long, Int> {
    TODO("each leaf's latency, with or without a hedge; the root takes the slowest")
}

/** What a fan-out simulation measured. */
class FanOutResult(
    val root: LogHistogram,
    /** Fraction of user requests that took at least one second. */
    val slowFraction: Double,
    /** Hedges sent, as a fraction of the leaf calls a request needs without hedging. */
    val extraLoad: Double,
)

/**
 * Runs [requests] user requests, each fanning out to [leaves] leaves (finished). A leaf takes 5 to
 * 15 ms, except with probability [slowChance] when it takes 1 second (a pause, a compaction, a
 * full queue). If [correlated] is true, a slow leaf's hedge is slow too, as when every replica
 * shares the cause (the same bad deploy, the same overloaded disk).
 */
fun simulateFanOut(
    leaves: Int, requests: Int, hedgeAfter: Long?, slowChance: Double = 0.01,
    correlated: Boolean = false, seed: Long = 1,
): FanOutResult {
    val rnd = Random(seed)
    fun leaf(): Long = if (rnd.nextDouble() < slowChance) 1_000_000L else rnd.nextLong(5_000, 15_001)
    val root = LogHistogram()
    var slow = 0
    var hedges = 0L
    repeat(requests) {
        val calls = List(leaves) {
            val first = leaf()
            val second = if (correlated && first >= 1_000_000L) first else leaf()
            LeafCall(first, second)
        }
        val (latency, h) = rootLatency(calls, hedgeAfter)
        root.record(latency)
        if (latency >= 1_000_000L) slow++
        hedges += h
    }
    return FanOutResult(root, slow.toDouble() / requests, hedges.toDouble() / (requests.toLong() * leaves))
}
