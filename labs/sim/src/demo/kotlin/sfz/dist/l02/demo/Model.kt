package sfz.dist.l02.demo

import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.log10
import kotlin.math.max
import kotlin.math.pow
import kotlin.math.sqrt
import kotlin.random.Random

// A copy of the lab's reference model (labs/sim/src/solution/kotlin/sfz/dist/l02), so the demos run
// without your exercises. Read the lab's files for the comments on each part.

/**
 * Lesson dist-02 (given): heartbeats on a simulated link, in virtual time, and a referee that scores
 * a [FailureDetector] against the truth. Read it, but you don't need to change it.
 *
 * The monitored node sends a heartbeat every [Scenario.intervalMs]. Each one reaches the monitor after
 * a delay drawn from its [Link]. The node can freeze ([Scenario.pauses]: a long GC, a VM that was
 * descheduled) or die ([Scenario.crashAtMs]). The detector sees only arrival times.
 */

/** A path from the node to the monitor: each heartbeat takes [baseMs] plus a uniform 0 to [jitterMs]. */
data class Link(val name: String, val baseMs: Long, val jitterMs: Long)

/** Two machines in one rack: 1 to 5 ms. */
val CALM = Link("calm LAN", baseMs = 1, jitterMs = 4)

/** A busy path between regions: 30 to 830 ms. */
val JITTERY = Link("jittery WAN", baseMs = 30, jitterMs = 800)

data class Scenario(
    val link: Link,
    /** The run lasts this long. */
    val endMs: Long = 320_000,
    /** The node sends a heartbeat at 0, intervalMs, 2 x intervalMs... */
    val intervalMs: Long = 1_000,
    /** The node is frozen during each range: it sends nothing, then sends one heartbeat as it wakes. */
    val pauses: List<LongRange> = emptyList(),
    /** The node dies here and never sends again. Null: it lives to the end. */
    val crashAtMs: Long? = 300_001,
    val seed: Long = 1,
)

/** When each heartbeat reached the monitor, sorted. */
fun arrivals(s: Scenario): List<Long> {
    val random = Random(s.seed)
    fun delay() = s.link.baseMs + random.nextLong(s.link.jitterMs + 1)
    val sends = mutableListOf<Long>()
    var t = 0L
    while (t < s.endMs && (s.crashAtMs == null || t < s.crashAtMs)) {
        if (s.pauses.none { t in it }) sends += t
        t += s.intervalMs
    }
    for (p in s.pauses) if (s.crashAtMs == null || p.last < s.crashAtMs) sends += p.last + 1   // wakes and sends at once
    return sends.sorted().map { it + delay() }.sorted()
}

/** How a detector did over one [Scenario]. */
data class Score(
    /** Times the detector started suspecting a node that was alive (paused counts as alive). */
    val falseAlarms: Int,
    /** Total time it suspected a live node. */
    val suspectedWhileAliveMs: Long,
    /** From the crash to the first check that suspected the node; null if it never did. */
    val detectionMs: Long?,
)

/** Plays [s] to [detector], asking [FailureDetector.suspects] every [checkEveryMs], and scores the answers. */
fun score(detector: FailureDetector, s: Scenario, checkEveryMs: Long = 10): Score {
    val beats = arrivals(s)
    var next = 0
    var falseAlarms = 0
    var suspectedAlive = 0L
    var detection: Long? = null
    var before = false
    var t = 0L
    while (t <= s.endMs) {
        while (next < beats.size && beats[next] <= t) detector.heartbeat(beats[next++])
        val suspect = detector.suspects(t)
        val alive = s.crashAtMs == null || t < s.crashAtMs
        if (alive && suspect) {
            if (!before) falseAlarms++
            suspectedAlive += checkEveryMs
        }
        if (!alive && suspect && detection == null) detection = t - s.crashAtMs!!
        before = suspect
        t += checkEveryMs
    }
    return Score(falseAlarms, suspectedAlive, detection)
}

/**
 * The chance that a heartbeat gap drawn from a normal distribution with [meanMs] and [stdDevMs] is
 * longer than [elapsedMs]: the area under the bell curve to the right of [elapsedMs].
 */
fun probabilityLater(elapsedMs: Double, meanMs: Double, stdDevMs: Double): Double =
    0.5 * erfc((elapsedMs - meanMs) / (stdDevMs * Math.sqrt(2.0)))

/** The complementary error function, to a relative error below 1.2e-7 (Numerical Recipes' erfcc). */
fun erfc(x: Double): Double {
    val z = abs(x)
    val t = 1.0 / (1.0 + 0.5 * z)
    val r = t * exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 + t * (-0.18628806 +
        t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (-0.82215223 + t * 0.17087277)))))))))
    return if (x >= 0) r else 2.0 - r
}

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

/**
 * Lesson dist-02, exercise 3: why redundancy makes a gray failure hit more requests, not fewer.
 *
 * A request fans out to [fanOut] servers. Each sub-request crosses one of [paths] equal paths (core
 * switches), picked at random. One path is gray: it drops or delays some packets but still looks
 * healthy. Returns the chance that the request touches that path at least once:
 * 1 - ((paths - 1) / paths) ^ fanOut.
 */
fun chanceToTouchGray(paths: Int, fanOut: Int): Double {
    require(paths >= 1 && fanOut >= 0) { "paths >= 1, fanOut >= 0" }
    val missOne = (paths - 1).toDouble() / paths           // one sub-request avoids the gray path
    return 1.0 - missOne.pow(fanOut)                       // all of them avoid it, or not
}
