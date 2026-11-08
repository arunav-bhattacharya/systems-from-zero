package sfz.dist.l02

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
    override fun heartbeat(atMs: Long) {
        TODO("Exercise 1: remember when the last heartbeat arrived")
    }

    override fun suspects(nowMs: Long): Boolean {
        TODO("Exercise 1: suspect once the silence is longer than timeoutMs")
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
    override fun heartbeat(atMs: Long) {
        TODO("Exercise 2: record the gap since the previous heartbeat, keeping the last windowSize gaps")
    }

    fun phi(nowMs: Long): Double {
        TODO("Exercise 2: -log10(probabilityLater(silence, mean gap, standard deviation))")
    }

    override fun suspects(nowMs: Long): Boolean = phi(nowMs) > threshold
}
