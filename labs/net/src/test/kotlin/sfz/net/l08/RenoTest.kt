package sfz.net.l08

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test

class RenoTest {
    @Test
    fun `slow start doubles the window every round trip`() {
        val reno = Reno(initialWindow = 10)
        val perRound = (1..4).map {
            val w = reno.cwnd
            repeat(w) { reno.onAck() }                       // a whole window of ACKs
            reno.cwnd
        }
        assertThat(perRound).containsExactly(20, 40, 80, 160)
        assertThat(reno.inSlowStart).isTrue()
    }

    @Test
    fun `three duplicate ACKs halve the window and end slow start`() {
        val reno = Reno(initialWindow = 10)
        repeat(150) { reno.onAck() }                         // 160 segments
        reno.onTripleDuplicateAck()
        assertThat(reno.ssthresh).isEqualTo(80)
        assertThat(reno.cwnd).isEqualTo(80)
        assertThat(reno.inSlowStart).isFalse()
    }

    @Test
    fun `in congestion avoidance a whole window of ACKs adds exactly one segment`() {
        val reno = Reno(initialWindow = 10)
        repeat(70) { reno.onAck() }                          // 80
        reno.onTripleDuplicateAck()                          // 40, ssthresh 40
        repeat(39) { reno.onAck() }
        assertThat(reno.cwnd).`as`("39 of 40 ACKs: not yet").isEqualTo(40)
        reno.onAck()
        assertThat(reno.cwnd).isEqualTo(41)
        repeat(41) { reno.onAck() }
        assertThat(reno.cwnd).isEqualTo(42)
    }

    @Test
    fun `a timeout starts over from one segment, then slow starts up to the new threshold`() {
        val reno = Reno(initialWindow = 10)
        repeat(30) { reno.onAck() }                          // 40
        reno.onTimeout()
        assertThat(reno.cwnd).isEqualTo(1)
        assertThat(reno.ssthresh).isEqualTo(20)
        val perRound = (1..6).map {
            repeat(reno.cwnd) { reno.onAck() }
            reno.cwnd
        }
        assertThat(perRound).`as`("doubling up to the threshold of 20, then one segment per round").containsExactly(2, 4, 8, 16, 20, 21)
    }

    @Test
    fun `the window never drops below two segments on a loss`() {
        val reno = Reno(initialWindow = 2)
        reno.onTripleDuplicateAck()
        assertThat(reno.ssthresh).isEqualTo(2)
        assertThat(reno.cwnd).isEqualTo(2)
    }

    @Test
    fun `the sawtooth over a path that holds 100 segments`() {
        val windows = sawtooth(Reno(initialWindow = 10), rounds = 130, capacity = 100)
        assertThat(windows.take(8)).`as`("slow start overshoots, halves, then grows by one per round")
            .containsExactly(10, 20, 40, 80, 160, 80, 81, 82)
        assertThat(windows[26]).`as`("101 overflows the path").isEqualTo(101)
        assertThat(windows[27]).isEqualTo(50)
        val afterFirstLoss = windows.drop(27)
        assertThat(afterFirstLoss.max()).isEqualTo(101)
        assertThat(afterFirstLoss.min()).isEqualTo(50)
        assertThat(afterFirstLoss.average()).`as`("Reno's sawtooth averages about 3/4 of the peak").isCloseTo(75.5, within(1.0))
    }

    @Test
    fun `CUBIC drops to 70 percent, flattens out at the old maximum, then probes beyond it`() {
        val wMax = 100.0
        assertThat(cubicWindow(0.0, wMax)).isCloseTo(70.0, within(1e-9))
        val k = Math.cbrt(wMax * 0.3 / 0.4)                  // 4.22 s
        assertThat(cubicWindow(k, wMax)).isCloseTo(100.0, within(1e-9))
        val climbEarly = cubicWindow(1.0, wMax) - cubicWindow(0.0, wMax)
        val climbNearMax = cubicWindow(k, wMax) - cubicWindow(k - 1.0, wMax)
        assertThat(climbEarly).`as`("fast at first").isGreaterThan(10 * climbNearMax)
        assertThat(cubicWindow(k + 3.0, wMax)).`as`("then past the old maximum").isCloseTo(110.8, within(0.1))
    }
}
