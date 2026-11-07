package sfz.net.l07

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.net.l07.Captured.CLIENT_ISN
import sfz.net.l07.Captured.CLIENT_PORT
import sfz.net.l07.Captured.SERVER_ISN
import sfz.net.l07.Captured.SERVER_PORT
import sfz.net.l07.Captured.connection
import sfz.net.l07.TcpState.CLOSED
import sfz.net.l07.TcpState.CLOSE_WAIT
import sfz.net.l07.TcpState.CLOSING
import sfz.net.l07.TcpState.ESTABLISHED
import sfz.net.l07.TcpState.FIN_WAIT_1
import sfz.net.l07.TcpState.FIN_WAIT_2
import sfz.net.l07.TcpState.LAST_ACK
import sfz.net.l07.TcpState.LISTEN
import sfz.net.l07.TcpState.SYN_RECEIVED
import sfz.net.l07.TcpState.SYN_SENT
import sfz.net.l07.TcpState.TIME_WAIT
import sfz.net.support.ManualClock

/**
 * Your two endpoints replay the captured connection: each segment one of them sends must match the
 * one the real kernel sent (window and options aside), and both must pass through the states
 * `ss -tan` showed.
 */
class TcpEndpointTest {
    private val clock = ManualClock()
    private val client = TcpEndpoint(CLIENT_PORT, CLIENT_ISN, clock)
    private val server = TcpEndpoint(SERVER_PORT, SERVER_ISN, clock).apply { listen() }

    /** Runs the handshake from the capture and returns both ends ESTABLISHED. */
    private fun handshake() {
        assertThat(client.connect(SERVER_PORT).shape()).isEqualTo(connection[0].shape())
        assertThat(server.receive(connection[0]).shape()).isEqualTo(connection[1].shape())
        assertThat(client.receive(connection[1]).shape()).isEqualTo(connection[2].shape())
        assertThat(server.receive(connection[2])).isNull()
    }

    @Test
    fun `the handshake goes SYN, SYN-ACK, ACK with the captured numbers, and both sides change state`() {
        assertThat(server.state).isEqualTo(LISTEN)
        client.connect(SERVER_PORT)
        assertThat(client.state).isEqualTo(SYN_SENT)
        server.receive(connection[0])
        assertThat(server.state).isEqualTo(SYN_RECEIVED)
        assertThat(server.remotePort).isEqualTo(CLIENT_PORT)
        client.receive(connection[1])
        assertThat(client.state).`as`("connect() returns here").isEqualTo(ESTABLISHED)
        server.receive(connection[2])
        assertThat(server.state).`as`("accept() can take it now").isEqualTo(ESTABLISHED)
        assertThat(client.sndNxt).isEqualTo(CLIENT_ISN + 1)
        assertThat(client.rcvNxt).isEqualTo(SERVER_ISN + 1)
    }

    @Test
    fun `the whole captured connection, from SYN to TIME-WAIT`() {
        handshake()
        // 17 bytes of data and the ACK for them
        assertThat(client.send(17).shape()).isEqualTo(connection[3].shape())
        assertThat(server.receive(connection[3]).shape()).isEqualTo(connection[4].shape())
        assertThat(client.receive(connection[4])).isNull()

        // the client closes first
        assertThat(client.close().shape()).isEqualTo(connection[5].shape())
        assertThat(client.state).isEqualTo(FIN_WAIT_1)
        val ackOfFin = server.receive(connection[5])
        assertThat(ackOfFin?.ack).`as`("the FIN took one sequence number").isEqualTo(244700554L)
        assertThat(server.state).`as`("the server program hasn't closed yet").isEqualTo(CLOSE_WAIT)

        // half-closed: the server still sends its echo, and the client still receives it
        assertThat(server.send(17).shape()).isEqualTo(connection[6].shape())
        assertThat(client.receive(connection[6]).shape()).isEqualTo(connection[7].shape())
        assertThat(client.state).isEqualTo(FIN_WAIT_2)
        assertThat(server.receive(connection[7])).isNull()

        // the server closes second
        assertThat(server.close().shape()).isEqualTo(connection[8].shape())
        assertThat(server.state).isEqualTo(LAST_ACK)
        assertThat(client.receive(connection[8]).shape()).isEqualTo(connection[9].shape())
        assertThat(client.state).isEqualTo(TIME_WAIT)
        assertThat(server.receive(connection[9])).isNull()
        assertThat(server.state).isEqualTo(CLOSED)
    }

    @Test
    fun `TIME-WAIT lasts 60 seconds on Linux, then the socket is gone`() {
        handshake()
        val fin = client.close()
        client.receive(server.receive(fin)!!)                    // the ACK of the client's FIN
        client.receive(server.close())                           // the server's FIN
        assertThat(client.state).isEqualTo(TIME_WAIT)
        clock.advanceSeconds(59)
        client.tick()
        assertThat(client.state).isEqualTo(TIME_WAIT)
        clock.advanceSeconds(1)
        client.tick()
        assertThat(client.state).isEqualTo(CLOSED)
    }

    @Test
    fun `a FIN repeated in TIME-WAIT is ACKed again, and the wait starts over`() {
        handshake()
        val fin = client.close()
        client.receive(server.receive(fin)!!)
        val serverFin = server.close()
        val lastAck = client.receive(serverFin)
        clock.advanceSeconds(40)
        // the last ACK was lost, so the server sends its FIN again
        assertThat(client.receive(serverFin).shape()).isEqualTo(lastAck.shape())
        clock.advanceSeconds(40)
        client.tick()
        assertThat(client.state).`as`("80 s after the first FIN, 40 s after the second").isEqualTo(TIME_WAIT)
        clock.advanceSeconds(20)
        client.tick()
        assertThat(client.state).isEqualTo(CLOSED)
    }

    @Test
    fun `a SYN to a port where nothing listens gets the RST the capture shows, and connect fails at once`() {
        val nobody = TcpEndpoint(9001, 777, clock)                 // never called listen()
        assertThat(nobody.receive(Captured.refusedSyn).shape()).isEqualTo(Captured.refusedRst.shape())

        val dialer = TcpEndpoint(60578, 1259064435, clock)
        dialer.connect(9001)
        dialer.receive(Captured.refusedRst)
        assertThat(dialer.state).isEqualTo(CLOSED)
        assertThat(dialer.reset).`as`("ConnectException: Connection refused").isTrue()
    }

    @Test
    fun `an RST is never answered`() {
        val nobody = TcpEndpoint(9001, 777, clock)
        assertThat(nobody.receive(Captured.refusedRst)).isNull()
    }

    @Test
    fun `when both sides close at the same moment, both go through CLOSING to TIME-WAIT`() {
        handshake()
        val clientFin = client.close()
        val serverFin = server.close()
        assertThat(server.state).isEqualTo(FIN_WAIT_1)
        val ackFromServer = server.receive(clientFin)
        val ackFromClient = client.receive(serverFin)
        assertThat(client.state).isEqualTo(CLOSING)
        assertThat(server.state).isEqualTo(CLOSING)
        client.receive(ackFromServer!!)
        server.receive(ackFromClient!!)
        assertThat(client.state).isEqualTo(TIME_WAIT)
        assertThat(server.state).`as`("both sides closed first, so both wait").isEqualTo(TIME_WAIT)
    }

    @Test
    fun `a segment that is not the next one expected gets a duplicate ACK and changes nothing`() {
        handshake()
        val ahead = Segment(CLIENT_PORT, SERVER_PORT, CLIENT_ISN + 1 + 1448, SERVER_ISN + 1, setOf(Flag.PSH, Flag.ACK), 502, 1448)
        val reply = server.receive(ahead)
        assertThat(reply?.ack).`as`("still waiting for the first byte").isEqualTo(CLIENT_ISN + 1)
        assertThat(server.rcvNxt).isEqualTo(CLIENT_ISN + 1)
        assertThat(server.state).isEqualTo(ESTABLISHED)
    }

    @Test
    fun `sequence numbers wrap around after 2 to the 32 minus one`() {
        val wrapping = TcpEndpoint(40000, 0xFFFF_FFFFL, clock)
        wrapping.connect(9000)
        assertThat(wrapping.sndNxt).isZero()
    }
}
