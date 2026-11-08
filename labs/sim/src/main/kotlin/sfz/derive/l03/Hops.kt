package sfz.derive.l03

/*
 * Lesson derive-03. Each class here is one hop's own duplicate suppression. Every one of them
 * works, and every one of them stops at its own edge.
 */

/** A transfer the user asked for, as the phone sends it. [requestId] travels through every hop. */
data class Request(val requestId: String, val from: String, val to: String, val cents: Long)

/**
 * One TCP-style connection. The sender numbers what it sends on this connection (0, 1, 2 ...),
 * and the receiver delivers each number once, however often the network repeats it.
 */
class Connection(val id: Int) {
    private var highestDelivered = -1L

    /**
     * TODO: deliver [request] (return it) the first time sequence number [seq] arrives on this
     * connection. A copy of a number this connection already delivered returns null. The
     * sequence numbers belong to this connection only; a new connection starts from nothing.
     */
    fun receive(seq: Long, request: Request): Request? {
        TODO("deliver each sequence number once")
    }
}

/** A record in the broker's log. [trace] names the event that produced it, for the fault plan. */
data class Record(val offset: Long, val request: Request, val trace: String)

/**
 * The broker's log. With [idempotent] on, it behaves like Kafka's idempotent producer: it
 * remembers, per producer id, which sequence numbers it has appended, so a producer that resends
 * a batch after a lost ack doesn't create a second record.
 */
class Broker(private val idempotent: Boolean) {
    private val records = ArrayList<Record>()
    private val appended = HashMap<Pair<Long, Long>, Long>()   // (producer id, sequence) -> offset

    /**
     * TODO: append a record for [request] and return its offset. When [idempotent] is on and
     * this ([producerId], [seq]) pair was appended before, append nothing and return the offset
     * it got the first time. When it is off, append every time.
     */
    fun append(producerId: Long, seq: Long, request: Request, trace: String): Long {
        TODO("append, unless an idempotent broker has seen this producer and sequence")
    }

    fun get(offset: Long): Record = records[offset.toInt()]

    val end: Long get() = records.size.toLong()
}

/** One ledger row: one movement of money. */
data class Row(val requestId: String, val from: String, val to: String, val cents: Long)

/**
 * The final write: the ledger table plus the balances it moves. [seen] plays the part of a
 * `UNIQUE (request_id)` index: request id to the time its row was inserted.
 */
class Ledger(opening: Map<String, Long>) {
    val rows = ArrayList<Row>()
    private val balances = HashMap(opening)
    private val seen = HashMap<String, Long>()

    fun balance(account: String): Long = balances[account] ?: 0

    /** A plain insert (given): one more row, money moves. What every variant but END_TO_END does. */
    fun post(row: Row) {
        rows += row
        balances.merge(row.from, -row.cents, Long::plus)
        balances.merge(row.to, row.cents, Long::plus)
    }

    /**
     * TODO: the end-to-end write. In one step (one database transaction in real life): if
     * [row]'s request id is already in [seen], do nothing and return false. Otherwise record it
     * in [seen] with [now], [post] the row, and return true. In SQL this is
     * `INSERT ... ON CONFLICT (request_id) DO NOTHING` and moving the money only if a row went in.
     */
    fun postOnce(row: Row, now: Long): Boolean {
        TODO("insert the request id and the row together, once")
    }

    /** Forgets request ids inserted before [olderThan] (given). Real tables prune to stay small. */
    fun prune(olderThan: Long) {
        seen.values.removeIf { it < olderThan }
    }

    /** How many request ids the unique index holds now. */
    val remembered: Int get() = seen.size
}

/** Something the phone can send a request to. Returns true when the response reached the phone. */
fun interface Endpoint {
    fun call(request: Request, intent: Int, attempt: Int): Boolean
}

/**
 * The phone. The user taps "send" once; the phone tries up to [maxAttempts] times, on a new
 * connection each time, until a response arrives. [newId] makes a fresh request id.
 */
class Phone(private val newId: () -> String, private val maxAttempts: Int = 3) {
    /**
     * Sends transfer number [intent] and returns the request ids it sent, one per attempt.
     *
     * TODO: this version makes a new id for every attempt, so the server can't tell a retry from
     * a new transfer. Make one id per tap and send that same id on every attempt.
     */
    fun send(server: Endpoint, intent: Int, from: String, to: String, cents: Long): List<String> {
        val sent = ArrayList<String>()
        for (attempt in 1..maxAttempts) {
            val id = newId()
            sent += id
            if (server.call(Request(id, from, to, cents), intent, attempt)) break
        }
        return sent
    }
}
