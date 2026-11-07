package sfz.os.l11

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import java.net.Socket
import java.util.concurrent.TimeUnit

@Timeout(20, unit = TimeUnit.SECONDS)
class NioEchoTest {
    private fun connect(port: Int): Socket = Socket("127.0.0.1", port).apply { soTimeout = 3000 }

    private fun echo(s: Socket, text: String): String {
        val bytes = text.toByteArray()
        s.getOutputStream().write(bytes)
        val back = ByteArray(bytes.size)
        var got = 0
        while (got < back.size) {
            val n = s.getInputStream().read(back, got, back.size - got)
            if (n < 0) break
            got += n
        }
        return String(back, 0, got)
    }

    private fun waitFor(what: () -> Boolean) {
        val end = System.nanoTime() + 3_000_000_000L
        while (!what() && System.nanoTime() < end) Thread.sleep(10)
    }

    private fun serverThreads(): Int = Thread.getAllStackTraces().keys.count { it.name == NioEchoServer.THREAD && it.isAlive }

    @Test
    fun `one thread echoes for 200 clients`() {
        NioEchoServer().start().use { server ->
            val clients = List(200) { connect(server.port) }
            val answers = clients.mapIndexed { i, c -> echo(c, "auth-$i ok\n") }
            assertThat(answers).isEqualTo(List(200) { "auth-$it ok\n" })
            waitFor { server.connections.get() == 200 }
            assertThat(server.connections.get()).isEqualTo(200)
            assertThat(serverThreads()).isEqualTo(1)                    // not one per connection
            clients.forEach { it.close() }
        }
    }

    @Test
    fun `every client keeps its own stream, even when they take turns`() {
        NioEchoServer().start().use { server ->
            val a = connect(server.port)
            val b = connect(server.port)
            assertThat(echo(a, "refund 12.50\n")).isEqualTo("refund 12.50\n")
            assertThat(echo(b, "capture 120.00\n")).isEqualTo("capture 120.00\n")
            assertThat(echo(a, "void\n")).isEqualTo("void\n")
            a.close(); b.close()
        }
    }

    @Test
    fun `quiet connections cost no wake-ups, and closed ones are forgotten`() {
        NioEchoServer().start().use { server ->
            val clients = List(50) { connect(server.port) }
            waitFor { server.connections.get() == 50 }
            val before = server.wakeups.get()
            Thread.sleep(300)                                           // 50 idle connections: select() just sleeps
            assertThat(server.wakeups.get() - before).isZero()
            assertThat(before).isBetween(1L, 60L)                       // about one wake-up per accept

            clients.forEach { it.close() }
            waitFor { server.connections.get() == 0 }
            assertThat(server.connections.get()).isZero()
        }
    }
}
