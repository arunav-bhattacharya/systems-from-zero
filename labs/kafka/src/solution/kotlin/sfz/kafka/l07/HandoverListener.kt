package sfz.kafka.l07

import org.apache.kafka.clients.consumer.Consumer
import org.apache.kafka.clients.consumer.ConsumerRebalanceListener
import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.OffsetAndMetadata
import org.apache.kafka.common.TopicPartition

/** One callback the group made: which partitions it handed to this consumer, or took away. */
data class RebalanceEvent(val kind: Kind, val partitions: Set<TopicPartition>) {
    enum class Kind { ASSIGNED, REVOKED, LOST }
}

/**
 * A rebalance listener that hands each partition over cleanly: when the group takes a partition away, it commits
 * how far this consumer got, so the next owner starts exactly there. Pass it to `subscribe(topics, listener)`.
 *
 * Kafka calls the three callbacks on the polling thread, inside `poll`, so the listener may use [consumer] there.
 * The poll loop calls [processed] after it has finished each record. It never commits anything else.
 */
class HandoverListener(private val consumer: Consumer<String, String>) : ConsumerRebalanceListener {
    /** Every callback, in the order Kafka made them, including calls with an empty set. */
    val events = mutableListOf<RebalanceEvent>()

    // per partition: the next offset to read, once everything before it is processed
    private val done = mutableMapOf<TopicPartition, Long>()

    /** Called by the poll loop after [record] is fully processed. */
    fun processed(record: ConsumerRecord<String, String>) {
        done[TopicPartition(record.topic(), record.partition())] = record.offset() + 1 // next to read
    }

    /**
     * The partitions are leaving this consumer, and it still owns them. Record a REVOKED event, then commit
     * (`commitSync`) the next offset to read of every revoked partition that has processed records, and forget them.
     */
    override fun onPartitionsRevoked(partitions: Collection<TopicPartition>) {
        events += RebalanceEvent(RebalanceEvent.Kind.REVOKED, partitions.toSet())
        val offsets = partitions.mapNotNull { tp -> done.remove(tp)?.let { tp to OffsetAndMetadata(it) } }.toMap()
        if (offsets.isNotEmpty()) consumer.commitSync(offsets) // the bookmark the next owner will start from
    }

    /** New partitions for this consumer. Record an ASSIGNED event. The consumer starts at the committed offsets. */
    override fun onPartitionsAssigned(partitions: Collection<TopicPartition>) {
        events += RebalanceEvent(RebalanceEvent.Kind.ASSIGNED, partitions.toSet())
    }

    /**
     * The group already gave these partitions to someone else (this consumer was thrown out). Record a LOST event
     * and forget their offsets without committing: a commit now could move the new owner's bookmark.
     */
    override fun onPartitionsLost(partitions: Collection<TopicPartition>) {
        events += RebalanceEvent(RebalanceEvent.Kind.LOST, partitions.toSet())
        partitions.forEach { done.remove(it) } // no commit: these are not ours any more
    }
}
