package sfz.net.l07

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.net.support.Hex

/** Real frames from the first Try it, captured on client in env/net.yml. */
class TcpHeaderTest {
    private val frames = Hex.resourceFrames("sfz/net/l07/echo-connection.txt")

    @Test
    fun `the SYN carries the ports, the client initial sequence number, no ACK yet, and the MSS option`() {
        val syn = TcpHeader.parse(frames[0])
        assertThat(syn.srcPort).isEqualTo(50744)
        assertThat(syn.dstPort).isEqualTo(9000)
        assertThat(syn.seq).isEqualTo(244700535L)
        assertThat(syn.ack).isZero()
        assertThat(syn.flags).containsExactly(Flag.SYN)
        assertThat(syn.window).isEqualTo(64240)
        assertThat(syn.mss).`as`("options: mss 1460, sackOK, timestamps, nop, wscale 7").isEqualTo(1460)
        assertThat(syn.payloadLength).isZero()
        assertThat(syn.sequenceLength).`as`("a SYN uses one sequence number").isEqualTo(1)
    }

    @Test
    fun `the SYN-ACK acknowledges the client's ISN plus one, and its seq is above 2 to the 31`() {
        val synAck = TcpHeader.parse(frames[1])
        assertThat(synAck.seq).`as`("unsigned: 0xf0f7f3fa").isEqualTo(4042781690L)
        assertThat(synAck.ack).isEqualTo(244700536L)
        assertThat(synAck.flags).containsExactlyInAnyOrder(Flag.SYN, Flag.ACK)
    }

    @Test
    fun `the data segment carries 17 bytes, counted from the IP total length`() {
        val data = TcpHeader.parse(frames[3])
        assertThat(data.payloadLength).isEqualTo(17)
        assertThat(data.flags).containsExactlyInAnyOrder(Flag.PSH, Flag.ACK)
        assertThat(data.mss).`as`("only SYNs carry the MSS").isNull()
    }

    @Test
    fun `all ten frames of the connection parse to the segments tcpdump printed`() {
        assertThat(frames.map(TcpHeader::parse)).containsExactlyElementsOf(Captured.connection)
    }

    @Test
    fun `a frame that is not TCP is rejected`() {
        val udp = frames[0].copyOf().also { it[23] = 17 }              // IP protocol 17: UDP
        assertThatThrownBy { TcpHeader.parse(udp) }.isInstanceOf(IllegalArgumentException::class.java)
    }
}
