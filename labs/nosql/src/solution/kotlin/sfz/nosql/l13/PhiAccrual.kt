package sfz.nosql.l13

import kotlin.math.ln

/**
 * Cassandra's variant of the phi accrual failure detector, for ONE remote endpoint.
 *
 * Every time gossip brings a newer heartbeat of that endpoint, the observer calls [heartbeat]. The
 * detector keeps the gaps between those arrivals (the inter-arrival times) in a window of the last
 * [windowSize]. Asked about the endpoint at some moment, it answers with [phi], a suspicion level
 * that grows the longer it has heard nothing, measured against the usual gap.
 *
 * Cassandra assumes the gaps are exponentially distributed with the window's mean. The chance of a
 * silence at least t long is then e^(-t / mean), and phi is minus its base-10 logarithm:
 * `phi = (t / mean) / ln 10`. Phi 1 means "a silence this long happens 1 time in 10", phi 8 "1 time in
 * 100 million". Cassandra marks the endpoint down when phi passes `phi_convict_threshold`, 8 by default.
 */
class PhiAccrualDetector(
    val windowSize: Int = 1000,
    /** Gaps longer than this are not recorded, so one long outage doesn't teach the detector to be patient. */
    val maxIntervalMillis: Long = 2_000,
    /** The gap recorded with the very first heartbeat, before there is any history. */
    val initialIntervalMillis: Long = 2_000,
) {
    /** The recorded gaps, oldest first. */
    private val intervals = ArrayDeque<Long>()

    /** When the last heartbeat arrived, or null before the first. */
    var lastHeartbeatMillis: Long? = null
        private set

    /** The recorded gaps, oldest first. Given. */
    val window: List<Long> get() = intervals.toList()

    /** The mean gap in the window, in milliseconds. Given. */
    val meanMillis: Double get() = intervals.average()

    /**
     * Records a heartbeat that arrived at [atMillis].
     * - The first heartbeat records [initialIntervalMillis] as the gap.
     * - Later ones record `atMillis - lastHeartbeatMillis`, but only if it is at most [maxIntervalMillis].
     * - Keep at most [windowSize] gaps: drop the oldest.
     * - Either way, this heartbeat becomes the last one.
     */
    fun heartbeat(atMillis: Long) {
        val last = lastHeartbeatMillis
        val gap = if (last == null) initialIntervalMillis else atMillis - last
        // a gap after an outage says nothing about the normal rhythm: leave it out
        if (last == null || gap <= maxIntervalMillis) {
            intervals.addLast(gap)
            if (intervals.size > windowSize) intervals.removeFirst()
        }
        lastHeartbeatMillis = atMillis
    }

    /**
     * The suspicion level at [nowMillis]: the silence since the last heartbeat divided by the mean gap,
     * times [PHI_FACTOR] (1 / ln 10). Zero before the first heartbeat.
     */
    fun phi(nowMillis: Long): Double {
        val last = lastHeartbeatMillis ?: return 0.0
        return PHI_FACTOR * (nowMillis - last) / meanMillis
    }

    /** What the gossiper's status check asks once a second: is phi still at or under the threshold? Given. */
    fun isAvailable(nowMillis: Long, threshold: Double = DEFAULT_THRESHOLD): Boolean = phi(nowMillis) <= threshold

    companion object {
        /** 1 / ln 10, about 0.434: turns t / mean into minus the base-10 log of e^(-t / mean). */
        val PHI_FACTOR = 1.0 / ln(10.0)

        /** `phi_convict_threshold` in cassandra.yaml (commented out, so the default applies): 8. */
        const val DEFAULT_THRESHOLD = 8.0
    }
}
