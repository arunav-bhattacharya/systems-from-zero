package sfz.derive.l03

import kotlin.random.Random

/*
 * Lesson derive-03 (given, nothing to change in this file): the whole path from the phone to the
 * ledger, with the faults injected at each hop.
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
