package sfz.msg.l08

import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.MockConsumer
import org.apache.kafka.clients.consumer.OffsetAndMetadata
import org.apache.kafka.common.TopicPartition
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import java.time.Duration

/**
 * The listener against MockConsumer, which plays the group coordinator: `rebalance(newAssignment)` calls
 * onPartitionsRevoked with what this consumer loses and onPartitionsAssigned with what it gains, and
 * `losePartitions(lost)` calls onPartitionsLost, as when the consumer was thrown out of the group.
 */
class HandoverListenerTest {
    private val ps = (0 until 6).map { TopicPartition("payments", it) }

    /** A MockConsumer that remembers every commit (its committed() reports 0 for partitions it no longer owns). */
    private class RecordingConsumer : MockConsumer<String, String>("earliest") {
        val commits = mutableListOf<Map<TopicPartition, OffsetAndMetadata>>()

        override fun commitSync(offsets: Map<TopicPartition, OffsetAndMetadata>) {
            commits += offsets
            super.commitSync(offsets)
        }
    }

    /** A consumer subscribed with a HandoverListener and given all six partitions, each holding offsets 0 to 4. */
    private fun setUp(): Pair<RecordingConsumer, HandoverListener> {
        val c = RecordingConsumer()
        val listener = HandoverListener(c)
        c.subscribe(listOf("payments"), listener)
        c.rebalance(ps)
        c.updateBeginningOffsets(ps.associateWith { 0L })
        for (tp in ps) for (o in 0L until 5) c.addRecord(ConsumerRecord("payments", tp.partition(), o, "acct-${tp.partition()}", "pay-$o"))
        return c to listener
    }

    /** Every offset committed so far, by partition number; a later commit replaces an earlier one. */
    private fun RecordingConsumer.committedOffsets(): Map<Int, Long> =
        commits.fold(emptyMap()) { all, commit -> all + commit.map { (tp, om) -> tp.partition() to om.offset() } }

    private fun HandoverListener.nonEmpty() = events.filter { it.partitions.isNotEmpty() }

    @Test
    fun `revoking a partition commits the next offset to read, and only for the partitions that leave`() {
        val (c, listener) = setUp()
        c.poll(Duration.ofMillis(10)).forEach(listener::processed)   // offsets 0..4 of every partition, all processed

        c.rebalance(ps.take(3))                                       // the group takes away partitions 3, 4 and 5

        assertThat(c.committedOffsets()).isEqualTo(mapOf(3 to 5L, 4 to 5L, 5 to 5L))
        assertThat(listener.nonEmpty()).containsExactly(
            RebalanceEvent(RebalanceEvent.Kind.ASSIGNED, ps.toSet()),
            RebalanceEvent(RebalanceEvent.Kind.REVOKED, ps.drop(3).toSet()),
        )
    }

    @Test
    fun `only processed records count, so a record that was polled but not finished is read again`() {
        val (c, listener) = setUp()
        val records = c.poll(Duration.ofMillis(10)).records(ps[5])
        records.take(2).forEach(listener::processed)                  // offsets 0 and 1 done, 2..4 not yet

        c.rebalance(ps.take(5))

        assertThat(c.committedOffsets()).isEqualTo(mapOf(5 to 2L))    // the next owner starts at offset 2
    }

    @Test
    fun `a partition revoked before anything was processed commits nothing`() {
        val (c, listener) = setUp()
        c.rebalance(ps.take(3))
        assertThat(c.committedOffsets()).isEmpty()
        assertThat(listener.nonEmpty().last()).isEqualTo(RebalanceEvent(RebalanceEvent.Kind.REVOKED, ps.drop(3).toSet()))
    }

    @Test
    fun `lost partitions are recorded but never committed, even later`() {
        val (c, listener) = setUp()
        c.poll(Duration.ofMillis(10)).forEach(listener::processed)

        c.losePartitions(ps.drop(4))                                  // the group already gave 4 and 5 to someone else
        c.rebalance(emptyList())                                      // later, everything else is revoked

        assertThat(listener.nonEmpty()[1]).isEqualTo(RebalanceEvent(RebalanceEvent.Kind.LOST, ps.drop(4).toSet()))
        assertThat(c.committedOffsets()).isEqualTo((0 until 4).associateWith { 5L }) // 4 and 5 were not committed
    }
}
