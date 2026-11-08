package sfz.dist.l03

import java.time.Clock
import java.time.Instant
import java.time.ZoneId
import java.time.ZoneOffset
import kotlin.math.abs

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
        TODO("Exercise 1a: true time + offset at the last sync + drift since")
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
        TODO("Exercise 1b: bound at the last sync + worst drift since, rounded up")
    }

    /**
     * Exercise 1c. The reading as an interval, the way TrueTime and ClockBound return it:
     * [millis] minus and plus [errorBoundMs].
     */
    fun bounds(): TimeInterval {
        TODO("Exercise 1c: [millis - bound, millis + bound]")
    }

    override fun instant(): Instant = Instant.ofEpochMilli(millis())
    override fun getZone(): ZoneId = ZoneOffset.UTC
    override fun withZone(zone: ZoneId): Clock = throw UnsupportedOperationException("this clock is UTC only")
}
