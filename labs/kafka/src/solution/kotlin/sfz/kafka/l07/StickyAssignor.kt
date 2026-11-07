package sfz.kafka.l07

import org.apache.kafka.common.TopicPartition

/**
 * A balanced, sticky assignor: the idea behind the classic `CooperativeStickyAssignor` and the broker's
 * `uniform` assignor in the new protocol. It balances the group, and moves as few partitions as it can.
 */
object StickyAssignor {
    private val order = compareBy<TopicPartition>({ it.topic() }, { it.partition() })

    /**
     * Assigns every partition in [partitions] to exactly one of [members] so that
     *
     * 1. the group is balanced: every member gets `partitions / members` or one more, and
     * 2. as many partitions as possible stay with the member that owned them in [previous].
     *
     * [previous] may name members that have left and partitions that no longer exist; ignore both. Return one entry
     * per member (an empty list if it gets nothing), each list sorted by topic, then partition.
     * For the same input, always return the same output.
     */
    fun assign(
        members: List<String>,
        partitions: List<TopicPartition>,
        previous: Map<String, List<TopicPartition>>,
    ): Map<String, List<TopicPartition>> {
        val sorted = members.sorted()
        val existing = partitions.toSet()

        // what each remaining member owned and could keep (a partition counts for its first owner only)
        val claimed = mutableSetOf<TopicPartition>()
        val kept = sorted.associateWith { m ->
            previous[m].orEmpty().filter { it in existing }.sortedWith(order).filter { claimed.add(it) }
        }

        // quotas: everyone gets base, and `extra` members get one more. Give the extra slots to the members
        // that owned the most, so they have to give up the least.
        val base = partitions.size / sorted.size
        val extra = partitions.size % sorted.size
        val quota = sorted.sortedWith(compareByDescending<String> { kept.getValue(it).size }.thenBy { it })
            .withIndex().associate { (i, m) -> m to base + if (i < extra) 1 else 0 }

        // each member keeps what fits in its quota; everything else goes back into the pile
        val result = sorted.associateWith { m -> kept.getValue(m).take(quota.getValue(m)).toMutableList() }
        val owned = result.values.flatten().toSet()
        val pile = partitions.filter { it !in owned }.sortedWith(order).toMutableList()

        // fill the members that still have room, in id order
        for (m in sorted) {
            while (result.getValue(m).size < quota.getValue(m)) result.getValue(m) += pile.removeAt(0)
        }
        return result.mapValues { (_, ps) -> ps.sortedWith(order) }
    }

    /**
     * What each member has to give up when the group moves from [previous] to [next]: the partitions it owned and
     * no longer owns. Members that lose nothing map to an empty set. Under the eager protocol every member gives up
     * everything instead; this is what the cooperative protocols revoke.
     */
    fun toRevoke(
        previous: Map<String, List<TopicPartition>>,
        next: Map<String, List<TopicPartition>>,
    ): Map<String, Set<TopicPartition>> =
        previous.mapValues { (m, owned) -> owned.toSet() - next[m].orEmpty().toSet() }
}
