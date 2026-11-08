package sfz.stream.l07.demo

/**
 * Four setups, 30 seeds each, every run crashing at 160 ms. For each: the updates the outside world received, how
 * many of them were duplicates, the runs that ended with wrong counts, and the alert emails sent. The counter sends
 * an email (a side effect outside the job) whenever a card's count reaches 10. Three cards, so 3 emails is right.
 */
fun main() {
    val inputs = listOf(List(50) { "card-${it % 3 + 1}" }, List(50) { "card-${it % 2 + 2}" })
    val sinks = listOf("append" to { out: MutableList<Update> -> AppendSink(out) as Sink },
        "transactional" to { out: MutableList<Update> -> TransactionalSink(out) as Sink })
    println("alignment  sink           updates written  duplicates  runs with wrong counts  emails sent")
    for (aligned in listOf(true, false)) for ((name, sink) in sinks) {
        var written = 0
        var duplicates = 0
        var wrong = 0
        var emails = 0
        for (seed in 1L..30) {
            val job = Job(inputs, aligned, sink, seed = seed, sideEffect = { if (it.count == 10) emails++ }).run(crashAt = 160)
            written += job.external.size
            duplicates += job.duplicates()
            if (job.finalCounts() != job.truth()) wrong++
        }
        println("%-10s %-14s %-16s %-11d %-23s %d".format(if (aligned) "on" else "off", name, "$written (of 3000)",
            duplicates, "$wrong of 30", emails))
    }
    println("(30 runs: 3,000 records, and 90 emails would be one per card per run)")
}
