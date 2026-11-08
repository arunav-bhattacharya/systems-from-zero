package sfz.found.l02

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.data.Offset
import org.junit.jupiter.api.Test
import kotlin.math.pow

class FanOutTest {
    @Test
    fun `the root waits for its slowest leaf`() {
        val calls = listOf(LeafCall(8_000, 9_000), LeafCall(12_000, 7_000), LeafCall(6_000, 6_000))
        assertThat(rootLatency(calls, hedgeAfter = null)).isEqualTo(12_000L to 0)
    }

    @Test
    fun `a late leaf gets a hedge and the first answer wins`() {
        val calls = listOf(LeafCall(8_000, 9_000), LeafCall(1_000_000, 10_000))
        // the slow leaf is hedged at 15 ms, and the hedge answers 10 ms later
        assertThat(rootLatency(calls, hedgeAfter = 15_000)).isEqualTo(25_000L to 1)
    }

    @Test
    fun `a hedge that is slower than the first copy does not make things worse`() {
        val calls = listOf(LeafCall(20_000, 1_000_000))
        assertThat(rootLatency(calls, hedgeAfter = 15_000)).isEqualTo(20_000L to 1)
    }

    @Test
    fun `a leaf that answers in time is never hedged`() {
        val calls = listOf(LeafCall(15_000, 1_000), LeafCall(14_000, 1_000))
        assertThat(rootLatency(calls, hedgeAfter = 15_000)).isEqualTo(15_000L to 0)
    }

    @Test
    fun `with 100 leaves each slow 1 time in 100, most user requests are slow`() {
        val r = simulateFanOut(leaves = 100, requests = 20_000, hedgeAfter = null)
        assertThat(r.slowFraction).isCloseTo(1 - 0.99.pow(100), Offset.offset(0.02))    // about 0.634
    }

    @Test
    fun `hedging after 15 ms buys back the tail for about 1 percent more requests`() {
        val plain = simulateFanOut(leaves = 100, requests = 20_000, hedgeAfter = null)
        val hedged = simulateFanOut(leaves = 100, requests = 20_000, hedgeAfter = 15_000)
        assertThat(plain.root.quantile(0.99)).isGreaterThan(900_000)
        assertThat(hedged.root.quantile(0.99)).isLessThan(50_000)
        assertThat(hedged.slowFraction).isLessThan(0.01)
        assertThat(hedged.extraLoad).isCloseTo(0.01, Offset.offset(0.002))
    }

    @Test
    fun `hedging does nothing when every replica is slow for the same reason`() {
        val hedged = simulateFanOut(leaves = 100, requests = 20_000, hedgeAfter = 15_000, correlated = true)
        assertThat(hedged.slowFraction).isCloseTo(1 - 0.99.pow(100), Offset.offset(0.02))
    }
}
