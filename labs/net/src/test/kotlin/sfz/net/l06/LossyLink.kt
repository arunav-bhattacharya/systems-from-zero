package sfz.net.l06

import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.SocketAddress
import java.net.SocketException
import java.util.concurrent.atomic.AtomicInteger

/**
 * A stand-in for a lossy network, on 127.0.0.1. The sender talks to [address]; the link passes each
 * datagram on to [target], and passes whatever [target] answers back to the sender. [dropForward] and
 * [dropBack] see each datagram's index in its direction (0, 1, 2, ...) and decide whether it vanishes.
 * Nobody is told when one does, which is the point.
 */
class LossyLink(
    private val target: SocketAddress,
    private val dropForward: (Int) -> Boolean = { false },
    private val dropBack: (Int) -> Boolean = { false },
) : AutoCloseable {
    private val front = DatagramSocket(InetSocketAddress(InetAddress.getLoopbackAddress(), 0))   // faces the sender
    private val back = DatagramSocket(InetSocketAddress(InetAddress.getLoopbackAddress(), 0))    // faces the target
    @Volatile private var sender: SocketAddress? = null

    val forwarded = AtomicInteger()
    val dropped = AtomicInteger()

    val address: InetSocketAddress get() = front.localSocketAddress as InetSocketAddress

    private val threads = listOf(
        pump(front, back, dropForward) { target },
        pump(back, front, dropBack) { sender },
    )

    private fun pump(from: DatagramSocket, to: DatagramSocket, drop: (Int) -> Boolean, dest: () -> SocketAddress?) =
        Thread.ofPlatform().daemon().start {
            val buf = ByteArray(65_535)
            var index = 0
            while (true) {
                val p = DatagramPacket(buf, buf.size)
                try { from.receive(p) } catch (_: SocketException) { return@start }
                if (from === front) sender = p.socketAddress
                if (drop(index++)) { dropped.incrementAndGet(); continue }
                val d = dest() ?: continue
                try { to.send(DatagramPacket(p.data.copyOf(p.length), p.length, d)) } catch (_: SocketException) { return@start }
                forwarded.incrementAndGet()
            }
        }

    override fun close() {
        front.close()
        back.close()
        threads.forEach { it.join(1_000) }
    }
}
