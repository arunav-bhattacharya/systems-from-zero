package sfz.os.l11

import java.net.InetSocketAddress
import java.nio.ByteBuffer
import java.nio.channels.SelectionKey
import java.nio.channels.Selector
import java.nio.channels.ServerSocketChannel
import java.nio.channels.SocketChannel
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicLong

/**
 * A real echo server on 127.0.0.1 with ONE thread and a [Selector], which is epoll on Linux and
 * kqueue on macOS. Whatever a client sends comes back to it.
 *
 * [start] binds a free port, makes the channel non-blocking, registers it for OP_ACCEPT and starts
 * a single platform thread named [THREAD] that runs [loop]. Everything except [loop] is written for you.
 */
class NioEchoServer : AutoCloseable {
    private val selector: Selector = Selector.open()
    private val server: ServerSocketChannel = ServerSocketChannel.open()
    private lateinit var thread: Thread
    @Volatile private var running = true

    /** Connections open right now. */
    val connections = AtomicInteger()
    /** How many times select() returned: wake-ups, not connections. */
    val wakeups = AtomicLong()

    val port: Int get() = (server.localAddress as InetSocketAddress).port

    fun start(): NioEchoServer {
        server.bind(InetSocketAddress("127.0.0.1", 0), 1024)
        server.configureBlocking(false)
        server.register(selector, SelectionKey.OP_ACCEPT)
        thread = Thread.ofPlatform().name(THREAD).daemon().start { loop() }
        return this
    }

    /**
     * The event loop. Until [running] is false:
     * 1. `selector.select()` sleeps until at least one channel is ready; count it in [wakeups].
     * 2. For each key in `selectedKeys()` (remove it from the set as you go):
     *    - acceptable: `server.accept()`, make the new channel non-blocking, register it for OP_READ
     *      and count it in [connections];
     *    - readable: read into a buffer; -1 means the client closed, so cancel the key, close the
     *      channel and count it out; otherwise flip the buffer and write it all back.
     * Closing the selector (in [close]) makes select() throw or return; just leave the loop then.
     */
    private fun loop() {
        TODO("loop: select, then accept or read and echo each selected key")
    }

    override fun close() {
        running = false
        selector.close()                                   // wakes select() and frees the epoll instance
        server.close()
        thread.join(2000)
    }

    companion object {
        const val THREAD = "nio-echo"
    }
}
