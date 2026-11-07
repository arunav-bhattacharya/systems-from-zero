package sfz.sql.support

import java.io.FilterInputStream
import java.io.FilterOutputStream
import java.io.InputStream
import java.io.OutputStream
import java.net.InetAddress
import java.net.Socket
import java.sql.Connection
import java.sql.DriverManager
import java.util.Properties
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger
import javax.net.SocketFactory

/**
 * Counts network round trips between pgJDBC and the server, for lesson 14.
 *
 * A round trip is one exchange: the driver sends one or more messages, then waits for the
 * answer. The driver opens its socket through [CountingSocketFactory] (the `socketFactory`
 * connection property), and the socket counts every switch from writing to reading. A query is
 * one round trip; a loop of 1,000 inserts is 1,000; a batch of 1,000 is a few.
 *
 * ```
 * roundTrips {
 *     val n = count { insertPayments(conn, rows) }   // round trips made by the block
 * }
 * ```
 */
fun roundTrips(block: RoundTripTx.() -> Unit): Unit {
    val counter = RoundTripCounter.create()
    DriverManager.getConnection(CourseDb.jdbcUrl, counter.properties()).use { conn ->
        conn.createStatement().use { it.execute("SET TIME ZONE 'UTC'") }
        conn.autoCommit = false
        try {
            conn.createStatement().use { it.execute("SET LOCAL statement_timeout = '20s'") }
            RoundTripTx(conn, counter).block()
        } finally {
            conn.rollback()
        }
    }
}

/** One open transaction on a connection whose round trips are counted. Everything is rolled back. */
class RoundTripTx(val conn: Connection, private val counter: RoundTripCounter) {
    val tx = Tx(conn)

    /** Runs [work] and returns how many round trips it made. */
    fun count(work: () -> Unit): Int {
        val before = counter.value
        work()
        return counter.value - before
    }
}

/** A named counter that [CountingSocketFactory] finds through the connection properties. */
class RoundTripCounter private constructor(val id: String) {
    private val trips = AtomicInteger()
    val value: Int get() = trips.get()

    internal fun add() = trips.incrementAndGet()

    /** Connection properties that make pgJDBC open its socket through a counting socket. */
    fun properties(): Properties = Properties().apply {
        setProperty("user", CourseDb.username)
        setProperty("password", CourseDb.password)
        setProperty("socketFactory", CountingSocketFactory::class.java.name)
        setProperty(PROPERTY, id)
    }

    /** The same two properties for a HikariConfig: `config.addDataSourceProperty(k, v)` for each. */
    fun dataSourceProperties(): Map<String, String> =
        mapOf("socketFactory" to CountingSocketFactory::class.java.name, PROPERTY to id)

    companion object {
        const val PROPERTY = "sfzRoundTripCounter"
        private val all = ConcurrentHashMap<String, RoundTripCounter>()

        fun create(): RoundTripCounter = RoundTripCounter(UUID.randomUUID().toString()).also { all[it.id] = it }

        internal fun find(id: String?): RoundTripCounter? = id?.let { all[it] }
    }
}

/**
 * The socket factory pgJDBC instantiates by class name. pgJDBC passes the connection's
 * Properties to this constructor, which is how a socket finds its counter.
 */
class CountingSocketFactory(props: Properties) : SocketFactory() {
    private val counter = RoundTripCounter.find(props.getProperty(RoundTripCounter.PROPERTY))

    override fun createSocket(): Socket = CountingSocket(counter)
    override fun createSocket(host: String, port: Int): Socket = createSocket().apply { connect(java.net.InetSocketAddress(host, port)) }
    override fun createSocket(host: String, port: Int, localHost: InetAddress, localPort: Int): Socket = createSocket(host, port)
    override fun createSocket(host: InetAddress, port: Int): Socket = createSocket().apply { connect(java.net.InetSocketAddress(host, port)) }
    override fun createSocket(address: InetAddress, port: Int, localAddress: InetAddress, localPort: Int): Socket = createSocket(address, port)
}

/** A socket that counts each time the driver starts reading after it has written something. */
private class CountingSocket(private val counter: RoundTripCounter?) : Socket() {
    @Volatile private var wrote = false
    private var input: InputStream? = null
    private var output: OutputStream? = null

    private fun readStarts() {
        if (wrote) {
            wrote = false
            counter?.add()
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

/**
 * Statements the server executed, from pg_stat_statements: the sum of `calls` over every
 * statement whose text starts with [prefix] (case-insensitive), since the last [resetStatements].
 */
fun statementsRun(prefix: String): Long = CourseDb.connect().use { c ->
    c.prepareStatement("SELECT coalesce(sum(calls), 0) FROM pg_stat_statements WHERE query ILIKE ? || '%'").use { ps ->
        ps.setString(1, prefix)
        ps.executeQuery().use { it.next(); it.getLong(1) }
    }
}

/** Empties pg_stat_statements, so [statementsRun] counts from now. */
fun resetStatements() {
    CourseDb.connect().use { c -> c.createStatement().use { it.execute("SELECT pg_stat_statements_reset()") } }
}
