package sfz.dist.l02

import kotlin.math.abs
import kotlin.math.exp
import kotlin.random.Random

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
