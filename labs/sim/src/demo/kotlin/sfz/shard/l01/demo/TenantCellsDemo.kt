package sfz.shard.l01.demo

/** 1,000 merchants on 10 cells. Sizes follow a Zipf curve: the k-th biggest sends 1/k as much as the biggest. */
fun main() {
    val total = 20_000.0 // payments a second, all merchants together
    val harmonic = (1..1_000).sumOf { 1.0 / it }
    val merchants = (1..1_000).associate { k -> "T-%04d".format(k) to total / (k * harmonic) }
    val cells = 10

    // the thin router's rule: hash the tenant id mod the cell count
    val byHash = merchants.keys.associateWith { Math.floorMod(md5(it), cells.toLong()).toInt() }

    // size-aware: tenants over 2,000 a second get a cell alone; the rest go biggest first to the emptiest shared cell
    val bySize = LinkedHashMap<String, Int>()
    val loads = DoubleArray(cells)
    var nextDedicated = 0
    for ((id, rate) in merchants.entries.sortedByDescending { it.value }) {
        val cell = if (rate >= 2_000.0) nextDedicated++ else (nextDedicated until cells).minBy { loads[it] }
        bySize[id] = cell
        loads[cell] += rate
    }

    println("T-0001 alone sends %.0f payments a second, %.1f%% of all".format(merchants.getValue("T-0001"), merchants.getValue("T-0001") / total * 100))
    for ((name, placement) in listOf("hash of tenant id" to byHash, "size-aware" to bySize)) {
        val perCell = DoubleArray(cells).also { l -> placement.forEach { (id, c) -> l[c] += merchants.getValue(id) } }
        val home = placement.getValue("T-0001")
        val neighbours = placement.count { (id, c) -> c == home && id != "T-0001" }
        println(name)
        println("  payments a second per cell: ${perCell.map { "%.0f".format(it) }}")
        println("  T-0001 is in cell $home with $neighbours other merchants")
        println("  a bad deploy to cell $home hits %.1f%% of payments; to the quietest cell, %.1f%%"
            .format(perCell[home] / total * 100, perCell.min() / total * 100))
    }
}
