package sfz.stream.l06

import org.apache.kafka.streams.Topology

/**
 * Why a join needs both inputs partitioned the same way, and the check Kafka Streams runs at start-up.
 *
 * Kafka Streams runs a join inside a task, and task N reads partition N of every input topic of its subtopology.
 * An order and its customer's tier meet only if the producers put them in the same partition number.
 */
object CoPartitioning {

    /** The partition Kafka's Java producer picks for a record with this key: murmur2 of the UTF-8 bytes, made
     * positive, modulo the partition count (the Messaging track's lesson on keys and partitions).
     * `org.apache.kafka.common.utils.Utils` has `murmur2(bytes)` and `toPositive(int)`. */
    @JvmStatic
    fun partitionFor(key: String, partitions: Int): Int {
        TODO("toPositive(murmur2(UTF-8 bytes of key)) % partitions")
    }

    /** The share of [keys] that land on a different partition number in a topic with [a] partitions than in a topic
     * with [b] partitions. Each of those keys' orders would meet no tier in a partitioned join. */
    @JvmStatic
    fun mismatchShare(keys: List<String>, a: Int, b: Int): Double {
        TODO("count the keys whose partitionFor(key, a) != partitionFor(key, b), divided by keys.size")
    }

    /**
     * The start-up check: in every subtopology, all source topics must have the same partition count, because a
     * subtopology that reads two topics joins them task by task. Global tables are not in any subtopology, so they
     * are never checked. Throws [IllegalStateException] whose message names each topic with its count, such as
     * `not co-partitioned: customer-tiers=2, orders=3`.
     *
     * `topology.describe().subtopologies()` lists the subtopologies; each has `nodes()`, and the nodes that are
     * `TopologyDescription.Source` have `topicSet()`.
     */
    @JvmStatic
    fun requireCoPartitioned(topology: Topology, partitions: Map<String, Int>) {
        TODO("for each subtopology: source topics -> partition counts; throw if the counts differ")
    }
}
