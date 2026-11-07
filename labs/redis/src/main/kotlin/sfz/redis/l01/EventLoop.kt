package sfz.redis.l01

/** A command a client sent, and the tick at which its bytes reached the server. */
data class Sent(val client: String, val args: List<String>, val arrivedAt: Long)

/** What the loop sent back for one command. All times are ticks of the loop's clock. */
data class Reply(
    val client: String,
    val command: String,
    val value: String,
    val arrivedAt: Long,
    val startedAt: Long,
    val finishedAt: Long,
) {
    /** How long the client waited, from its bytes arriving to the reply being ready. */
    val latency: Long get() = finishedAt - arrivedAt
}

/**
 * A model of Redis's main thread: one loop that runs every client's commands, one at a time.
 *
 * Time is counted in ticks. `SET`, `GET` and `INCR` take 1 tick each. `SLOW n` stands in for
 * a long Lua script or a `KEYS *` on a big keyspace: it takes `n` ticks, and nothing else runs
 * while it does.
 */
class EventLoop {
    private val store = HashMap<String, String>()
    private val clients = mutableListOf<String>()   // in the order they first connected
    private val pending = mutableListOf<Sent>()     // every command not yet answered, in send order

    /** The loop's clock, in ticks. */
    var clock = 0L
        private set

    /** Client [client] sends [args]. Its bytes reach the server at tick [at]. */
    fun send(client: String, at: Long, vararg args: String) {
        val last = pending.lastOrNull { it.client == client }
        require(last == null || last.arrivedAt <= at) { "a client's bytes arrive in the order it sent them" }
        if (client !in clients) clients += client
        pending += Sent(client, args.toList(), at)
    }

    /**
     * Runs until every command has been answered. Returns the replies in the order the loop
     * produced them.
     *
     * Work the way Redis's event loop does:
     * 1. If no pending command has arrived yet (none with `arrivedAt <= clock`), move [clock]
     *    forward to the earliest arrival. The real loop sleeps in `epoll_wait` here.
     * 2. Otherwise take a snapshot of the pending commands that have arrived. That is one pass.
     * 3. Visit the clients in [clients] order. For each one, run its arrived commands in the
     *    order it sent them. Run each to completion with [execute], remove it from [pending],
     *    and record a [Reply] (startedAt is the clock before [execute], finishedAt after it).
     * 4. Commands that arrive during the pass wait for the next pass. Go back to step 1.
     */
    fun runUntilIdle(): List<Reply> {
        TODO("lesson 1 lab: write the event loop described above")
    }

    /** Runs one command against the store and moves the clock forward by its cost. Done for you. */
    private fun execute(args: List<String>): String {
        val name = args[0].uppercase()
        clock += if (name == "SLOW") args[1].toLong() else 1L
        return when (name) {
            "SET" -> { store[args[1]] = args[2]; "OK" }
            "GET" -> store[args[1]] ?: "(nil)"
            "INCR" -> ((store[args[1]]?.toLong() ?: 0L) + 1).toString().also { store[args[1]] = it }
            "SLOW" -> "OK"
            else -> "ERR unknown command '${args[0]}'"
        }
    }
}
