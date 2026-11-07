package sfz.bigdata.l02.demo

import kotlin.random.Random

/**
 * A word count on three "nodes", printed phase by phase: map, partition, shuffle, reduce.
 * Run it with -Pargs=combine to add a combiner to each map task.
 */
fun main(args: Array<String>) {
    val combine = "combine" in args
    val splits = listOf(
        "approved declined approved",      // block 1, stored on node A
        "approved refunded approved",      // block 2, on node B
        "declined approved refunded",      // block 3, on node C
    )
    val reducers = 3
    fun partition(key: String) = (key.hashCode() and Int.MAX_VALUE) % reducers   // Hadoop's HashPartitioner

    // map: each node turns its own block into (word, 1) pairs, optionally combined
    val mapOutputs = splits.map { line ->
        val pairs = line.split(" ").map { it to 1 }
        if (combine) pairs.groupingBy { it.first }.fold(0) { s, p -> s + p.second }.toList() else pairs
    }
    mapOutputs.forEachIndexed { i, out ->
        println("map ${"ABC"[i]}:    " + out.joinToString(" ") { (k, v) -> "($k,$v)->r${partition(k)}" })
    }

    // shuffle: reducer r pulls partition r from every map node, then sorts by key
    val buckets = (0 until reducers).map { r -> mapOutputs.flatten().filter { partition(it.first) == r }.sortedBy { it.first } }
    buckets.forEachIndexed { r, b -> println("reduce $r gets: " + b.joinToString(" ") { (k, v) -> "($k,$v)" }) }
    val records = buckets.sumOf { it.size }
    val bytes = buckets.flatten().sumOf { it.first.length + 4 }
    println("shuffled: $records records, $bytes bytes")

    // reduce: one sum per key
    val output = buckets.flatMap { b -> b.groupBy({ it.first }, { it.second }).map { (k, vs) -> "$k=${vs.sum()}" } }
    println("output:   " + output.joinToString(", "))

    if (combine) atScale()
}

/** The same shuffle arithmetic on 20 map tasks of 50,000 events each, with and without a combiner. */
private fun atScale() {
    val rnd = Random(1)
    val statuses = listOf("approved", "declined", "refunded", "captured", "reversed")
    // key = status: five distinct keys per map task
    val byStatus = List(20) { List(50_000) { statuses[rnd.nextInt(statuses.size)] } }
    // key = payment id: every key is new
    val byPayment = List(20) { task -> List(50_000) { i -> "pay-%07d".format(task * 50_000 + i) } }
    for ((name, tasks) in listOf("count by status    " to byStatus, "count by payment id" to byPayment)) {
        val plain = tasks.flatten()                                  // one record per event
        val combined = tasks.flatMap { it.distinct() }               // one record per key per map task
        println("%s  without combiner: %,9d records %,10d bytes   with: %,9d records %,10d bytes".format(
            name, plain.size, plain.sumOf { it.length + 4 }, combined.size, combined.sumOf { it.length + 4 }))
    }
}
