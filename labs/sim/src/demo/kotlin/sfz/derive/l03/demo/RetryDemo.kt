package sfz.derive.l03.demo

/**
 * Try it, derive-03 section 1: one transfer of 45.00, one lost response.
 *
 * The phone sends the transfer, the server commits it, and the response is lost on the way back.
 * The phone times out and sends it again on a new connection. Run 1 has no end-to-end request id
 * (a new id per attempt, as many apps do); run 2 makes one id per tap and the ledger keeps it
 * unique.
 */
fun main() {
    for (variant in listOf(Variant.BROKER, Variant.END_TO_END)) {
        val faults = Faults(seed = 1, rates = Rates(0.0, 0.0, 0.0, 0.0))
        val broker = Broker(idempotent = true)
        val ledger = Ledger(mapOf("acc-01" to 100_000L, "acc-02" to 0L))
        val server = Server(variant, faults, broker)
        val consumer = Consumer(variant, broker, ledger, faults)
        var ids = 0
        val oneIdPerTap = variant == Variant.END_TO_END
        val lostFirst = Endpoint { r, intent, attempt ->
            server.call(r, intent, attempt)                     // the server does the work...
            attempt > 1                                         // ...and the first response is lost
        }
        val sent = ArrayList<String>()
        val firstId = "req-%06d".format(++ids)
        for (attempt in 1..3) {
            val id = if (oneIdPerTap || attempt == 1) firstId else "req-%06d".format(++ids)
            sent += id
            if (lostFirst.call(Request(id, "acc-01", "acc-02", 4_500), 0, attempt)) break
        }
        consumer.drain(now = 0)
        println(if (oneIdPerTap) "one request id per tap, UNIQUE (request_id) in the ledger:" else "a new request id per attempt, no unique check:")
        println("  attempts sent: ${sent.size}, ids ${sent.joinToString()}")
        println("  records in the broker: ${broker.end}")
        for (row in ledger.rows) println("  ledger row: ${row.requestId} ${row.from} -> ${row.to} %.2f".format(row.cents / 100.0))
        println("  acc-01 %.2f -> %.2f, moved %.2f".format(1000.0, ledger.balance("acc-01") / 100.0, (100_000 - ledger.balance("acc-01")) / 100.0))
    }
}
