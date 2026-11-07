package sfz.net.l11

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * Three streams interleaved one packet each, A B C A B C, like the three answers in the lesson's
 * stepper. One packet every millisecond, 25 ms one way, and a lost packet is resent 50 ms after it left.
 */
class HolModelTest {
    private val t = Timing(sendGapMs = 1, oneWayMs = 25, resendAfterMs = 50)
    private val packets = listOf(Packet(1, 1200), Packet(3, 1200), Packet(5, 1200), Packet(1, 800), Packet(3, 800), Packet(5, 800))

    @Test
    fun `a lost packet arrives a resend later`() {
        assertThat(HolModel.arrival(1, emptySet(), t)).isEqualTo(26)
        assertThat(HolModel.arrival(1, setOf(1), t)).isEqualTo(76)
    }

    @Test
    fun `with nothing lost, TCP and QUIC deliver alike`() {
        val expected = mapOf(1 to 28L, 3 to 29L, 5 to 30L)
        assertThat(HolModel.tcp(packets, emptySet(), t)).isEqualTo(expected)
        assertThat(HolModel.quic(packets, emptySet(), t)).isEqualTo(expected)
    }

    @Test
    fun `over TCP one lost packet of stream 3 holds back every stream`() {
        assertThat(HolModel.tcp(packets, setOf(1), t)).isEqualTo(mapOf(1 to 76L, 3 to 76L, 5 to 76L))
    }

    @Test
    fun `over QUIC the same loss holds back only stream 3`() {
        assertThat(HolModel.quic(packets, setOf(1), t)).isEqualTo(mapOf(1 to 28L, 3 to 76L, 5 to 30L))
    }

    @Test
    fun `a loss at the very end hurts only its own stream, even over TCP`() {
        assertThat(HolModel.tcp(packets, setOf(5), t)).isEqualTo(mapOf(1 to 28L, 3 to 29L, 5 to 80L))
    }

    @Test
    fun `losing the first packet delays everything over TCP`() {
        assertThat(HolModel.tcp(packets, setOf(0), t)).isEqualTo(mapOf(1 to 75L, 3 to 75L, 5 to 75L))
        assertThat(HolModel.quic(packets, setOf(0), t)).isEqualTo(mapOf(1 to 75L, 3 to 29L, 5 to 30L))
    }
}
