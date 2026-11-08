package sfz.shard.l02.demo

/** Jump consistent hash (Lamping and Veach, 2014): a key's bucket from 0 until [buckets], with no table at all. */
fun jumpHash(key: Long, buckets: Int): Int {
    var k = key
    var b = -1L
    var j = 0L
    while (j < buckets) {
        b = j
        k = k * 2862933555777941757L + 1 // a 64-bit linear congruential step: a new pseudo-random k
        j = ((b + 1) * ((1L shl 31).toDouble() / ((k ushr 33) + 1).toDouble())).toLong() // the next bucket this key jumps to
    }
    return b.toInt()
}

/** Rendezvous (highest random weight) hashing: score every node for this key and take the highest. */
fun rendezvous(key: String, nodes: List<String>): String = nodes.maxBy { position("$key|$it") }

/** A fifth node joins four. Which keys move, and where do they come from? */
fun main() {
    val four = listOf("node-A", "node-B", "node-C", "node-D")
    val five = four + "node-E"
    val keys = (0 until 100_000).map { "pay-$it" }

    // lesson 1's placement: node number hash mod S
    fun modOwner(key: String, nodes: List<String>) = nodes[Math.floorMod(position(key), nodes.size.toLong()).toInt()]
    val modMoved = keys.count { modOwner(it, four) != modOwner(it, five) }
    println("hash mod S, 4 -> 5 nodes: %,d of %,d keys move".format(modMoved, keys.size))

    for (t in listOf(1, 16)) {
        val before = ring(four, t)
        val after = ring(five, t)
        // the owner is the node of the first token at or after the key; past the top, wrap to the first
        fun owner(tokens: java.util.TreeMap<Long, String>, key: String) = (tokens.ceilingEntry(position(key)) ?: tokens.firstEntry()).value
        val moved = keys.filter { owner(before, it) != owner(after, it) }
        val gaveUp = moved.groupingBy { owner(before, it) }.eachCount().toSortedMap()
        println("ring, %2d token(s) per node: %,d keys move, all to node-E; given up by %s".format(t, moved.size, gaveUp))
    }

    // no ring: jump hash numbers the nodes 0 to 4, rendezvous scores all of them
    val jumpMoved = keys.filter { jumpHash(position(it), 4) != jumpHash(position(it), 5) }
    val jumpGaveUp = jumpMoved.groupingBy { four[jumpHash(position(it), 4)] }.eachCount().toSortedMap()
    println("jump hash:               %,d keys move, all to node-E; given up by %s".format(jumpMoved.size, jumpGaveUp))
    val hrwMoved = keys.filter { rendezvous(it, four) != rendezvous(it, five) }
    val hrwGaveUp = hrwMoved.groupingBy { rendezvous(it, four) }.eachCount().toSortedMap()
    println("rendezvous:              %,d keys move, all to node-E; given up by %s".format(hrwMoved.size, hrwGaveUp))
}
