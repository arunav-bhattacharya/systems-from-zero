package sfz.nosql.l05.demo

import java.nio.ByteBuffer
import java.security.MessageDigest
import java.util.TreeMap

/** Where text lands on a ring of 2^64 positions: the first 8 bytes of its MD5. */
fun position(text: String): Long = ByteBuffer.wrap(MessageDigest.getInstance("MD5").digest(text.toByteArray())).long

/** A ring with [tokensPerNode] tokens for each node: token position -> node. */
fun ring(nodes: List<String>, tokensPerNode: Int): TreeMap<Long, String> {
    val tokens = TreeMap<Long, String>()
    for (node in nodes) for (i in 0 until tokensPerNode) tokens[position("$node#$i")] = node
    return tokens
}

/** Each node's share of the ring: the gap before each of its tokens, summed. */
fun shares(tokens: TreeMap<Long, String>): Map<String, Double> {
    val share = sortedMapOf<String, Double>()
    var previous = tokens.lastKey()
    for ((token, node) in tokens) {
        share[node] = (share[node] ?: 0.0) + (token - previous).toULong().toDouble() / 18446744073709551616.0
        previous = token
    }
    return share
}

/** Six nodes, the same names as lesson 1's demo. How even is the ring with 1, 4, 16, 64 and 256 tokens each? */
fun main() {
    val nodes = listOf("node-A", "node-B", "node-C", "node-D", "node-E", "node-F")
    println("one token per node:")
    shares(ring(nodes, 1)).forEach { (node, share) -> println("  %s owns %5.1f%%".format(node, share * 100)) }
    println("tokens per node   smallest share   largest share   largest / fair (16.7%)")
    for (t in listOf(1, 4, 16, 64, 256)) {
        val s = shares(ring(nodes, t)).values
        println("%15d   %13.1f%%   %12.1f%%   %20.2f".format(t, s.min() * 100, s.max() * 100, s.max() * nodes.size))
    }
}
