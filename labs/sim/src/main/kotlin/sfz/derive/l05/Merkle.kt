package sfz.derive.l05

import java.nio.ByteBuffer

/**
 * A Merkle tree over a key-value view, cut into [leaves] key ranges (a power of two).
 *
 * The tree is stored as an array, like a binary heap: `nodes[1]` is the root, node `i` has the
 * children `2i` and `2i + 1`, and the leaves are `nodes[leaves]` to `nodes[2 * leaves - 1]`.
 * Leaf `k` is the hash of every entry whose key falls in range `k` (finished, see [leafHash]).
 * Every other node is the hash of its two children.
 */
class MerkleTree(view: Map<String, Long>, val leaves: Int = 1_024) {
    init {
        require(leaves > 0 && leaves and (leaves - 1) == 0) { "leaves must be a power of two" }
    }

    val nodes: Array<ByteArray> = Array(2 * leaves) { ByteArray(0) }

    init {
        val buckets = Array(leaves) { sortedMapOf<String, Long>() }
        for ((k, v) in view) buckets[leafOf(k, leaves)][k] = v
        for (i in 0 until leaves) nodes[leaves + i] = leafHash(buckets[i])
        buildInternalNodes()
    }

    val root: ByteArray get() = nodes[1]

    /**
     * Exercise 3. Fill in every internal node, from the bottom up: for `i` from `leaves - 1` down
     * to 1, `nodes[i] = sha256(nodes[2i], nodes[2i + 1])`. Bottom up, because a parent needs its
     * children first.
     */
    private fun buildInternalNodes() {
        TODO("hash each pair of children into their parent, from leaves - 1 down to the root at 1")
    }

    companion object {
        /** Which key range a key falls in: the first 4 bytes of SHA-256(key), modulo [leaves]. */
        fun leafOf(key: String, leaves: Int): Int =
            Math.floorMod(ByteBuffer.wrap(sha256(key.toByteArray())).int, leaves)

        /** The hash of one range: SHA-256 over "key=value\n" for each entry, in key order. An empty range hashes "" . */
        fun leafHash(entries: Map<String, Long>): ByteArray =
            sha256(entries.entries.joinToString("") { "${it.key}=${it.value}\n" }.toByteArray())
    }
}

/** The result of comparing two trees: the ranges that differ, and how many node pairs were compared. */
data class MerkleDiff(val leaves: List<Int>, val comparisons: Int)

/**
 * Exercise 4. Find the key ranges where [a] and [b] differ, without looking at every range.
 *
 * Start at the root. Compare the node in both trees (count one comparison). If the hashes are
 * equal, everything below is equal: stop. If they differ and the node is a leaf, record its range
 * number (`node - leaves`). Otherwise descend into both children. Return the ranges in increasing
 * order. Both trees must have the same number of leaves.
 */
fun compare(a: MerkleTree, b: MerkleTree): MerkleDiff {
    require(a.leaves == b.leaves) { "trees must have the same shape" }
    TODO("descend from the root, only into nodes whose hashes differ, counting each comparison")
}
