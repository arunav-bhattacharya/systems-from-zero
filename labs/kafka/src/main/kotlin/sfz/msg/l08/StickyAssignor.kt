package sfz.msg.l08

import org.apache.kafka.common.TopicPartition

/**
 * A balanced, sticky assignor: the idea behind the classic `CooperativeStickyAssignor` and the broker's
 * `uniform` assignor in the new protocol. It balances the group, and moves as few partitions as it can.
 */
object StickyAssignor {
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
        TODO("keep what each member owned up to its quota (give the +1 slots to the biggest owners), then deal out the rest")
    }

    /**
     * What each member has to give up when the group moves from [previous] to [next]: the partitions it owned and
     * no longer owns. Members that lose nothing map to an empty set. Under the eager protocol every member gives up
     * everything instead; this is what the cooperative protocols revoke.
     */
    fun toRevoke(
        previous: Map<String, List<TopicPartition>>,
        next: Map<String, List<TopicPartition>>,
    ): Map<String, Set<TopicPartition>> {
        TODO("for each member in previous: what it owned minus what it owns in next")
    }
}
