package sfz.dist.l03

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.LongRange
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import java.time.Clock
import java.time.Instant

/** Exercise 1, [DriftingClock]: drift, syncs and the error bound, in virtual time. */
class ClockTest {
    private fun offsetOf(clock: DriftingClock, sim: Sim) = clock.millis() - sim.now

    @Test
    fun `a clock that is never synced keeps its starting offset only if it has no drift`() {
        val sim = Sim()
        val clock = DriftingClock(sim, driftPpm = 0, offsetMs = -250)
        sim.runUntil(sim.now + 86_400_000)
        assertThat(offsetOf(clock, sim)).isEqualTo(-250)
    }

    @Test
    fun `a clock 200 ppm fast gains 17_28 seconds a day when nobody syncs it`() {
        val sim = Sim()
        val clock = DriftingClock(sim, driftPpm = 200)
        sim.runUntil(sim.now + 86_400_000)
        assertThat(offsetOf(clock, sim)).isEqualTo(17_280)
    }

    @Test
    fun `a sync every 30 seconds keeps a 200 ppm clock within 6 ms`() {
        val sim = Sim()
        val clock = DriftingClock(sim, driftPpm = 200)
        val start = sim.now
        var worst = 0L
        // look first, then sync: at 30 s, 60 s... the reading just before each sync is the worst one
        for (t in 0L..3_600_000L step 1_000L) sim.at(start + t) { worst = maxOf(worst, offsetOf(clock, sim)) }
        for (t in 30_000L..3_600_000L step 30_000L) sim.at(start + t) { clock.sync(0) }
        sim.run()
        assertThat(worst).isEqualTo(6)
    }

    @Test
    fun `a sync can move the wall clock backward`() {
        val sim = Sim()
        val clock = DriftingClock(sim, driftPpm = 200)
        sim.runUntil(sim.now + 3_600_000)                      // an hour unsynced: 720 ms ahead
        val before = clock.millis()
        sim.runUntil(sim.now + 1)
        clock.sync(0)                                          // step back to the true time
        val after = clock.millis()
        assertThat(after - before).isEqualTo(-719)              // 1 ms passed; the clock says -719
    }

    @Test
    fun `with a 30-second poll the error bound is a sawtooth from 1 to 7 ms`() {
        val sim = Sim()
        val clock = DriftingClock(sim, driftPpm = 150, maxDriftPpm = 200, boundMs = 1)
        val start = sim.now
        for (t in 30_000L..300_000L step 30_000L) sim.at(start + t) { clock.sync(residualMs = 0, boundMs = 1) }
        val bounds = mutableListOf<Long>()
        for (t in 1L..300_000L step 1_000L) sim.at(start + t - 1) { bounds += clock.errorBoundMs() }
        sim.run()
        assertThat(bounds.min()).isEqualTo(1)
        assertThat(bounds.max()).isEqualTo(7)
    }

    @Test
    fun `bounds is the reading plus and minus the error bound`() {
        val sim = Sim()
        val clock = DriftingClock(sim, driftPpm = 0, offsetMs = 3, boundMs = 5)
        assertThat(clock.bounds()).isEqualTo(TimeInterval(sim.now + 3 - 5, sim.now + 3 + 5))
    }

    @Test
    fun `it is a java_time Clock, so code that takes a Clock can be given a skewed one`() {
        val sim = Sim()
        val skewed: Clock = DriftingClock(sim, offsetMs = -5_000)
        assertThat(Instant.now(skewed)).isEqualTo(Instant.parse("2026-11-07T09:59:55Z"))
    }

    @Property(tries = 300)
    fun `an honest bound always contains the true time`(
        @ForAll @LongRange(min = -200, max = 200) driftPpm: Long,
        @ForAll @LongRange(min = -50, max = 50) offsetMs: Long,
        @ForAll @LongRange(min = 0, max = 10) slackMs: Long,
        @ForAll @LongRange(min = 0, max = 7_200_000) elapsedMs: Long,
    ) {
        val sim = Sim()
        val clock = DriftingClock(sim, driftPpm, offsetMs, maxDriftPpm = 200, boundMs = kotlin.math.abs(offsetMs) + slackMs)
        sim.runUntil(sim.now + elapsedMs)
        val b = clock.bounds()
        assertThat(sim.now).isBetween(b.earliest, b.latest)
    }
}
