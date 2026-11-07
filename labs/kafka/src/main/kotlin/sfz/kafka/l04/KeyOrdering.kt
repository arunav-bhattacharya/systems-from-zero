package sfz.kafka.l04

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
        TODO("remember the last seq per key; a key whose seq goes down is out of order")
    }

    /**
     * The first index `i` where `seen[i].seq < seen[i - 1].seq`, that is, where the consumer's order stops
     * matching the producer's send order. Returns -1 if the whole list is in send order.
     */
    fun firstGlobalBreak(seen: List<Seen>): Int {
        TODO("compare each record's seq with the one before it")
    }

    /** For each key, the partitions its records landed in. Records without a key are ignored. */
    fun partitionsByKey(seen: List<Seen>): Map<String, Set<Int>> {
        TODO("group the keyed records by key and collect their partitions")
    }

    /**
     * The keys that the default partitioner sends to a different partition once the topic grows from
     * [before] to [after] partitions. Use [KeyPartitioner.partitionFor].
     */
    fun movedKeys(keys: Collection<String>, before: Int, after: Int): Set<String> {
        TODO("keep the keys whose partition for `before` differs from their partition for `after`")
    }
}
