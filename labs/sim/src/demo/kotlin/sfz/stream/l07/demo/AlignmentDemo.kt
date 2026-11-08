package sfz.stream.l07.demo

/**
 * The same job, with and without barrier alignment, over 30 seeds (30 different interleavings), each crashing at
 * 160 ms. Counts snapshots that hold records past their own offsets, runs whose final counts are too high, and the
 * time inputs spent blocked while the counter aligned.
 */
fun main() {
    val inputs = listOf(List(50) { "card-${it % 3 + 1}" }, List(50) { "card-${it % 2 + 2}" })
    println("alignment  snapshots  inconsistent  runs overcounting  blocked ms per run")
    for (aligned in listOf(true, false)) {
        var snapshots = 0
        var inconsistent = 0
        var overcounting = 0
        var blocked = 0L
        for (seed in 1L..30) {
            val job = Job(inputs, aligned, sink = { AppendSink(it) }, seed = seed).run(crashAt = 160)
            snapshots += job.completed.size
            inconsistent += job.completed.count { it.counts.values.sum() != it.offsets.sum() }
            if (job.finalCounts().any { (k, n) -> n > job.truth().getValue(k) }) overcounting++
            blocked += job.blockedMs
        }
        println("%-10s %-10d %-13d %-18s %.1f".format(if (aligned) "on" else "off", snapshots, inconsistent,
            "$overcounting of 30", blocked / 30.0))
    }
}
