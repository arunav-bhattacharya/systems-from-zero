package sfz.shard.l03

import java.nio.ByteBuffer
import java.security.MessageDigest
import java.util.TreeMap

/** The first 8 bytes of MD5 as a signed Long: the same in every process. Given. */
fun hash64(key: String): Long = ByteBuffer.wrap(MessageDigest.getInstance("MD5").digest(key.toByteArray())).long

/** Which node holds a key. Every scheme in this lesson is one of these. */
interface Placement {
    fun ownerOf(key: String): String
}

/**
 * How many of [keys] change owner when [change] runs: each one is a key copied over the network
 * while the cluster keeps serving. Given.
 */
fun movedKeys(keys: List<String>, placement: Placement, change: () -> Unit): Int {
    val before = keys.map(placement::ownerOf)
    change()
    return keys.indices.count { placement.ownerOf(keys[it]) != before[it] }
}

/** Lesson 1's rule: node number `hash mod N`. Given. */
class ModN(initial: List<String>) : Placement {
    private val nodes = initial.toMutableList()
    override fun ownerOf(key: String): String = nodes[Math.floorMod(hash64(key), nodes.size.toLong()).toInt()]
    fun addNode(node: String) {
        nodes += node
    }
}

/** Lesson 2's ring: [tokensPerNode] tokens per node at `hash64("<node>#<i>")`. Given. */
class Ring(private val tokensPerNode: Int, initial: List<String>) : Placement {
    private val tokens = TreeMap<Long, String>()

    init {
        initial.forEach(::addNode)
    }

    override fun ownerOf(key: String): String = (tokens.ceilingEntry(hash64(key)) ?: tokens.firstEntry()).value
    fun addNode(node: String) {
        for (i in 0 until tokensPerNode) tokens[hash64("$node#$i")] = node
    }
}

/**
 * A fixed number of partitions, many more than nodes: Kafka partitions, Elasticsearch and OpenSearch
 * shards, Redis Cluster's 16,384 slots, Notion's 480 logical shards.
 *
 * A key's partition is `hash mod partitionCount` and never changes. What changes is the second map,
 * partition -> node. It starts round robin: partition p on `initial[p % initial.size]`.
 */
class FixedPartitions(val partitionCount: Int, initial: List<String>) : Placement {
    private val owner = Array(partitionCount) { initial[it % initial.size] }

    /** The nodes, in the order they joined. */
    val nodes: MutableList<String> = initial.toMutableList()

    /** Given. */
    fun partitionOf(key: String): Int = Math.floorMod(hash64(key), partitionCount.toLong()).toInt()

    /** Given. */
    override fun ownerOf(key: String): String = owner[partitionOf(key)]

    /** The partitions [node] holds, lowest first. Given. */
    fun partitionsOf(node: String): List<Int> = owner.indices.filter { owner[it] == node }

    /**
     * Adds [node] and moves whole partitions to it until it holds `partitionCount / nodes.size`
     * (rounded down, counting the new node). Each move takes the highest-numbered partition of the
     * node that holds the most partitions right now (on a tie, the node whose name sorts first).
     * Returns the partitions moved, in the order they moved. If there are more nodes than partitions,
     * the new node gets nothing.
     */
    fun addNode(node: String): List<Int> {
        nodes += node
        val target = partitionCount / nodes.size // the new node's fair share, rounded down
        val counts = nodes.associateWith { 0 }.toMutableMap()
        owner.forEach { counts.merge(it, 1, Int::plus) }
        val moved = mutableListOf<Int>()
        while (counts.getValue(node) < target) {
            // the busiest donor gives up one partition; the data of that partition is copied, nothing else
            val donor = counts.entries.filter { it.key != node }
                .maxWith(compareBy<Map.Entry<String, Int>> { it.value }.thenByDescending { it.key }).key
            val p = owner.indices.last { owner[it] == donor }
            owner[p] = node
            counts.merge(donor, -1, Int::plus)
            counts.merge(node, 1, Int::plus)
            moved += p
        }
        return moved
    }
}
