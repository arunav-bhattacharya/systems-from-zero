package sfz.nosql.l09.demo

/** A PN-Counter: per-replica slots of increments and of decrements. Merge takes each slot's maximum. */
private data class PN(val p: Map<String, Long> = emptyMap(), val n: Map<String, Long> = emptyMap()) {
    fun add(r: String, by: Long) = if (by >= 0) copy(p = p + (r to (p[r] ?: 0) + by)) else copy(n = n + (r to (n[r] ?: 0) - by))
    val value get() = p.values.sum() - n.values.sum()
    fun merge(o: PN) = PN(maxed(p, o.p), maxed(n, o.n))
    private fun maxed(a: Map<String, Long>, b: Map<String, Long>) = (a.keys + b.keys).associateWith { maxOf(a[it] ?: 0, b[it] ?: 0) }
}

/** An OR-Set: element -> tags of its adds, plus the tags removed. Merge is two unions. */
private data class OR(val adds: Map<String, Set<String>> = emptyMap(), val removed: Set<String> = emptySet()) {
    fun add(e: String, tag: String) = copy(adds = adds + (e to (adds[e].orEmpty() + tag)))
    fun remove(e: String) = copy(removed = removed + adds[e].orEmpty())
    val elements get() = adds.filterValues { tags -> tags.any { it !in removed } }.keys.sorted()
    fun merge(o: OR) = OR((adds.keys + o.adds.keys).associateWith { adds[it].orEmpty() + o.adds[it].orEmpty() }, removed + o.removed)
}

/** Every order in which three copies can be merged, by name. */
private fun <T> orders(copies: Map<String, T>, merge: (T, T) -> T): List<Pair<String, T>> {
    val n = copies.keys.toList()
    val perms = listOf(listOf(0, 1, 2), listOf(0, 2, 1), listOf(1, 0, 2), listOf(1, 2, 0), listOf(2, 0, 1), listOf(2, 1, 0))
    return perms.map { p -> p.joinToString(" + ") { n[it] } to p.map { copies.getValue(n[it]) }.reduce(merge) }
}

/**
 * Three regions are cut off from each other. Each keeps taking writes: the merchant's pending-payout
 * counter and its blocked-card set. Then the partition heals and the copies merge, in every order.
 */
fun main() {
    // the state every region had before the partition
    val counter0 = PN().add("eu", 5)
    val blocked0 = OR().add("card-4417", "eu:1").add("card-9921", "eu:2")

    // during the partition, each region edits its own copy
    val counters = mapOf(
        "eu" to counter0.add("eu", 3).add("eu", -2), // 3 payouts queued, 2 paid
        "us" to counter0.add("us", 4),               // 4 queued
        "ap" to counter0.add("ap", -1),              // 1 paid
    )
    val sets = mapOf(
        "eu" to blocked0.remove("card-4417"),                           // eu unblocks card-4417
        "us" to blocked0.add("card-4417", "us:1").add("card-5310", "us:2"), // us reports it again, and blocks another
        "ap" to blocked0.remove("card-9921"),                           // ap unblocks card-9921
    )
    counters.forEach { (r, c) -> println("$r sees pending payouts = ${c.value}") }
    sets.forEach { (r, s) -> println("$r sees blocked cards = ${s.elements}") }

    println("after the partition heals:")
    for ((order, c) in orders(counters, PN::merge)) println("  merge $order -> pending payouts = ${c.value}")
    for ((order, s) in orders(sets, OR::merge)) println("  merge $order -> blocked cards = ${s.elements}")
}
