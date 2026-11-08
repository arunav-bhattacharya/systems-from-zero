package sfz.cons.l06

// Lesson cons-06 lab, part 2: a transaction across two ranges, and readers on servers whose clocks
// disagree. A settlement job on one server marks batch k as paid in two places in one transaction:
// the payouts range and the ledger range. Auditors on other servers read both. An audit must see the
// two agree (atomic), and must see every batch whose commit was acknowledged before the audit began
// (no stale reads). The clocks are off by up to epsilon each way, so a timestamp alone can't promise
// the second part. Each Policy pays for that differently.
// Your job: commitTimestamp(), commitWait() and audit(). The rest is provided.

enum class Policy {
    /** Use each server's clock as if it were right: no waiting, no restarts, and stale reads. */
    TRUST_CLOCK,

    /** Spanner: commit at TrueTime's latest, then wait until that timestamp is surely past. */
    COMMIT_WAIT,

    /** CockroachDB: commit at the local clock; a reader that finds a version it can't place restarts above it. */
    RESTART,
}

/** The starting values' timestamp: before any clock in the simulation, even one that runs behind. */
const val BEGINNING = -1_000_000L

/** One audit: what it read from each range, and what it took to get there. */
data class Audit(val payout: Long, val ledger: Long, val restarts: Int, val waitedMs: Long)

data class Stats(
    val settled: Int,
    val audits: Int,
    /** Audits that missed a batch acknowledged before they began. */
    val staleReads: Int,
    /** Audits where the two ranges disagreed. */
    val fracturedReads: Int,
    val restarts: Int,
    val meanWriteMs: Double,
    val meanReadMs: Double,
)

class Cluster(
    val policy: Policy,
    val epsilonMs: Long,
    seed: Long = 1,
    readerCount: Int = 4,
    /** Phase one of two-phase commit: intents written to both ranges, each through its own consensus group. */
    val prepareMs: Long = 4,
    /** The commit record replicated through consensus: after this the transaction is decided. */
    val commitMs: Long = 4,
    /** One read round trip to both ranges (sent in parallel). */
    val rttMs: Long = 2,
    /** The ledger range hears the outcome this much later than the payouts range. */
    val resolveLagMs: Long = 1,
) {
    val sim = Sim(seed)
    val payouts = Range("payouts").apply { load("batch", 0, ts = BEGINNING) }
    val ledger = Range("ledger").apply { load("batch", 0, ts = BEGINNING) }

    /** The settlement job runs here. Its clock is ahead by the full bound: the worst case for readers. */
    val writer = server("settle", epsilonMs)

    /** Auditors with clocks spread across the bound, from epsilon behind to epsilon ahead. */
    val readers = (0 until readerCount).map { i ->
        val offset = if (readerCount == 1) -epsilonMs else -epsilonMs + 2 * epsilonMs * i / (readerCount - 1)
        server("audit-$i", offset)
    }

    // ---------------------------------------------------------------- your part

    /**
     * The commit timestamp for a transaction coordinated by [server]:
     * TRUST_CLOCK and RESTART use the server's clock; COMMIT_WAIT uses the latest time TrueTime allows,
     * so that the true time at the moment of choosing is surely not after it.
     */
    fun commitTimestamp(server: Server): Long {
        TODO("cons-06: the clock, or TrueTime latest for COMMIT_WAIT")
    }

    /**
     * Called after the commit record is replicated and before the client is told. COMMIT_WAIT only:
     * wait (in steps of 1 ms) until TrueTime's earliest is at or past [ts], so [ts] is surely in the
     * past on every server's clock before anyone can learn of the commit. The other policies return at once.
     */
    suspend fun commitWait(server: Server, ts: Long) {
        TODO("cons-06: COMMIT_WAIT only: wait until TrueTime earliest >= ts")
    }

    /**
     * One audit from [server]: read "batch" from [payouts] and [ledger] at one timestamp.
     *
     * - Pick the read timestamp and the top of the uncertainty window. TRUST_CLOCK: the clock, no window
     *   (limit = readTs). COMMIT_WAIT: TrueTime's latest, no window. RESTART: the clock, and the window
     *   reaches 2 x epsilon above it, because the writer's clock may be that far ahead of this one.
     * - Each attempt costs one round trip: sleep [rttMs], then read both ranges.
     * - Either read [Blocked]: sleep 1 ms (add it to waitedMs) and read both again, with no new round trip.
     * - Either read [Uncertain]: restart. Count it, move readTs up to the highest uncertain timestamp
     *   (keep the limit where it was, so restarts must end) and try again with a new round trip.
     * - Both [Value]: return the [Audit].
     */
    suspend fun audit(server: Server): Audit {
        TODO("cons-06: read both ranges at one timestamp; wait on intents, restart on uncertainty")
    }

    // ---------------------------------------------------------------- provided

    private fun server(name: String, offset: Long): Server {
        val clock = NodeClock(sim, offset)
        return Server(name, clock, TrueTime(clock, epsilonMs))
    }

    private class Ack(val batch: Long, val at: Long)

    private val acks = ArrayList<Ack>()
    private val writeMs = ArrayList<Long>()
    private val readMs = ArrayList<Long>()
    private var stale = 0
    private var fractured = 0
    private var restartCount = 0

    /** The settlement transaction for batch [k]: two-phase commit across both ranges. */
    suspend fun settle(k: Long) {
        val start = sim.now
        val ts = commitTimestamp(writer)
        sim.sleep(prepareMs)                                      // phase one: both intents replicated
        payouts.putIntent(k, "batch", k, ts)
        ledger.putIntent(k, "batch", k, ts)
        sim.sleep(commitMs)                                       // the decision is replicated: committed
        commitWait(writer, ts)
        acks += Ack(k, sim.now)                                   // the client is told
        writeMs += sim.now - start
        payouts.resolve(k)                                        // the participants learn the outcome,
        sim.after(resolveLagMs) { ledger.resolve(k) }             // not at the same instant
    }

    /** Runs one audit from [server] and checks it against what had been acknowledged when it began. */
    suspend fun checkedAudit(server: Server): Audit {
        val start = sim.now
        val mustSee = acks.lastOrNull { it.at < start }?.batch ?: 0L
        val a = audit(server)
        readMs += sim.now - start
        restartCount += a.restarts
        if (a.payout != a.ledger) fractured++
        if (minOf(a.payout, a.ledger) < mustSee) stale++
        return a
    }

    /** Runs the settlement job and the auditors for [durationMs] of virtual time. */
    fun run(durationMs: Long = 10_000): Stats {
        sim.launch {
            var k = 1L
            while (sim.now < durationMs) {
                settle(k++)
                sim.sleep(sim.random.nextLong(2, 11))
            }
        }
        for (r in readers) {
            sim.launch {
                sim.sleep(sim.random.nextLong(0, 20))
                while (sim.now < durationMs) {
                    checkedAudit(r)
                    sim.sleep(sim.random.nextLong(0, 20))
                }
            }
        }
        sim.runUntil(durationMs + 1_000)
        return Stats(
            settled = writeMs.size,
            audits = readMs.size,
            staleReads = stale,
            fracturedReads = fractured,
            restarts = restartCount,
            meanWriteMs = writeMs.average(),
            meanReadMs = readMs.average(),
        )
    }
}
