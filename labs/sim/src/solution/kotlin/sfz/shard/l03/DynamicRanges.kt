package sfz.shard.l03

import java.util.TreeMap
import java.util.TreeSet

/**
 * Key ranges that split as they grow, the way HBase splits regions, MongoDB splits chunks and
 * CockroachDB splits ranges. The store starts as ONE range that covers every key, on [firstNode].
 * Real stores split on bytes (HBase at 10 GiB, CockroachDB at 512 MiB; MongoDB's balancer works in ranges of 128 MB); this one
 * splits when a range holds more than [maxKeys] keys.
 */
class DynamicRanges(val maxKeys: Int, firstNode: String) : Placement {
    init {
        require(maxKeys >= 2) { "a range must be able to hold two keys before it splits" }
    }

    /** One range: every key k with `start <= k` and below the next range's start. Its keys and its node. */
    class Range(val start: String, var node: String) {
        val keys = TreeSet<String>()
    }

    /** start key -> range. The first range starts at "", which is below every other string. */
    private val byStart = TreeMap<String, Range>().apply { put("", Range("", firstNode)) }

    /** Every range in key order. Given. */
    val ranges: List<Range> get() = byStart.values.toList()

    /** The range that holds [key]: the one with the greatest start <= key. Given. */
    fun rangeOf(key: String): Range = byStart.floorEntry(key).value

    /** Given. */
    override fun ownerOf(key: String): String = rangeOf(key).node

    /**
     * Stores [key] in its range. If the range now holds more than [maxKeys] keys, split it in two at
     * its median key, the one at index `size / 2` in sorted order: the lower half keeps the old start,
     * the upper half starts AT the median key and holds it and every key above it. Both halves stay on
     * the same node (a split moves no data between machines; only rebalancing does).
     */
    fun insert(key: String) {
        val range = rangeOf(key)
        range.keys += key
        if (range.keys.size <= maxKeys) return
        val median = range.keys.elementAt(range.keys.size / 2)
        val upper = Range(median, range.node)
        val moving = range.keys.tailSet(median, true) // a view: copy it before removing
        upper.keys += moving
        moving.clear()
        byStart[median] = upper
    }

    /**
     * Adds [node] and moves whole ranges to it, the same rule as [FixedPartitions.addNode]: until the
     * new node holds `ranges / nodes` (rounded down), take the last range of the node with the most
     * ranges (ties: the name that sorts first). Returns how many ranges moved. Given.
     */
    fun addNode(node: String): Int {
        val nodes = (ranges.map { it.node } + node).toSortedSet()
        val target = ranges.size / nodes.size
        var moved = 0
        while (ranges.count { it.node == node } < target) {
            val counts = ranges.groupingBy { it.node }.eachCount()
            val donor = nodes.filter { it != node }.maxWith(compareBy<String> { counts[it] ?: 0 }.thenByDescending { it })
            ranges.last { it.node == donor }.node = node
            moved++
        }
        return moved
    }
}
