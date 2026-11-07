package sfz.nosql.l05

import java.nio.ByteBuffer
import java.security.MessageDigest
import java.util.TreeMap

/**
 * A consistent-hash ring with virtual nodes, the way Dynamo and Cassandra place keys.
 *
 * The ring is every 64-bit number, from `Long.MIN_VALUE` up to `Long.MAX_VALUE`, and then it wraps
 * around. [position] puts any text on it. Each physical node owns [tokensPerNode] positions
 * (tokens, also called virtual nodes) at `position("<node>#0")`, `position("<node>#1")`, and so on.
 * A key belongs to the node owning the first token at or after the key's position, walking
 * upward (clockwise) and wrapping past the top.
 *
 * Your job: [addNode], [ownerOf] and [preferenceList]. Everything else is given.
 */
class HashRing(val tokensPerNode: Int) {
    init {
        require(tokensPerNode >= 1) { "every node needs at least one token" }
    }

    /** token position -> physical node. Sorted, so "the first token at or after x" is one lookup. */
    private val tokens = TreeMap<Long, String>()

    /** The physical nodes on the ring. Given. */
    val nodes: Set<String> get() = tokens.values.toSortedSet()

    /** How many tokens the ring holds in all. Given. */
    val tokenCount: Int get() = tokens.size

    /** Puts [tokensPerNode] tokens for [node] on the ring, at `position("$node#$i")` for i = 0, 1, ... */
    fun addNode(node: String) {
        TODO("put tokensPerNode tokens on the ring, at position(\"<node>#<i>\")")
    }

    /** Takes every token of [node] off the ring. Its keys fall to the next tokens clockwise. Given. */
    fun removeNode(node: String) {
        tokens.values.removeIf { it == node }
    }

    /**
     * The node that owns [key]: the owner of the first token at or after `position(key)`.
     * If no token is at or after it, wrap around to the smallest token.
     */
    fun ownerOf(key: String): String {
        TODO("the owner of the first token at or after position(key), wrapping to the first token")
    }

    /**
     * The [n] DISTINCT physical nodes that store [key], in ring order: the owner first, then the
     * owners of the next tokens clockwise, skipping a node that is already on the list (with
     * virtual nodes, the next token often belongs to a node you already have). Wraps around.
     * If the ring has fewer than [n] nodes, returns all of them.
     */
    fun preferenceList(key: String, n: Int): List<String> {
        TODO("walk clockwise from the key, collect n distinct nodes")
    }

    /** The share of the ring (0.0 to 1.0) each node owns: the gaps before its tokens, summed. Given. */
    fun ownership(): Map<String, Double> {
        if (tokens.isEmpty()) return emptyMap()
        val share = HashMap<String, Double>()
        var previous = tokens.lastKey() // the first token's gap starts at the last token, across the wrap
        for ((token, node) in tokens) {
            // unsigned difference: the gap is right even when it crosses from MAX_VALUE to MIN_VALUE
            val gap = (token - previous).toULong().toDouble() / RING_SIZE
            share[node] = (share[node] ?: 0.0) + if (tokens.size == 1) 1.0 else gap
            previous = token
        }
        return share
    }

    companion object {
        /** 2^64 positions, as a Double. */
        const val RING_SIZE = 18446744073709551616.0

        /** Where [text] sits on the ring: the first 8 bytes of its MD5 hash, as a signed Long. Given. */
        fun position(text: String): Long =
            ByteBuffer.wrap(MessageDigest.getInstance("MD5").digest(text.toByteArray())).long

        /** Lesson 1's placement, for comparison: node number `hash mod S`. Given. */
        fun modOwner(key: String, nodes: List<String>): String =
            nodes[Math.floorMod(position(key), nodes.size.toLong()).toInt()]
    }
}
