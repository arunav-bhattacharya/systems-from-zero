package sfz.sql.l10.demo

import java.io.FilterInputStream
import java.io.FilterOutputStream
import java.io.InputStream
import java.io.OutputStream
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Socket
import java.sql.Connection
import java.sql.DriverManager
import java.util.Properties
import java.util.concurrent.atomic.AtomicInteger
import javax.net.SocketFactory

/**
 * Shared bits for the sql-10 demos. They connect to the Compose service's database "course"
 * (start it from the labs folder: docker compose -f env/postgres.yml up -d --wait).
 * Set SFZ_JDBC_URL to point them somewhere else.
 */
object Db {
    val url: String = System.getenv("SFZ_JDBC_URL") ?: "jdbc:postgresql://localhost:5432/course"
    const val USER = "sfz"
    const val PASSWORD = "sfz"

    init {
        // keep Hikari and Flyway to warnings, so the demo's own lines stand out
        System.setProperty("org.slf4j.simpleLogger.defaultLogLevel", "warn")
        System.setProperty("org.slf4j.simpleLogger.showDateTime", "false")
    }

    fun connect(extra: Map<String, String> = emptyMap()): Connection {
        val props = Properties().apply {
            setProperty("user", USER)
            setProperty("password", PASSWORD)
            extra.forEach { (k, v) -> setProperty(k, v) }
        }
        return DriverManager.getConnection(url, props)
    }

    /** A connection whose round trips [RoundTrips.count] counts. */
    fun counted(extra: Map<String, String> = emptyMap()): Connection =
        connect(extra + ("socketFactory" to CountingSocketFactory::class.java.name))
}

/** Round trips made through [CountingSocketFactory] sockets: the number of times the driver sent, then waited. */
object RoundTrips {
    private val trips = AtomicInteger()
    val value: Int get() = trips.get()
    internal fun add() = trips.incrementAndGet()

    fun <T> count(work: () -> T): Pair<T, Int> {
        val before = value
        val result = work()
        return result to (value - before)
    }
}

class CountingSocketFactory : SocketFactory() {
    override fun createSocket(): Socket = CountingSocket()
    override fun createSocket(host: String, port: Int): Socket = createSocket().apply { connect(InetSocketAddress(host, port)) }
    override fun createSocket(host: String, port: Int, localHost: InetAddress, localPort: Int): Socket = createSocket(host, port)
    override fun createSocket(host: InetAddress, port: Int): Socket = createSocket().apply { connect(InetSocketAddress(host, port)) }
    override fun createSocket(address: InetAddress, port: Int, localAddress: InetAddress, localPort: Int): Socket = createSocket(address, port)
}

/** Counts each switch from writing to reading: one request sent, one answer awaited. */
private class CountingSocket : Socket() {
    @Volatile private var wrote = false
    private var input: InputStream? = null
    private var output: OutputStream? = null

    private fun readStarts() {
        if (wrote) {
            wrote = false
            RoundTrips.add()
        }
    }

    @Synchronized
    override fun getInputStream(): InputStream = input ?: object : FilterInputStream(super.getInputStream()) {
        override fun read(): Int { readStarts(); return super.read() }
        override fun read(b: ByteArray, off: Int, len: Int): Int { readStarts(); return super.read(b, off, len) }
    }.also { input = it }

    @Synchronized
    override fun getOutputStream(): OutputStream = output ?: object : FilterOutputStream(super.getOutputStream()) {
        override fun write(b: Int) { wrote = true; out.write(b) }
        override fun write(b: ByteArray, off: Int, len: Int) { if (len > 0) wrote = true; out.write(b, off, len) }
    }.also { output = it }
}

/** Median of some millisecond timings, formatted. */
fun median(ms: List<Double>): String = "%.3f ms".format(ms.sorted()[ms.size / 2])

fun ms(nanos: Long): Double = nanos / 1_000_000.0
