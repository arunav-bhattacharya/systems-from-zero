package sfz.dist.l02

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test

/** Exercises 1 and 2 on heartbeats written out by hand. Times are milliseconds. */
class DetectorTest {
    private fun regular(d: FailureDetector, count: Int, gapMs: Long = 1_000, start: Long = 0): Long {
        var t = start
        repeat(count) { d.heartbeat(t); t += gapMs }
        return t - gapMs                                         // the last heartbeat
    }

    /** The first millisecond after [last] at which [d] suspects, scanning up to [limit] ms of silence. */
    private fun silenceToSuspect(d: FailureDetector, last: Long, limit: Long = 20_000): Long? =
        (0..limit).firstOrNull { d.suspects(last + it) }

    @Test
    fun `a fixed timeout suspects only once the silence is longer than the timeout`() {
        val d = FixedTimeoutDetector(1_500)
        d.heartbeat(10_000)
        assertThat(d.suspects(11_000)).isFalse()
        assertThat(d.suspects(11_500)).isFalse()
        assertThat(d.suspects(11_501)).isTrue()
        d.heartbeat(11_600)                                      // a late heartbeat clears the suspicion
        assertThat(d.suspects(11_700)).isFalse()
    }

    @Test
    fun `no detector suspects a node it has never heard from`() {
        assertThat(FixedTimeoutDetector(100).suspects(1_000_000)).isFalse()
        assertThat(PhiAccrualDetector().suspects(1_000_000)).isFalse()
        val one = PhiAccrualDetector().apply { heartbeat(0) }    // one heartbeat is no gap yet
        assertThat(one.phi(1_000_000)).isEqualTo(0.0)
    }

    @Test
    fun `phi is about 0_3 when the silence equals the mean gap`() {
        val d = PhiAccrualDetector()
        val last = regular(d, 11)
        // a gap as long as the mean happens half the time: -log10(0.5)
        assertThat(d.phi(last + 1_000)).isCloseTo(0.30103, within(1e-4))
    }

    @Test
    fun `phi follows the bell curve past the mean`() {
        val d = PhiAccrualDetector()
        val last = regular(d, 11)                                // every gap 1,000: the 100 ms floor applies
        assertThat(d.phi(last + 1_500)).isCloseTo(6.5426, within(1e-3))     // 5 standard deviations late
        assertThat(d.phi(last + 1_600)).isCloseTo(9.0058, within(1e-3))     // 6 standard deviations late
        val phis = (1_000..2_000 step 50).map { d.phi(last + it) }
        assertThat(phis).isSorted()
    }

    @Test
    fun `phi crosses 8 about 5_6 standard deviations past the mean`() {
        val d = PhiAccrualDetector(threshold = 8.0)
        val last = regular(d, 11)
        assertThat(silenceToSuspect(d, last)).isBetween(1_555L, 1_565L)
    }

    @Test
    fun `phi gives a jittery link more time before it suspects`() {
        val d = PhiAccrualDetector(threshold = 8.0)
        var last = 0L
        d.heartbeat(last)
        repeat(100) { i ->
            last += if (i % 2 == 0) 800 else 1_200                // gaps 800, 1,200, 800...: mean 1,000, deviation 200
            d.heartbeat(last)
        }
        assertThat(silenceToSuspect(d, last)).isBetween(2_115L, 2_130L)
    }

    @Test
    fun `phi forgets gaps older than its window`() {
        val d = PhiAccrualDetector(windowSize = 4)
        val last = regular(d, 100, 1_000)
        repeat(4) { i -> d.heartbeat(last + (i + 1) * 3_000L) }   // four gaps of 3,000 push the old ones out
        assertThat(d.phi(last + 4 * 3_000L + 3_000)).isCloseTo(0.30103, within(1e-4))
    }
}
