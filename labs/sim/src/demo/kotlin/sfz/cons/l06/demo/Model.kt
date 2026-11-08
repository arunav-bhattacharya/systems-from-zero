package sfz.cons.l06.demo

import java.util.PriorityQueue
import kotlin.coroutines.Continuation
import kotlin.coroutines.EmptyCoroutineContext
import kotlin.coroutines.resume
import kotlin.coroutines.startCoroutine
import kotlin.coroutines.suspendCoroutine
import kotlin.random.Random

// A copy of the cons-06 lab's reference solution, for the demo (the demo can't see src/solution),
// with a timeline printed by Cluster.trace. Read the lab files, not this one, to learn the model.

/**
 * Virtual time for lesson cons-06 (given). Nothing here sleeps or starts a thread. [launch] runs a
 * process written as straight-line code; when it calls [sleep], it stops until the virtual clock gets
 * there. [runUntil] takes the scheduled events in time order and moves [now] from one to the next, so
 * ten simulated seconds take a few milliseconds and the same seed always gives the same run. Times are
 * milliseconds. Two events at the same millisecond run in the order they were scheduled.
 */
class Sim(seed: Long = 1) {
    val random = Random(seed)

    var now: Long = 0
        private set

    private class Event(val at: Long, val seq: Long, val action: () -> Unit)

    private var seq = 0L
    private val queue = PriorityQueue(compareBy<Event>({ it.at }, { it.seq }))

    /** Runs [action] at [time]. */
    fun at(time: Long, action: () -> Unit) {
        require(time >= now) { "time $time is in the past (now $now)" }
        queue += Event(time, seq++, action)
    }

    /** Runs [action] [delayMs] from now. */
    fun after(delayMs: Long, action: () -> Unit) = at(now + delayMs, action)

    /** Starts a process now. It runs until its first [sleep], and carries on from there later. */
    fun launch(process: suspend () -> Unit) {
        process.startCoroutine(Continuation(EmptyCoroutineContext) { it.getOrThrow() })
    }

    /** Stops the calling process for [ms] of virtual time. */
    suspend fun sleep(ms: Long) {
        require(ms >= 0) { "can't sleep $ms ms" }
        suspendCoroutine { c -> after(ms) { c.resume(Unit) } }
    }

    /** Runs every event scheduled at or before [time], then sets the clock to [time]. */
    fun runUntil(time: Long) {
        while (queue.isNotEmpty() && queue.peek().at <= time) {
            val e = queue.poll()
            now = e.at
            e.action()
        }
        if (time > now) now = time
    }
}

/**
 * One server's clock (given): the true time of the simulation plus an offset the server doesn't know.
 * The offset stays fixed for the whole run, so the clock never jumps; it is just wrong by [offsetMs].
 */
class NodeClock(private val sim: Sim, val offsetMs: Long) {
    fun now(): Long = sim.now + offsetMs
}

/**
 * A TrueTime-style clock (given): the server doesn't know its offset, but it does know a bound,
 * [epsilonMs], on how wrong it can be. So instead of one number it reports an interval that surely
 * contains the true time: [earliest] to [latest]. Every server in a cluster has the same bound, so two
 * servers' clocks can differ by up to 2 x epsilon.
 */
class TrueTime(private val clock: NodeClock, val epsilonMs: Long) {
    init {
        require(kotlin.math.abs(clock.offsetMs) <= epsilonMs) { "offset ${clock.offsetMs} is outside the bound $epsilonMs" }
    }

    fun earliest(): Long = clock.now() - epsilonMs
    fun latest(): Long = clock.now() + epsilonMs
}

/** A server: a name, its clock and its TrueTime view of that clock. */
class Server(val name: String, val clock: NodeClock, val tt: TrueTime)

/** One version of a key. An intent has [committed] false and belongs to transaction [txn]. */
data class Version(val ts: Long, val value: Long, val txn: Long?, val committed: Boolean)

/** What a read at a timestamp finds. */
sealed interface ReadResult

/** The value to return, and the timestamp of the version it came from. */
data class Value(val value: Long, val ts: Long) : ReadResult

/** A committed version the reader can't place: it may have happened before the read began, or after. */
data class Uncertain(val ts: Long) : ReadResult

/** An intent the reader can't skip: wait until transaction [txn] commits or aborts, then read again. */
data class Blocked(val txn: Long) : ReadResult

class Range(val name: String) {
    private val versions = HashMap<String, MutableList<Version>>()

    // ---------------------------------------------------------------- your part

    /**
     * Reads [key] at [readTs]. [limit] is the top of the reader's uncertainty window: a committed
     * version with a timestamp in (readTs, limit] may have been written before the read began, so the
     * reader can't simply ignore it. Without uncertainty, limit == readTs. In this order:
     *
     * 1. An intent with a timestamp at or below [limit] returns [Blocked]: once it commits, the reader
     *    would have to see it (or would not know whether to), so it must wait for the outcome.
     * 2. A committed version with readTs < ts <= limit returns [Uncertain] with the highest such ts.
     * 3. Otherwise return the newest committed version with ts <= readTs as a [Value]. Every key has
     *    one, because [load] stores a starting value below any timestamp a read will use.
     *
     * Versions above [limit] are in the future of this read whatever the clocks say: ignore them.
     */
    fun read(key: String, readTs: Long, limit: Long): ReadResult {
        val all = versionsOf(key)
        all.firstOrNull { !it.committed && it.ts <= limit }?.let { return Blocked(it.txn!!) }   // may land below us
        all.filter { it.committed && it.ts > readTs && it.ts <= limit }                          // can't tell past from future
            .maxOfOrNull { it.ts }?.let { return Uncertain(it) }
        val v = all.filter { it.committed && it.ts <= readTs }.maxBy { it.ts }                   // the snapshot at readTs
        return Value(v.value, v.ts)
    }

    // ---------------------------------------------------------------- provided

    /** Stores the starting value of [key], committed at timestamp [ts] (by default 0). */
    fun load(key: String, value: Long, ts: Long = 0) {
        versions.getOrPut(key) { ArrayList() } += Version(ts, value, txn = null, committed = true)
    }

    /** Writes a provisional version for transaction [txn] at timestamp [ts]. */
    fun putIntent(txn: Long, key: String, value: Long, ts: Long) {
        versions.getOrPut(key) { ArrayList() } += Version(ts, value, txn, committed = false)
    }

    /** Transaction [txn] committed: its intents become ordinary committed versions at the same timestamps. */
    fun resolve(txn: Long) {
        for (list in versions.values) {
            list.replaceAll { if (it.txn == txn && !it.committed) it.copy(committed = true) else it }
        }
    }

    fun versionsOf(key: String): List<Version> = versions[key] ?: emptyList()
}

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

    /** Prints a line of the timeline when set. */
    var trace: ((String) -> Unit)? = null
    private fun log(who: String, what: String) = trace?.invoke("t=%5d  %-8s %s".format(sim.now, who, what))

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
    fun commitTimestamp(server: Server): Long = when (policy) {
        Policy.COMMIT_WAIT -> server.tt.latest()                 // no real time "now" can be later than this
        else -> server.clock.now()
    }

    /**
     * Called after the commit record is replicated and before the client is told. COMMIT_WAIT only:
     * wait (in steps of 1 ms) until TrueTime's earliest is at or past [ts], so [ts] is surely in the
     * past on every server's clock before anyone can learn of the commit. The other policies return at once.
     */
    suspend fun commitWait(server: Server, ts: Long) {
        if (policy != Policy.COMMIT_WAIT) return
        while (server.tt.earliest() < ts) sim.sleep(1)           // overlaps with prepare and commit: only the rest is waited
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
        var readTs = if (policy == Policy.COMMIT_WAIT) server.tt.latest() else server.clock.now()
        val limit = if (policy == Policy.RESTART) readTs + 2 * epsilonMs else readTs
        log(server.name, "audit starts: read timestamp $readTs (clock ${server.clock.now()})" +
            if (limit > readTs) ", uncertain up to $limit" else "")
        var restarts = 0
        var waited = 0L
        sim.sleep(rttMs)
        while (true) {
            val p = payouts.read("batch", readTs, limit)
            val l = ledger.read("batch", readTs, limit)
            if (p is Blocked || l is Blocked) {                   // a transaction is mid-commit: wait it out
                if (waited == 0L) log(server.name, "meets an intent at or below its timestamp: waits")
                waited++
                sim.sleep(1)
                continue
            }
            if (p is Uncertain || l is Uncertain) {               // a version we can't place: read above it
                restarts++
                readTs = maxOf((p as? Uncertain)?.ts ?: readTs, (l as? Uncertain)?.ts ?: readTs)
                log(server.name, "finds a version it can't place: restarts at $readTs")
                sim.sleep(rttMs)
                continue
            }
            log(server.name, "reads payouts = ${(p as Value).value}, ledger = ${(l as Value).value}")
            return Audit(p.value, (l as Value).value, restarts, waited)
        }
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
        log(writer.name, "batch $k: commit timestamp $ts (its clock reads ${writer.clock.now()})")
        sim.sleep(prepareMs)                                      // phase one: both intents replicated
        payouts.putIntent(k, "batch", k, ts)
        ledger.putIntent(k, "batch", k, ts)
        log(writer.name, "intents for batch $k written to payouts and ledger at $ts")
        sim.sleep(commitMs)                                       // the decision is replicated: committed
        log(writer.name, "commit record replicated: batch $k is decided")
        val waitFrom = sim.now
        commitWait(writer, ts)
        if (sim.now > waitFrom) log(writer.name, "commit wait over: TrueTime earliest is now ${writer.tt.earliest()}, so $ts has surely passed")
        acks += Ack(k, sim.now)                                   // the client is told
        log(writer.name, "client told: batch $k is paid (${sim.now - start} ms)")
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
