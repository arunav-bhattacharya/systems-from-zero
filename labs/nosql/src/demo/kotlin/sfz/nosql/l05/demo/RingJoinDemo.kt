package sfz.nosql.l05.demo

/** A fifth node joins four. Which keys move, and where do they come from? */
fun main() {
    val four = listOf("node-A", "node-B", "node-C", "node-D")
    val keys = (0 until 100_000).map { "pay-$it" }

    // lesson 1's placement: node number hash mod S
    fun modOwner(key: String, nodes: List<String>) = nodes[Math.floorMod(position(key), nodes.size.toLong()).toInt()]
    val modMoved = keys.count { modOwner(it, four) != modOwner(it, four + "node-E") }
    println("hash mod S, 4 -> 5 nodes: %,d of %,d keys move".format(modMoved, keys.size))

    for (t in listOf(1, 16)) {
        val before = ring(four, t)
        val after = ring(four + "node-E", t)
        // the owner is the node of the first token at or after the key; past the top, wrap to the first
        fun owner(tokens: java.util.TreeMap<Long, String>, key: String) = (tokens.ceilingEntry(position(key)) ?: tokens.firstEntry()).value
        val moved = keys.filter { owner(before, it) != owner(after, it) }
        val gaveUp = moved.groupingBy { owner(before, it) }.eachCount().toSortedMap()
        println("ring, %2d token(s) per node: %,d keys move, all to node-E; given up by %s".format(t, moved.size, gaveUp))
    }
}
