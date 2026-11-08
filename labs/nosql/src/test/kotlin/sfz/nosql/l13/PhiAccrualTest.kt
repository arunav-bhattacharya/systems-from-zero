package sfz.nosql.l13

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test
import kotlin.math.ln

class PhiAccrualTest {
    /** A detector that has heard [count] heartbeats, [gapMillis] apart, the last one at [lastAt]. */
    private fun steady(gapMillis: Long, count: Int, lastAt: Long = 100_000): PhiAccrualDetector {
        val d = PhiAccrualDetector()
        for (i in count - 1 downTo 0) d.heartbeat(lastAt - i * gapMillis)
        return d
    }

    @Test
    fun `the first heartbeat seeds the window with the initial interval`() {
        val d = PhiAccrualDetector()
        assertThat(d.phi(5_000)).isEqualTo(0.0) // nothing heard yet: no opinion
        d.heartbeat(10_000)
        assertThat(d.window).containsExactly(2_000L)
        d.heartbeat(11_000)
        assertThat(d.window).containsExactly(2_000L, 1_000L)
        assertThat(d.lastHeartbeatMillis).isEqualTo(11_000L)
    }

    @Test
    fun `phi grows in a straight line with the silence, measured in mean gaps`() {
        val d = steady(gapMillis = 1_000, count = 1_001) // the initial 2,000 fell out of the window
        assertThat(d.meanMillis).isCloseTo(1_000.0, within(1e-9))
        // one mean gap of silence: phi = 1 / ln 10, about 0.43
        assertThat(d.phi(101_000)).isCloseTo(1 / ln(10.0), within(1e-9))
        // twice the silence, twice the phi
        assertThat(d.phi(102_000)).isCloseTo(2 * d.phi(101_000), within(1e-9))
    }

    @Test
    fun `with heartbeats a second apart, phi passes 8 after about 18 seconds of silence`() {
        val d = steady(gapMillis = 1_000, count = 1_001)
        assertThat(d.isAvailable(100_000 + 18_000)).isTrue()   // phi 7.8
        assertThat(d.isAvailable(100_000 + 18_500)).isFalse()  // phi 8.03
        // the exact point: 8 * ln 10 mean gaps
        assertThat(d.phi(100_000 + Math.round(8 * ln(10.0) * 1_000))).isCloseTo(8.0, within(0.001))
    }

    @Test
    fun `a faster rhythm convicts sooner, because the threshold counts mean gaps, not seconds`() {
        val fast = steady(gapMillis = 500, count = 1_001)
        assertThat(fast.isAvailable(100_000 + 9_000)).isTrue()
        assertThat(fast.isAvailable(100_000 + 9_500)).isFalse() // half the gap, half the patience
    }

    @Test
    fun `a gap longer than the max interval is not learned`() {
        val d = steady(gapMillis = 1_000, count = 101)
        val mean = d.meanMillis
        d.heartbeat(100_000 + 30_000) // back after a 30-second outage
        assertThat(d.meanMillis).isEqualTo(mean)          // the outage didn't make the detector more patient
        assertThat(d.lastHeartbeatMillis).isEqualTo(130_000L) // but the clock restarts from this heartbeat
        assertThat(d.phi(130_000)).isEqualTo(0.0)
    }

    @Test
    fun `the window keeps only the most recent gaps`() {
        val d = PhiAccrualDetector(windowSize = 10)
        var t = 0L
        repeat(50) { t += 1_500; d.heartbeat(t) }  // a slow rhythm first
        repeat(10) { t += 500; d.heartbeat(t) }    // then a fast one
        assertThat(d.window).hasSize(10).containsOnly(500L)
        assertThat(d.meanMillis).isEqualTo(500.0)
    }
}
