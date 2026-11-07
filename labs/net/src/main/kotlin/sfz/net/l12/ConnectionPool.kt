package sfz.net.l12

/** Thrown by [ConnectionPool.acquire] when every connection is in use and no more may be opened. */
class PoolExhausted(message: String) : RuntimeException(message)

/**
 * A client-side connection pool, single-threaded for the lab. Time comes from [clock] in ms;
 * [connect] opens a new connection (a TCP and maybe TLS handshake in real life).
 *
 * - At most [maxSize] connections are open at once, in use or idle.
 * - An idle connection unused for [idleTimeoutMs] or more is closed, never reused. Set this below
 *   the idle timeout of every hop in front of you (load balancer, NAT, server).
 * - A connection [maxLifetimeMs] old or older is closed when it comes back or is found idle, so
 *   new connections pick up DNS changes and spread over new backends.
 */
class ConnectionPool(
    private val maxSize: Int,
    private val idleTimeoutMs: Long,
    private val maxLifetimeMs: Long,
    private val clock: () -> Long,
    private val connect: () -> Connection,
) {
    /** A connection handed out, and whether it came from the pool rather than a fresh connect. */
    data class Lease(val connection: Connection, val reused: Boolean)

    /** Connections open now, in use or idle. */
    val open: Int
        get() = TODO("count every connection not yet closed")

    /** Idle connections waiting in the pool. */
    val idle: Int
        get() = TODO("count the idle ones")

    /**
     * First close every idle connection that has been idle too long or lived too long. Then hand out
     * the most recently released idle connection (it is the least likely to be stale), or open a new
     * one if fewer than [maxSize] are open, or throw [PoolExhausted].
     */
    fun acquire(): Lease {
        TODO("evict, then reuse the newest idle connection, or connect, or throw")
    }

    /**
     * The caller is done with [connection]. If it is not [healthy] (anything but a status came back),
     * or it has reached [maxLifetimeMs], close it. Otherwise it goes back to the pool, idle from now.
     */
    fun release(connection: Connection, healthy: Boolean) {
        TODO("close it, or park it with the time it went idle")
    }
}
