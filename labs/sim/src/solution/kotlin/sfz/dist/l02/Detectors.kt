package sfz.dist.l02

import kotlin.math.log10
import kotlin.math.max
import kotlin.math.sqrt

/**
 * Lesson dist-02: two failure detectors. Neither can know whether the node is dead. Each turns
 * "how long since the last heartbeat" into a suspicion, in a different way.
 */
interface FailureDetector {
    /** A heartbeat arrived at [atMs]. Calls come in time order. */
    fun heartbeat(atMs: Long)

    /** Whether the node is suspected at [nowMs]. Before the first heartbeat, nothing is suspected. */
    fun suspects(nowMs: Long): Boolean
}

/**
 * Exercise 1. Suspects the node once the silence since the last heartbeat is longer than [timeoutMs]
 * (strictly longer: at exactly [timeoutMs] it still trusts the node).
 */
class FixedTimeoutDetector(val timeoutMs: Long) : FailureDetector {
    private var last: Long? = null

    override fun heartbeat(atMs: Long) {
        last = atMs
    }

    override fun suspects(nowMs: Long): Boolean {
        val l = last ?: return false
        return nowMs - l > timeoutMs                       // silence is all a detector can measure
    }
}

/**
 * Exercise 2. The phi accrual detector of Hayashibara and colleagues, with the gaps between
 * heartbeats modelled as a normal distribution (Akka's choice; Cassandra uses an exponential one).
 *
 *  - Keep the last [windowSize] gaps between consecutive heartbeats.
 *  - phi(now) = -log10(P), where P = [probabilityLater] (time since the last heartbeat, the mean gap,
 *    the standard deviation of the gaps). Use the population standard deviation (divide by n), and
 *    never less than [minStdDevMs], so a perfectly regular link doesn't give a zero.
 *  - phi is 0.0 until at least one gap has been seen.
 *  - Suspect when phi is greater than [threshold].
 */
class PhiAccrualDetector(
    val threshold: Double = 8.0,
    val windowSize: Int = 1_000,
    val minStdDevMs: Double = 100.0,
) : FailureDetector {
    private val gaps = ArrayDeque<Long>()
    private var sum = 0.0                                  // running sums keep each check O(1)
    private var sumOfSquares = 0.0
    private var last: Long? = null

    override fun heartbeat(atMs: Long) {
        last?.let { previous ->
            val gap = atMs - previous
            gaps.addLast(gap)
            sum += gap
            sumOfSquares += gap.toDouble() * gap
            if (gaps.size > windowSize) {                   // forget the oldest gap
                val old = gaps.removeFirst()
                sum -= old
                sumOfSquares -= old.toDouble() * old
            }
        }
        last = atMs
    }

    fun phi(nowMs: Long): Double {
        val l = last ?: return 0.0
        if (gaps.isEmpty()) return 0.0
        val n = gaps.size
        val mean = sum / n
        val variance = max(sumOfSquares / n - mean * mean, 0.0)
        val stdDev = max(sqrt(variance), minStdDevMs)      // the floor: a calm link still gets some slack
        val p = probabilityLater((nowMs - l).toDouble(), mean, stdDev)
        return -log10(p)                                   // phi 1: one in 10; phi 8: one in 100 million
    }

    override fun suspects(nowMs: Long): Boolean = phi(nowMs) > threshold
}
