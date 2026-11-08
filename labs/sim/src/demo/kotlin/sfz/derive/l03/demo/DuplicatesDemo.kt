package sfz.derive.l03.demo

/**
 * Try it, derive-03 section 3: the same faults, four amounts of duplicate suppression.
 *
 * 1,000 transfers through phone, server, broker, consumer and ledger. Faults per event: 2% of
 * requests repeated on their connection, 3% of responses lost (the phone retries), 2% of broker
 * acks lost (the producer resends), 1.5% consumer crashes between the ledger write and the offset
 * commit. Pass a seed to see another run: -Pargs=7
 */
fun main(args: Array<String>) {
    val seed = args.firstOrNull()?.toLong() ?: 2026
    println("%-11s %16s %16s".format("variant", "duplicate rows", "extra money"))
    for (v in Variant.entries) {
        val r = Pipeline.run(v, seed)
        println("%-11s %16d %16s".format(v, r.duplicates, "%,.2f".format(r.extraCents / 100.0)))
    }
}
