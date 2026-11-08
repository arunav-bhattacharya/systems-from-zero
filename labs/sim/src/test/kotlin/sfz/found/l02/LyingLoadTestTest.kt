package sfz.found.l02

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.data.Percentage
import org.junit.jupiter.api.Test

/**
 * 1,000 requests a second for 30 seconds of virtual time. In the paused runs the server freezes
 * for 1.4 seconds, 10 seconds in.
 */
class LyingLoadTestTest {
    private val rate = 1_000
    private val duration = 30_000_000L
    private fun quiet() = PausingServer(seed = 1)
    private fun paused() = PausingServer(pauseAt = 10_000_000L, pauseMicros = 1_400_000L, seed = 1)

    @Test
    fun `the open model sends every request on schedule`() {
        val h = openLoop(quiet(), rate, duration)
        assertThat(h.count).isEqualTo(30_000)
    }

    @Test
    fun `on a quiet server both models agree`() {
        val open = openLoop(quiet(), rate, duration)
        val closed = closedLoop(quiet(), rate, connections = 10, durationMicros = duration).fromActualSend
        assertThat(open.quantile(0.99)).isLessThan(10_000)
        assertThat(open.quantile(0.99)).isCloseTo(closed.quantile(0.99), Percentage.withPercentage(25.0))
    }

    @Test
    fun `the open model sees the pause in its p99`() {
        val open = openLoop(paused(), rate, duration)
        // 1,400 requests should have been sent during the pause: about 4.7% of all of them
        assertThat(open.quantile(0.99)).isGreaterThan(1_000_000)
        assertThat(open.max).isGreaterThanOrEqualTo(1_400_000)
    }

    @Test
    fun `the closed model hides the pause from everything but the max`() {
        val closed = closedLoop(paused(), rate, connections = 10, durationMicros = duration).fromActualSend
        assertThat(closed.quantile(0.99)).isLessThan(10_000)               // looks perfectly healthy
        assertThat(closed.max).isGreaterThanOrEqualTo(1_400_000)           // only 10 samples saw the pause
    }

    @Test
    fun `timing the closed model from the planned send time gets the truth back`() {
        val open = openLoop(paused(), rate, duration)
        val corrected = closedLoop(paused(), rate, connections = 10, durationMicros = duration).fromPlannedSend
        assertThat(corrected.quantile(0.99)).isCloseTo(open.quantile(0.99), Percentage.withPercentage(20.0))
    }
}
