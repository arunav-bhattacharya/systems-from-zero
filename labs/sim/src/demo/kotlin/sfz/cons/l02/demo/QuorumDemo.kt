package sfz.cons.l02.demo

/**
 * Lesson cons-02: record 1,000 histories from each store (3 clients, 10 operations each, one key) and
 * check them. Then show the first bad quorum history around the read the checker could not place.
 *   ./gradlew :sim:demo -Pmain=sfz.cons.l02.demo.QuorumDemoKt -q
 */
fun main() {
    val stores: List<Pair<String, (Network) -> Store>> = listOf(
        "single leader, reads at the leader" to { n -> SingleLeaderStore(n) },
        "single leader, reads at the follower" to { n -> SingleLeaderStore(n, followerReads = true) },
        "quorum n=3 w=2 r=2" to { n -> QuorumStore(n) },
        "quorum n=3 w=2 r=2, sync read repair" to { n -> QuorumStore(n, syncReadRepair = true) },
    )
    val seeds = 1L..1_000L
    println("%-38s %16s %14s".format("store", "bad histories", "mean read ms"))
    for ((name, store) in stores) {
        var bad = 0
        var readMs = 0L
        var reads = 0
        for (seed in seeds) {
            val h = record(seed, store = store)
            if (!check(h).linearizable) bad++
            h.ops.filter { it.kind == Kind.READ }.forEach { readMs += it.end - it.start; reads++ }
        }
        println("%-38s %10d of %d %14.1f".format(name, bad, seeds.count(), readMs.toDouble() / reads))
    }
    val seed = seeds.first { !check(record(it) { n -> QuorumStore(n) }).linearizable }
    val h = record(seed) { n -> QuorumStore(n) }
    val prefix = check(h).order.toSet()
    val stuck = h.ops.filter { it !in prefix }.minBy { it.start }
    println()
    println("seed $seed, the operations around ${stuck.process}'s read at ${stuck.start} ms (the checker's first unplaceable op):")
    val near = h.ops.filter { it.end >= stuck.start - 40 && it.start <= stuck.end }
    val seenValues = near.filter { it.kind == Kind.READ }.mapNotNull { it.value }.toSet()
    val window = h.ops.filter { it in near || (it.kind == Kind.WRITE && it.value in seenValues) }
    val t0 = window.minOf { it.start }
    for (op in window) {
        val bar = " ".repeat(((op.start - t0) / 2).toInt()) + "=".repeat(((op.end - op.start) / 2 + 1).toInt())
        println("  %4d-%-4d %-3s %-16s %s".format(op.start, op.end, op.process, op.toString().substringAfter(':').substringBefore('@'), bar))
    }
}
