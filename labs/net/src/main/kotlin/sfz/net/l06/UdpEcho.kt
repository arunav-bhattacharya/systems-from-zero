package sfz.net.l06

import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.SocketTimeoutException
import java.nio.ByteBuffer
import java.nio.channels.ClosedChannelException
import java.nio.channels.DatagramChannel
import java.time.Duration

/**
 * A UDP echo server on 127.0.0.1: every datagram that arrives goes straight back to the address it
 * came from. Pass port 0 and the kernel picks a free port; read it from [port].
 *
 * The constructor opens and binds the socket and starts one thread that runs [serve]. [close] closes
 * the channel, which makes the blocked `receive()` throw, and that ends the thread.
 */
class UdpEchoServer(port: Int = 0) : AutoCloseable {
    private val channel: DatagramChannel =
        DatagramChannel.open().bind(InetSocketAddress(InetAddress.getLoopbackAddress(), port))

    /** The port the server listens on. */
    val port: Int = (channel.localAddress as InetSocketAddress).port

    /** How many datagrams it has sent back so far. */
    @Volatile
    var echoed: Int = 0
        private set

    private val worker = Thread.ofPlatform().daemon().name("udp-echo-$port").start { serve() }

    /**
     * The server loop. Receive one datagram into a buffer big enough for any UDP datagram (65,535 bytes):
     * `channel.receive(buffer)` blocks until one arrives and returns the sender's address. Flip the
     * buffer, send exactly those bytes back to that address, count it in [echoed], clear, repeat.
     * Return quietly when the channel is closed (`receive` throws a [ClosedChannelException]).
     */
    private fun serve() {
        TODO("receive, flip, send back to the returned address, clear; stop on ClosedChannelException")
    }

    override fun close() {
        channel.close()
        worker.join(1_000)
    }
}

/**
 * Sends [payload] to [target] as one datagram, then waits up to [timeout] for one datagram back and
 * returns its bytes (exactly as many as arrived). Returns null when nothing came back in time. UDP
 * never says why: the request, the server or the answer may be gone, and the code here can't tell.
 *
 * Use a fresh [DatagramSocket] (bound to any free port) and close it before you return. Its
 * `soTimeout` makes `receive()` throw [SocketTimeoutException] after that many milliseconds.
 */
fun udpRequest(target: InetSocketAddress, payload: ByteArray, timeout: Duration): ByteArray? {
    TODO("open a DatagramSocket, set soTimeout, send one DatagramPacket, receive one, or null on timeout")
}
