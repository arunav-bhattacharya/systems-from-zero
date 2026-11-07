package sfz.net.l08

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test

class NagleTest {
    @Test
    fun `with nothing in flight a small write goes out at once`() {
        val sender = NagleSender()
        assertThat(sender.write(12)).containsExactly(12)
        assertThat(sender.unacked).isEqualTo(12)
    }

    @Test
    fun `a second small write waits for the ACK of the first`() {
        val sender = NagleSender()
        sender.write(12)
        assertThat(sender.write(100)).isEmpty()
        assertThat(sender.buffered).isEqualTo(100)
        assertThat(sender.onAck(12)).containsExactly(100)
        assertThat(sender.buffered).isZero()
    }

    @Test
    fun `small writes made while waiting are sent together as one segment`() {
        val sender = NagleSender()
        sender.write(12)
        repeat(5) { assertThat(sender.write(20)).isEmpty() }
        assertThat(sender.onAck(12)).`as`("five writes, one segment").containsExactly(100)
    }

    @Test
    fun `full segments go out even while data is unacknowledged, only the small tail waits`() {
        val sender = NagleSender(mss = 1448)
        sender.write(500)
        assertThat(sender.write(3000)).containsExactly(1448, 1448)
        assertThat(sender.buffered).isEqualTo(104)
        assertThat(sender.onAck(500)).`as`("2,896 bytes still in flight").isEmpty()
        assertThat(sender.onAck(2896)).containsExactly(104)
    }

    @Test
    fun `TCP_NODELAY sends every write at once`() {
        val sender = NagleSender(noDelay = true)
        assertThat(sender.write(12)).containsExactly(12)
        assertThat(sender.write(100)).containsExactly(100)
        assertThat(sender.write(3000)).containsExactly(1448, 1448, 104)
    }

    @Test
    fun `on loopback, write-write-read with Nagle costs one delayed ACK, about 40 ms`() {
        val nagle = writeWriteRead(12, 100, rttMillis = 0.05, delayedAckMillis = 40.0, noDelay = false)
        val noDelay = writeWriteRead(12, 100, rttMillis = 0.05, delayedAckMillis = 40.0, noDelay = true)
        assertThat(nagle).`as`("the demo measured a median of 41 to 43 ms").isCloseTo(40.1, within(0.01))
        assertThat(noDelay).isCloseTo(0.05, within(0.001))
    }

    @Test
    fun `across a 20 ms round trip the stall is two round trips plus the delayed ACK`() {
        assertThat(writeWriteRead(12, 100, rttMillis = 20.0, delayedAckMillis = 40.0, noDelay = false)).isCloseTo(80.0, within(0.01))
        assertThat(writeWriteRead(12, 100, rttMillis = 20.0, delayedAckMillis = 40.0, noDelay = true)).isCloseTo(20.0, within(0.01))
    }

    @Test
    fun `one write of header and body together never waits, even with Nagle on`() {
        val sender = NagleSender()
        assertThat(sender.write(112)).containsExactly(112)
    }
}
