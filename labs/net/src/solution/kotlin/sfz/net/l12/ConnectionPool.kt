package sfz.net.l12

class PoolExhausted(message: String) : RuntimeException(message)

class ConnectionPool(
    private val maxSize: Int,
    private val idleTimeoutMs: Long,
    private val maxLifetimeMs: Long,
    private val clock: () -> Long,
    private val connect: () -> Connection,
) {
    data class Lease(val connection: Connection, val reused: Boolean)

    private val openedAt = HashMap<Int, Long>()                       // every open connection: id -> when it opened
    private val idleSince = ArrayDeque<Pair<Connection, Long>>()       // idle ones, newest last

    val open: Int
        get() = openedAt.size

    val idle: Int
        get() = idleSince.size

    fun acquire(): Lease {
        val now = clock()
        // evict first: an idle connection past either limit may already be dead on the other side
        idleSince.removeAll { (c, since) ->
            val stale = now - since >= idleTimeoutMs || now - openedAt.getValue(c.id) >= maxLifetimeMs
            if (stale) close(c)
            stale
        }
        idleSince.removeLastOrNull()?.let { (c, _) -> return Lease(c, reused = true) }   // LIFO: the warmest one
        if (openedAt.size >= maxSize) throw PoolExhausted("all $maxSize connections are in use")
        val c = connect()
        openedAt[c.id] = now
        return Lease(c, reused = false)
    }

    fun release(connection: Connection, healthy: Boolean) {
        val now = clock()
        val age = now - (openedAt[connection.id] ?: return)
        if (!healthy || age >= maxLifetimeMs) close(connection) else idleSince.addLast(connection to now)
    }

    private fun close(c: Connection) {
        c.close()
        openedAt.remove(c.id)
    }
}
