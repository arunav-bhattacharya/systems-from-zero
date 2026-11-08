package sfz.shard.l03.demo

/**
 * Five nodes, 20 partitions of 220 requests a second each: 880 a second per node, against a capacity
 * of 1,000. At second 1, one merchant in partition 7 (on node-3) triples that partition's traffic.
 * A node over capacity answers health checks late, so the failure detector calls it dead.
 */
fun main() {
    val capacity = 1_000.0
    for (automatic in listOf(true, false)) {
        val load = MutableList(20) { 220.0 }
        val owner = MutableList(20) { "node-${it % 5 + 1}" }
        val alive = (1..5).map { "node-$it" }.toSortedSet()
        println(if (automatic) "automatic: move a dead node's partitions to the others" else "manual: alert a person, move nothing")
        for (second in 0..3) {
            if (second == 1) load[7] = 660.0 // the hot merchant
            val perNode = alive.associateWith { n -> owner.indices.filter { owner[it] == n }.sumOf { load[it] } }
            val served = perNode.values.sumOf { minOf(it, capacity) }
            println("  second $second: %s  served %,.0f of %,.0f a second".format(
                perNode.entries.joinToString(" ") { "${it.key}=%.0f".format(it.value) }.ifEmpty { "no nodes left" }, served, load.sum()))
            if (!automatic) continue
            val dead = perNode.filter { it.value > capacity }.keys
            alive -= dead
            if (alive.isEmpty()) continue
            // the "fix": hand every partition of a dead node to the least loaded survivor, one at a time
            for (p in owner.indices.filter { owner[it] in dead }) {
                owner[p] = alive.minBy { n -> owner.indices.filter { owner[it] == n }.sumOf { load[it] } }
            }
        }
    }
}
