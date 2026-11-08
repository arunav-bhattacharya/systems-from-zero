package sfz.cons.l01.demo

/**
 * Lesson cons-01: a serializable database can still return stale data.
 *   ./gradlew :sim:demo -Pmain=sfz.cons.l01.demo.SnapshotDemoKt -q
 *   ./gradlew :sim:demo -Pmain=sfz.cons.l01.demo.SnapshotDemoKt -Pargs=5 -q     the follower 5 ms behind
 *
 * The leader runs write transactions one at a time, so they are serializable by construction.
 * Read-only transactions run on a consistent snapshot, either on the leader or on a follower that
 * applies each commit some milliseconds late (50 by default).
 */
fun main(args: Array<String>) {
    val lag = args.firstOrNull()?.toLong() ?: 50
    run("read-only transactions on a follower ($lag ms behind)", lag)
    run("read-only transactions on the leader", 0)
}

private class Txn(val name: String, val start: Long, val end: Long, val writes: Map<String, Int> = emptyMap()) {
    var reads: Map<String, Int?> = emptyMap()
    val readOnly get() = writes.isEmpty()
}

private fun run(title: String, lagMs: Long) {
    val txns = listOf(
        Txn("T1 setup", 0, 5, mapOf("balance" to 100)),
        Txn("T2 checkout", 20, 30, mapOf("balance" to 70, "pay-7" to 2)),
        Txn("T3 ledger", 60, 70),
        Txn("T4 ledger", 100, 110),
    )
    // a read-only transaction sees every commit that reached its replica before it started
    for (t in txns.filter { it.readOnly }) {
        val state = mutableMapOf<String, Int?>()
        txns.filter { !it.readOnly && it.end + lagMs <= t.start }.sortedBy { it.end }.forEach { state.putAll(it.writes) }
        t.reads = listOf("balance", "pay-7").associateWith { state[it] }
    }
    println(title)
    for (t in txns) {
        val what = if (t.readOnly) "reads  " + t.reads.entries.joinToString(", ") { "${it.key}=${show(it.key, it.value)}" }
        else "writes " + t.writes.entries.joinToString(", ") { "${it.key}=${show(it.key, it.value)}" }
        println("  %-12s %3d-%-3d  %s".format(t.name, t.start, t.end, what))
    }
    val serial = serialOrder(txns, respectRealTime = false)
    val strict = serialOrder(txns, respectRealTime = true)
    println("  serializable: " + (serial?.let { "yes, as " + it.joinToString(", ") { t -> t.name.substringBefore(' ') } } ?: "no"))
    println("  strict serializable (the order must also respect real time): " + if (strict != null) "yes" else "no")

    // the same story for one key, as single reads and writes, through the lab's classifier
    val h = history {
        for (t in txns) {
            if (t.readOnly) t.name.substringAfter(' ').read("balance", t.reads["balance"], t.start.toInt()..t.end.toInt())
            else t.writes["balance"]?.let { t.name.substringAfter(' ').write("balance", it, t.start.toInt()..t.end.toInt()) }
        }
    }
    val got = classify(h)
    println("  key balance on its own: linearizable ${yes(Model.LINEARIZABLE in got)}, sequential ${yes(Model.SEQUENTIAL in got)}")
    println()
}

private fun yes(b: Boolean) = if (b) "yes" else "no"

/** pay-7 holds a status code: 2 is captured. A dash means the row isn't there. */
private fun show(key: String, v: Int?) = when {
    v == null -> "-"
    key == "pay-7" && v == 2 -> "captured"
    else -> v.toString()
}

/** A serial order of the transactions in which each read-only one sees exactly what it saw, if one exists. */
private fun serialOrder(txns: List<Txn>, respectRealTime: Boolean): List<Txn>? {
    fun permutations(left: List<Txn>): Sequence<List<Txn>> =
        if (left.isEmpty()) sequenceOf(emptyList())
        else left.asSequence().flatMap { t -> permutations(left - t).map { listOf(t) + it } }
    return permutations(txns).firstOrNull { order ->
        val okTime = !respectRealTime || order.indices.all { i -> (i + 1 until order.size).none { j -> order[j].end < order[i].start } }
        val state = mutableMapOf<String, Int?>()
        okTime && order.all { t ->
            val matches = !t.readOnly || t.reads.all { (k, v) -> state[k] == v }
            state.putAll(t.writes)
            matches
        }
    }
}
