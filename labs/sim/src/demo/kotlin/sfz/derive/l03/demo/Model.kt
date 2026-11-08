package sfz.derive.l03.demo

import kotlin.random.Random

/*
 * A copy of the derive-03 lab with the reference answers filled in, so the demos run on their own.
 */

/** How much of the pipeline removes duplicates. Each variant includes the ones before it. */
enum class Variant {
    /** Nothing removes duplicates. */
    NONE,

    /** Plus TCP-style sequence numbers within one connection. */
    TRANSPORT,

    /** Plus the broker's idempotent producer and exactly-once inside the broker. */
    BROKER,

    /** Plus a request id made on the phone, carried to the ledger and kept unique there. */
    END_TO_END,
}

/** The chance of each fault, per event. */
data class Rates(
    /** The network delivers one request twice on the same connection (a retransmission). */
    val duplicatePacket: Double = 0.02,
    /** The server did the work, and the response never reached the phone, which times out and retries. */
    val lostResponse: Double = 0.03,
    /** The broker appended the record, and its ack to the producer was lost, so the producer resends. */
    val lostAck: Double = 0.02,
    /** The consumer wrote the ledger row, then died before committing its offset, so it gets the record again. */
    val consumerCrash: Double = 0.015,
)

/**
 * Which fault hits which event. Each decision is a hash of the seed, the kind of fault and the
 * event's name ("i17/a2" for the second attempt of transfer 17), so it doesn't depend on the order
 * code asks, or on how many other events happened. The same seed gives the same faults in every
 * variant.
 */
class Faults(private val seed: Long, val rates: Rates = Rates()) {
    private fun hit(kind: String, key: String, rate: Double): Boolean =
        Random(seed * 31 + "$kind/$key".hashCode()).nextDouble() < rate

    fun duplicatePacket(intent: Int, attempt: Int) = hit("dup", "i$intent/a$attempt", rates.duplicatePacket)
    fun lostResponse(intent: Int, attempt: Int) = hit("resp", "i$intent/a$attempt", rates.lostResponse)
    fun lostAck(trace: String) = hit("ack", trace, rates.lostAck)
    fun consumerCrash(trace: String, delivery: Int) = hit("crash", "$trace/d$delivery", rates.consumerCrash)
}

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

/*
 * The whole path from the phone to the ledger, with the faults injected at each hop:
 *
 *   phone --HTTP--> server --produce--> broker --consume--> ledger
 */

val ACCOUNTS: List<String> = (1..20).map { "acc-%02d".format(it) }
const val OPENING_CENTS = 10_000_000L

/** The API server: one connection per attempt, then a producer that writes to the broker. */
class Server(private val variant: Variant, private val faults: Faults, private val broker: Broker) : Endpoint {
    private var connections = 0
    private val producerId = 1L
    private var nextSeq = 0L

    override fun call(request: Request, intent: Int, attempt: Int): Boolean {
        val connection = Connection(connections++)                 // a retry opens a new connection
        val copies = if (faults.duplicatePacket(intent, attempt)) 2 else 1
        for (copy in 0 until copies) {
            val delivered = if (variant >= Variant.TRANSPORT) connection.receive(0, request) else request
            if (delivered != null) produce(delivered, "i$intent/a$attempt/c$copy")
        }
        return !faults.lostResponse(intent, attempt)               // false: the phone times out
    }

    private fun produce(request: Request, trace: String) {
        val seq = nextSeq++
        broker.append(producerId, seq, request, trace)
        // the ack was lost: the producer resends the same batch, same producer id, same sequence
        if (faults.lostAck(trace)) broker.append(producerId, seq, request, "$trace/resend")
    }
}

/**
 * The consumer: reads the broker in order, writes the ledger, then commits its offset. A crash
 * between the write and the commit means the record is delivered again. With [Variant.BROKER]
 * the broker's exactly-once covers the offset commit and anything written back to the broker,
 * but the ledger is another system, so the row written before the crash stays.
 */
class Consumer(private val variant: Variant, private val broker: Broker, private val ledger: Ledger, private val faults: Faults) {
    var committed = 0L
        private set
    private val deliveries = HashMap<Long, Int>()

    fun drain(now: Long) {
        while (committed < broker.end) {
            val r = broker.get(committed)
            val n = deliveries.merge(r.offset, 1, Int::plus)!!
            val row = Row(r.request.requestId, r.request.from, r.request.to, r.request.cents)
            if (variant == Variant.END_TO_END) ledger.postOnce(row, now) else ledger.post(row)
            if (faults.consumerCrash(r.trace, n)) continue          // died before the commit: again
            committed++
        }
    }
}

/** What one run produced. Every transfer the user asked for should be exactly one row. */
data class Result(val variant: Variant, val transfers: Int, val rows: Int, val askedCents: Long, val movedCents: Long) {
    val duplicates: Int get() = rows - transfers
    val extraCents: Long get() = movedCents - askedCents
}

object Pipeline {
    /**
     * [transfers] users each tap "send" once, one second apart, through the whole path with the
     * faults of [seed]. Request ids are req-000001, req-000002 ... (a UUIDv7 in real life).
     */
    fun run(variant: Variant, seed: Long, transfers: Int = 1_000, rates: Rates = Rates()): Result {
        val faults = Faults(seed, rates)
        val broker = Broker(idempotent = variant >= Variant.BROKER)
        val ledger = Ledger(ACCOUNTS.associateWith { OPENING_CENTS })
        val server = Server(variant, faults, broker)
        val consumer = Consumer(variant, broker, ledger, faults)
        var ids = 0
        val phone = Phone({ "req-%06d".format(++ids) })
        val random = Random(seed)
        var asked = 0L
        for (i in 0 until transfers) {
            val from = ACCOUNTS[random.nextInt(ACCOUNTS.size)]
            val to = ACCOUNTS.filter { it != from }[random.nextInt(ACCOUNTS.size - 1)]
            val cents = 100 + random.nextLong(99_900)
            asked += cents
            phone.send(server, i, from, to, cents)
            consumer.drain(now = i * 1_000L)
        }
        return Result(variant, transfers, ledger.rows.size, asked, ledger.rows.sumOf { it.cents })
    }
}
