package sfz.dist.l03.demo

import java.time.Clock
import java.time.Instant
import java.time.ZoneId
import java.time.ZoneOffset
import java.util.PriorityQueue
import kotlin.math.abs
import kotlin.random.Random

// A copy of the lab's reference model (labs/sim/src/solution/kotlin/sfz/dist/l03), so the demos run
// without your exercises. Read the lab's files for the comments on each part.

/**
 * Virtual time for lesson dist-03 (given). Nothing here sleeps or starts a thread. [run] takes the
 * scheduled events in time order and moves [now] from one to the next, so a simulated hour takes a
 * few milliseconds and the same seed always gives the same run.
 *
 * [now] is the true time, in epoch milliseconds: what a perfect clock would read. It starts at
 * [START], 10:00:00.000 UTC on 7 November 2026. No node can read it; nodes read their own
 * [DriftingClock]s.
 *
 * Every random choice in a simulation comes from [random], which is seeded once. Two events at the
 * same millisecond run in the order they were scheduled.
 */
class Sim(seed: Long = 1) {
    companion object {
        /** 2026-11-07T10:00:00Z */
        const val START = 1_794_045_600_000L
    }

    val random = Random(seed)

    var now: Long = START
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

    /** Runs every event scheduled at or before [time], then sets the clock to [time]. */
    fun runUntil(time: Long) {
        while (queue.isNotEmpty() && queue.peek().at <= time) step()
        if (time > now) now = time
    }

    /** Runs events until none are left. */
    fun run() {
        while (queue.isNotEmpty()) step()
    }

    private fun step() {
        val event = queue.poll()
        now = event.at
        event.action()
    }
}

/** A clock reading that admits its error: the true time is somewhere from [earliest] to [latest]. */
data class TimeInterval(val earliest: Long, val latest: Long)

/**
 * Lesson dist-03: one node's time-of-day clock, in virtual time. It is a [java.time.Clock], so code
 * under test takes it wherever production code takes `Clock.systemUTC()`. That is how you give one
 * service a skewed clock: containers on one host share the kernel's wall clock, so you can't skew a
 * container, but you can hand its code a different [Clock].
 *
 * The true time is [Sim.now]. The clock's oscillator runs [driftPpm] parts per million fast
 * (negative: slow), and right after the last sync the clock was off by an amount the node doesn't
 * know, inside a bound it does know.
 *
 * Three exercises: [millis], [errorBoundMs] and [bounds].
 */
class DriftingClock(
    private val sim: Sim,
    /** The real rate error: +200 gains 200 microseconds every second. The node can't see this number. */
    val driftPpm: Long = 0,
    /** How far off the clock starts, in ms (negative: behind). The node can't see this either. */
    offsetMs: Long = 0,
    /** The worst drift the node assumes when it computes its bound (Spanner assumed 200 ppm). */
    val maxDriftPpm: Long = 200,
    /** The error bound the node believes right after start: by default, honest. */
    boundMs: Long = abs(offsetMs),
) : Clock() {
    private var syncedAt = sim.now          // the true time of the last sync
    private var offsetAtSync = offsetMs     // clock minus true time, right after the last sync
    private var boundAtSync = boundMs       // what the node believes about that offset

    /**
     * Exercise 1a. The clock's reading in epoch ms: the true time, plus the offset it had at the last
     * sync, plus what the drift has added since: `elapsed * driftPpm / 1_000_000`, with Long division.
     */
    override fun millis(): Long {
        val elapsed = sim.now - syncedAt
        return sim.now + offsetAtSync + elapsed * driftPpm / 1_000_000
    }

    /**
     * Given. A sync with a time server (NTP, PTP) steps the clock to within [residualMs] of the true
     * time, and the node now believes its error is at most [boundMs]. A step can move the clock
     * backward: chrony and ntpd usually slew (run the clock a little faster or slower) instead, and
     * step only for large offsets.
     */
    fun sync(residualMs: Long = 0, boundMs: Long = abs(residualMs)) {
        syncedAt = sim.now
        offsetAtSync = residualMs
        boundAtSync = boundMs
    }

    /**
     * Exercise 1b. How far off the node believes it can be: the bound at the last sync, plus the
     * worst drift since, `elapsed * maxDriftPpm / 1_000_000` rounded up (a bound must never
     * undershoot; `Math.ceilDiv` does it).
     */
    fun errorBoundMs(): Long {
        val elapsed = sim.now - syncedAt
        return boundAtSync + Math.ceilDiv(elapsed * maxDriftPpm, 1_000_000L)   // grows until the next sync
    }

    /**
     * Exercise 1c. The reading as an interval, the way TrueTime and ClockBound return it:
     * [millis] minus and plus [errorBoundMs].
     */
    fun bounds(): TimeInterval {
        val now = millis()
        val e = errorBoundMs()
        return TimeInterval(now - e, now + e)
    }

    override fun instant(): Instant = Instant.ofEpochMilli(millis())
    override fun getZone(): ZoneId = ZoneOffset.UTC
    override fun withZone(zone: ZoneId): Clock = throw UnsupportedOperationException("this clock is UTC only")
}

/**
 * Lesson dist-03: a register that settles conflicts by timestamp, the way Cassandra settles one cell,
 * and writers that stamp their writes with their own clocks.
 *
 * Two exercises: [LwwRegister.apply] and [Writer.writeWithCommitWait].
 */

/** One write as the store receives it: the value, the timestamp its writer chose, and who wrote it. */
data class Write(val value: String, val timestampMs: Long, val writer: String)

class LwwRegister {
    var current: Write? = null
        private set

    /**
     * Exercise 2. Last write wins: keep [write] if there is no current write, or its timestamp is
     * higher, or the timestamps are equal and its writer name is larger (a fixed tie-break, so every
     * replica picks the same one). Returns whether [write] became current.
     */
    fun apply(write: Write): Boolean {
        val c = current
        val newer = c == null ||
            write.timestampMs > c.timestampMs ||
            (write.timestampMs == c.timestampMs && write.writer > c.writer)
        if (newer) current = write                       // otherwise the write is dropped, silently
        return newer
    }
}

/**
 * Given. A store with one [LwwRegister], [networkMs] one way from every writer. It acknowledges every
 * write it receives, kept or dropped, as a Cassandra replica does: the timestamp decided, not the
 * order of arrival, and nobody was told.
 */
class Store(private val sim: Sim, val networkMs: Long = 1) {
    val register = LwwRegister()

    /** Writes the store acknowledged but dropped because an existing write had a higher timestamp. */
    var dropped = 0
        private set

    fun write(w: Write, ack: () -> Unit) {
        sim.after(networkMs) {
            if (!register.apply(w)) dropped++
            sim.after(networkMs) { ack() }
        }
    }

    fun read(reply: (Write?) -> Unit) {
        sim.after(networkMs) {
            val c = register.current
            sim.after(networkMs) { reply(c) }
        }
    }
}

/** A service instance with its own clock, writing to the [store]. */
class Writer(val name: String, val clock: DriftingClock, private val sim: Sim, private val store: Store) {

    /** Given. Plain last-write-wins: stamp the write with this node's clock reading and send it. */
    fun write(value: String, done: () -> Unit) {
        store.write(Write(value, clock.millis(), name)) { done() }
    }

    /**
     * Exercise 3. Commit wait, as Spanner does it with TrueTime:
     *  - stamp the write with `clock.bounds().latest`, a time that can't be in the past yet;
     *  - send it;
     *  - once the store has acknowledged, check the clock every 1 ms of virtual time and call [done]
     *    when `clock.bounds().earliest` is greater than the stamp: from then on, that time is surely
     *    in the past on every honest clock, so any later write anywhere gets a larger stamp.
     * [done] receives the ms waited after the acknowledgement.
     */
    fun writeWithCommitWait(value: String, done: (waitedMs: Long) -> Unit) {
        val stamp = clock.bounds().latest                  // no honest clock reads past this yet
        store.write(Write(value, stamp, name)) {
            val ackedAt = sim.now
            fun check() {
                if (clock.bounds().earliest > stamp) done(sim.now - ackedAt)   // the stamp is in everyone's past
                else sim.after(1) { check() }
            }
            check()
        }
    }
}

/** What a [causalChain] saw. */
data class ChainResult(
    /** Writes the store acknowledged. */
    val acknowledged: Int,
    /** Acknowledged writes that a read straight after did not return: the register kept an older value. */
    val lost: List<String>,
    /** For commit-wait runs, how long each write waited after its acknowledgement. */
    val waitsMs: List<Long>,
)

/**
 * Given. [rounds] writes in a causal chain: in round i, `writers[i % writers.size]` reads the register,
 * then writes "v<i>", then reads again to check it. The next round starts after a think time drawn
 * from 0 to [maxThinkMs]. Every write is causally after the one before it, because its writer read it
 * first, so a correct store must end each round showing the newest value.
 */
fun causalChain(sim: Sim, store: Store, writers: List<Writer>, rounds: Int, commitWait: Boolean, maxThinkMs: Long = 0): ChainResult {
    var acknowledged = 0
    val lost = mutableListOf<String>()
    val waits = mutableListOf<Long>()
    fun round(i: Int) {
        if (i == rounds) return
        val w = writers[i % writers.size]
        val value = "v$i"
        fun check() {
            acknowledged++
            store.read { seen ->
                if (seen?.value != value) lost += value       // OK was said, the value isn't there
                sim.after(sim.random.nextLong(maxThinkMs + 1)) { round(i + 1) }
            }
        }
        store.read { _ ->                                      // read first: this write follows the last one
            if (commitWait) w.writeWithCommitWait(value) { waited -> waits += waited; check() }
            else w.write(value) { check() }
        }
    }
    sim.at(sim.now) { round(0) }
    sim.run()
    return ChainResult(acknowledged, lost, waits)
}
