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

    /** Delivers [request] the first time [seq] arrives on this connection; a repeat returns null. */
    fun receive(seq: Long, request: Request): Request? {
        if (seq <= highestDelivered) return null                  // a retransmitted copy: drop it
        highestDelivered = seq
        return request
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

    /** Appends a record and returns its offset; an idempotent broker appends each (producer, sequence) once. */
    fun append(producerId: Long, seq: Long, request: Request, trace: String): Long {
        if (idempotent) appended[producerId to seq]?.let { return it }   // a resend of a batch we have
        val r = Record(records.size.toLong(), request, trace)
        records += r
        appended[producerId to seq] = r.offset
        return r.offset
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

    /** Inserts the request id and posts the row in one step, once per request id. */
    fun postOnce(row: Row, now: Long): Boolean {
        if (row.requestId in seen) return false                   // the unique index says no
        seen[row.requestId] = now                                 // same transaction as the money
        post(row)
        return true
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
    /** Sends transfer number [intent] and returns the request ids it sent, one per attempt. */
    fun send(server: Endpoint, intent: Int, from: String, to: String, cents: Long): List<String> {
        val id = newId()                                          // one id per tap, made where the intent is
        val sent = ArrayList<String>()
        for (attempt in 1..maxAttempts) {
            sent += id
            if (server.call(Request(id, from, to, cents), intent, attempt)) break
        }
        return sent
    }
}
