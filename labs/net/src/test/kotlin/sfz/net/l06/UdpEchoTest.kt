package sfz.net.l06

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.InetSocketAddress
import java.time.Duration

@Timeout(10)
class UdpEchoTest {
    private val loopback = InetAddress.getLoopbackAddress()

    /**
     * The server sends the reply and then counts it, on its own thread, so the client can hold the reply
     * a moment before `echoed` goes up. Wait briefly for the count instead of reading it at once.
     */
    private fun UdpEchoServer.echoedSoon(atLeast: Int, within: Duration = Duration.ofSeconds(2)): Int {
        val deadline = System.nanoTime() + within.toNanos()
        while (echoed < atLeast && System.nanoTime() < deadline) Thread.sleep(5)
        return echoed
    }

    @Test
    fun `the echo server sends a datagram back to whoever sent it`() {
        UdpEchoServer().use { server ->
            val answer = udpRequest(InetSocketAddress(loopback, server.port), "AUTH 4242 100.00".toByteArray(), Duration.ofSeconds(2))
            assertThat(answer?.decodeToString()).isEqualTo("AUTH 4242 100.00")
            assertThat(server.echoedSoon(1)).isEqualTo(1)
        }
    }

    @Test
    fun `three sends are three datagrams, and each receive returns exactly one`() {
        UdpEchoServer().use { server ->
            DatagramSocket().use { socket ->
                socket.soTimeout = 2_000
                val target = InetSocketAddress(loopback, server.port)
                for (m in listOf("AUTH 1", "AUTH 22", "AUTH 333")) socket.send(DatagramPacket(m.toByteArray(), m.length, target))
                val got = List(3) {
                    val p = DatagramPacket(ByteArray(1_000), 1_000)
                    socket.receive(p)
                    String(p.data, 0, p.length)
                }
                assertThat(got).`as`("UDP keeps the boundaries; on loopback nothing is lost or reordered").containsExactly("AUTH 1", "AUTH 22", "AUTH 333")
            }
        }
    }

    @Test
    fun `an 8,000-byte datagram comes back whole, in one receive`() {
        UdpEchoServer().use { server ->
            val big = ByteArray(8_000) { (it % 251).toByte() }
            assertThat(udpRequest(InetSocketAddress(loopback, server.port), big, Duration.ofSeconds(2))).isEqualTo(big)
        }
    }

    @Test
    fun `each client gets its own answer back`() {
        UdpEchoServer().use { server ->
            val target = InetSocketAddress(loopback, server.port)
            val answers = java.util.concurrent.ConcurrentHashMap<String, String>()
            val clients = listOf("from A", "from B").map { m ->
                Thread.ofPlatform().start { udpRequest(target, m.toByteArray(), Duration.ofSeconds(2))?.let { answers[m] = it.decodeToString() } }
            }
            clients.forEach { it.join() }
            assertThat(answers).containsEntry("from A", "from A").containsEntry("from B", "from B")
            assertThat(server.echoedSoon(2)).isEqualTo(2)
        }
    }

    @Test
    fun `when nobody answers, udpRequest returns null once the timeout has passed`() {
        DatagramSocket(InetSocketAddress(loopback, 0)).use { silent ->   // bound, but never replies
            val start = System.nanoTime()
            val answer = udpRequest(silent.localSocketAddress as InetSocketAddress, "AUTH 4242".toByteArray(), Duration.ofMillis(300))
            val waited = Duration.ofNanos(System.nanoTime() - start)
            assertThat(answer).isNull()
            assertThat(waited).isGreaterThanOrEqualTo(Duration.ofMillis(250))
        }
    }

    @Test
    fun `close stops the server`() {
        val server = UdpEchoServer()
        val target = InetSocketAddress(loopback, server.port)
        assertThat(udpRequest(target, "one".toByteArray(), Duration.ofSeconds(2))).isNotNull()
        server.close()
        assertThat(udpRequest(target, "two".toByteArray(), Duration.ofMillis(200))).isNull()
    }
}
