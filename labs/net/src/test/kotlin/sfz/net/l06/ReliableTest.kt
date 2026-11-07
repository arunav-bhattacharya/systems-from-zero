package sfz.net.l06

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.InetSocketAddress
import java.time.Duration
import java.util.Collections

@Timeout(10)
class ReliableTest {
    private val loopback = InetAddress.getLoopbackAddress()
    private val closeLater = mutableListOf<AutoCloseable>()
    private fun <T : AutoCloseable> T.closing(): T = also { closeLater += it }

    @AfterEach
    fun cleanUp() = closeLater.reversed().forEach { it.close() }

    private val delivered: MutableList<String> = Collections.synchronizedList(mutableListOf())

    private lateinit var receiver: ReliableReceiver

    /** A receiver running on its own thread, behind a LossyLink; returns a sender that talks through the link. */
    private fun connect(
        dropForward: (Int) -> Boolean = { false },
        dropBack: (Int) -> Boolean = { false },
        timeout: Duration = Duration.ofMillis(200),
        maxAttempts: Int = 5,
    ): ReliableSender {
        val receiverSocket = DatagramSocket(InetSocketAddress(loopback, 0)).closing()
        receiver = ReliableReceiver(receiverSocket) { delivered += it.decodeToString() }
        Thread.ofPlatform().daemon().start { receiver.serve() }
        val link = LossyLink(receiverSocket.localSocketAddress, dropForward, dropBack).closing()
        val senderSocket = DatagramSocket(InetSocketAddress(loopback, 0)).closing()
        return ReliableSender(senderSocket, link.address, timeout, maxAttempts)
    }

    @Test
    fun `with nothing lost, every message takes one attempt`() {
        val sender = connect()
        val attempts = listOf("AUTH 1", "AUTH 2", "AUTH 3").map { sender.send(it.toByteArray()) }
        assertThat(attempts).containsExactly(1, 1, 1)
        assertThat(delivered).containsExactly("AUTH 1", "AUTH 2", "AUTH 3")
        assertThat(sender.retransmissions).isZero()
    }

    @Test
    fun `a lost DATA datagram is sent again after the timeout`() {
        val sender = connect(dropForward = { it == 0 })
        val start = System.nanoTime()
        assertThat(sender.send("AUTH 4242".toByteArray())).isEqualTo(2)
        assertThat(Duration.ofNanos(System.nanoTime() - start)).`as`("it waited one timeout first").isGreaterThanOrEqualTo(Duration.ofMillis(150))
        assertThat(sender.retransmissions).isEqualTo(1)
        assertThat(delivered).containsExactly("AUTH 4242")
    }

    @Test
    fun `a lost ACK makes the receiver see a duplicate, which it acknowledges but delivers only once`() {
        val sender = connect(dropBack = { it == 0 })
        assertThat(sender.send("CAPTURE 4242".toByteArray())).isEqualTo(2)
        assertThat(sender.send("REFUND 4242".toByteArray())).isEqualTo(1)
        assertThat(delivered).containsExactly("CAPTURE 4242", "REFUND 4242")
        assertThat(receiver.duplicates).isEqualTo(1)
    }

    @Test
    fun `losing every third datagram one way and every fourth the other, 40 messages still arrive once each, in order`() {
        val sender = connect(dropForward = { it % 3 == 2 }, dropBack = { it % 4 == 3 }, timeout = Duration.ofMillis(60), maxAttempts = 10)
        val messages = (1..40).map { "AUTH $it" }
        messages.forEach { sender.send(it.toByteArray()) }
        assertThat(delivered).containsExactlyElementsOf(messages)
        assertThat(sender.retransmissions).isGreaterThan(10)
        assertThat(receiver.duplicates).isGreaterThan(0)
    }

    @Test
    fun `when the peer is gone, the sender gives up after its last attempt`() {
        val silent = DatagramSocket(InetSocketAddress(loopback, 0)).closing()     // bound, never answers
        val sender = ReliableSender(DatagramSocket(InetSocketAddress(loopback, 0)).closing(), silent.localSocketAddress, Duration.ofMillis(50), maxAttempts = 3)
        val start = System.nanoTime()
        assertThatThrownBy { sender.send("AUTH 4242".toByteArray()) }.isInstanceOf(DeliveryFailedException::class.java)
        assertThat(Duration.ofNanos(System.nanoTime() - start)).isGreaterThanOrEqualTo(Duration.ofMillis(140))
        assertThat(sender.retransmissions).isEqualTo(2)
    }

    @Test
    fun `an ACK for a different sequence number does not count`() {
        // a fake peer that first answers with a stale ACK, then with the right one
        val peer = DatagramSocket(InetSocketAddress(loopback, 0)).closing()
        Thread.ofPlatform().daemon().start {
            val p = DatagramPacket(ByteArray(100), 100)
            peer.receive(p)
            val seq = Frame.decode(p.data, p.length)!!.seq
            for (s in listOf(seq + 7, seq)) {
                val ack = Frame(Frame.Kind.ACK, s).encode()
                peer.send(DatagramPacket(ack, ack.size, p.socketAddress))
            }
        }
        val sender = ReliableSender(DatagramSocket(InetSocketAddress(loopback, 0)).closing(), peer.localSocketAddress, Duration.ofSeconds(2))
        assertThat(sender.send("AUTH 4242".toByteArray())).isEqualTo(1)
    }

    @Test
    fun `sequence numbers start at 0 and go up by one per message`() {
        val seen = Collections.synchronizedList(mutableListOf<Int>())
        val peer = DatagramSocket(InetSocketAddress(loopback, 0)).closing()
        Thread.ofPlatform().daemon().start {
            val p = DatagramPacket(ByteArray(100), 100)
            repeat(3) {
                peer.receive(p)
                val f = Frame.decode(p.data, p.length)!!
                seen += f.seq
                val ack = Frame(Frame.Kind.ACK, f.seq).encode()
                peer.send(DatagramPacket(ack, ack.size, p.socketAddress))
            }
        }
        val sender = ReliableSender(DatagramSocket(InetSocketAddress(loopback, 0)).closing(), peer.localSocketAddress)
        repeat(3) { sender.send("m$it".toByteArray()) }
        assertThat(seen).containsExactly(0, 1, 2)
    }
}
