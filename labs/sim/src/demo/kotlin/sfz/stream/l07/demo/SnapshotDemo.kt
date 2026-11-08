package sfz.stream.l07.demo

/**
 * The lab's job with aligned barriers and a transactional sink: two sources of 50 card records each, a keyed
 * counter, a checkpoint every 20 virtual ms. It crashes at 160 ms and restarts from the last completed checkpoint.
 */
fun main() {
    val inputs = listOf(List(50) { "card-${it % 3 + 1}" }, List(50) { "card-${it % 2 + 2}" })
    val job = Job(inputs, aligned = true, sink = { TransactionalSink(it) }, seed = 1).run(crashAt = 160)
    println("checkpoint  source offsets  counter state                          records counted")
    for (s in job.completed) {
        println("%-11d %-15s %-38s %d".format(s.id, s.offsets, s.counts.toSortedMap(), s.counts.values.sum()))
    }
    println("crashed at 160 ms; restarted from checkpoint ${job.restoredFrom}")
    println("finished at ${job.now} ms: ${job.external.size} updates written, ${job.duplicates()} duplicates")
    println("final counts ${job.finalCounts().toSortedMap()}, truth ${job.truth().toSortedMap()}")
}
