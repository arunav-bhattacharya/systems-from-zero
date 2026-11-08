package sfz.msg.l05

/**
 * One record as a consumer saw it. [seq] is the order the producer sent it in: 0, 1, 2, ... across all keys.
 * [key] is null for a record sent without a key.
 */
data class Seen(val key: String?, val seq: Int, val partition: Int, val offset: Long)

/** Checks on what a consumer saw, and what a change of partition count does to keys. */
object KeyOrdering {
    /**
     * The keys whose records the consumer did not see in send order: somewhere a record of that key has a
     * smaller [Seen.seq] than an earlier record of the same key. An empty set means per-key order held.
     * Records without a key are ignored.
     */
    fun keysOutOfOrder(seen: List<Seen>): Set<String> {
        val lastSeq = HashMap<String, Int>()
        val broken = LinkedHashSet<String>()
        for (r in seen) {
            val key = r.key ?: continue
            val prev = lastSeq[key]
            if (prev != null && r.seq < prev) broken += key // this key went backwards
            lastSeq[key] = r.seq
        }
        return broken
    }

    /**
     * The first index `i` where `seen[i].seq < seen[i - 1].seq`, that is, where the consumer's order stops
     * matching the producer's send order. Returns -1 if the whole list is in send order.
     */
    fun firstGlobalBreak(seen: List<Seen>): Int =
        (1 until seen.size).firstOrNull { seen[it].seq < seen[it - 1].seq } ?: -1

    /** For each key, the partitions its records landed in. Records without a key are ignored. */
    fun partitionsByKey(seen: List<Seen>): Map<String, Set<Int>> =
        seen.filter { it.key != null }
            .groupBy({ it.key!! }, { it.partition })
            .mapValues { (_, partitions) -> partitions.toSortedSet() }

    /**
     * The keys that the default partitioner sends to a different partition once the topic grows from
     * [before] to [after] partitions. Use [KeyPartitioner.partitionFor].
     */
    fun movedKeys(keys: Collection<String>, before: Int, after: Int): Set<String> =
        keys.filterTo(LinkedHashSet()) { KeyPartitioner.partitionFor(it, before) != KeyPartitioner.partitionFor(it, after) }
}
