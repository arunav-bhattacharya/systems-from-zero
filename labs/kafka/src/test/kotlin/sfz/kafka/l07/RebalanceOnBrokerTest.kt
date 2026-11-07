package sfz.kafka.l07

import org.apache.kafka.clients.consumer.ConsumerConfig
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import sfz.kafka.l07.RebalanceEvent.Kind.ASSIGNED
import sfz.kafka.l07.RebalanceEvent.Kind.REVOKED
import sfz.kafka.support.KafkaSupport
import java.time.Duration
import java.util.UUID

/**
 * A real group on a Kafka 4.4 broker grows from one consumer to three on a 6-partition topic, once with the new
 * protocol and once with the classic eager one. Your listener records what moved and hands each partition over.
 * The poll loop never commits: the only commits are the ones your listener makes when a partition leaves.
 */
class RebalanceOnBrokerTest {
    companion object {
        @JvmStatic
        @BeforeAll
        fun startBroker() = KafkaSupport.start()
    }

    /** One member of the group: a consumer, your listener, and a shared log of every record it processed. */
    private class Member(name: String, config: Map<String, Any>, topic: String, private val processed: MutableList<String>) : AutoCloseable {
        // client.id c1, c2, c3: the classic protocol sorts members by id, so c1 gets the first range
        val consumer: KafkaConsumer<String, String> = KafkaSupport.consumer(config + (ConsumerConfig.CLIENT_ID_CONFIG to name))
        val listener = HandoverListener(consumer)

        init {
            consumer.subscribe(listOf(topic), listener)
        }

        fun pollOnce() {
            for (r in consumer.poll(Duration.ofMillis(50))) {
                processed += "${r.partition()}@${r.offset()}" // "process" the record ...
                listener.processed(r)                         // ... and tell the listener
            }
        }

        fun owned(): Set<Int> = consumer.assignment().map { it.partition() }.toSet()
        fun revoked(): List<Set<Int>> = listener.events.filter { it.kind == REVOKED && it.partitions.isNotEmpty() }.map { e -> e.partitions.map { it.partition() }.toSet() }
        fun assigned(): List<Set<Int>> = listener.events.filter { it.kind == ASSIGNED && it.partitions.isNotEmpty() }.map { e -> e.partitions.map { it.partition() }.toSet() }
        override fun close() = consumer.close()
    }

    /** Polls every member in turn until [done] holds, or fails after 40 seconds. */
    private fun pollUntil(members: List<Member>, what: String, done: () -> Boolean) {
        val deadline = System.nanoTime() + Duration.ofSeconds(40).toNanos()
        while (!done()) {
            check(System.nanoTime() < deadline) { "timed out waiting for: $what" }
            members.forEach { it.pollOnce() }
        }
    }

    /** Appends 10 records to each of the 6 partitions. */
    private fun write(topic: String, round: Int) = KafkaSupport.producer().use { p ->
        for (part in 0 until 6) for (i in 0 until 10) p.send(ProducerRecord(topic, part, "acct-$part", "r$round-$i"))
    }

    /** Grows the group to three members, 60 new records per step, and returns the members and what they processed. */
    private fun growGroup(extra: Map<String, Any>, check: (List<Member>, List<String>) -> Unit) {
        val topic = KafkaSupport.newTopic("rebalance", 6)
        val config = mapOf<String, Any>(
            ConsumerConfig.GROUP_ID_CONFIG to "ledger-${UUID.randomUUID().toString().take(8)}",
            ConsumerConfig.MAX_POLL_RECORDS_CONFIG to 5,
        ) + extra
        val processed = mutableListOf<String>()
        val members = mutableListOf<Member>()
        try {
            write(topic, 1)
            members += Member("c1", config, topic, processed)
            pollUntil(members, "c1 processes all 60 records") { processed.size == 60 }

            members += Member("c2", config, topic, processed)
            pollUntil(members, "a 3/3 split") { members.map { it.owned().size } == listOf(3, 3) }
            write(topic, 2)
            pollUntil(members, "120 records processed") { processed.size >= 120 }

            members += Member("c3", config, topic, processed)
            pollUntil(members, "a 2/2/2 split") { members.map { it.owned().size } == listOf(2, 2, 2) }
            write(topic, 3)
            pollUntil(members, "180 records processed") { processed.size >= 180 }

            // the final assignment: every partition owned by exactly one member
            assertThat(members.flatMap { it.owned() }).containsExactlyInAnyOrder(0, 1, 2, 3, 4, 5)
            // the handover commits mean no record was processed twice
            assertThat(processed).hasSize(180).doesNotHaveDuplicates()
            check(members, processed)
        } finally {
            members.forEach { it.close() }
        }
    }

    @Test
    fun `with the new protocol, a joining member only takes partitions, it never stops the others`() =
        growGroup(mapOf(ConsumerConfig.GROUP_PROTOCOL_CONFIG to "consumer")) { members, _ ->
            val (c1, c2, c3) = members
            // c1 got its six partitions once, and later only gave some away: 3 when c2 joined, 1 when c3 joined
            assertThat(c1.assigned()).containsExactly(setOf(0, 1, 2, 3, 4, 5))
            assertThat(c1.revoked().map { it.size }).containsExactly(3, 1)
            assertThat(c1.revoked().flatten()).doesNotContainAnyElementsOf(c1.owned())
            // c2 was assigned once and gave away one partition
            assertThat(c2.assigned()).hasSize(1)
            assertThat(c2.revoked().map { it.size }).containsExactly(1)
            assertThat(c3.revoked()).isEmpty()
        }

    @Test
    fun `with the classic eager protocol, every rebalance takes every partition from every member`() =
        growGroup(mapOf(ConsumerConfig.PARTITION_ASSIGNMENT_STRATEGY_CONFIG to "org.apache.kafka.clients.consumer.RangeAssignor")) { members, _ ->
            val (c1, c2, _) = members
            // c1 handed back all six when c2 joined, then all three it had when c3 joined, and got new sets each time
            assertThat(c1.revoked()).containsExactly(setOf(0, 1, 2, 3, 4, 5), setOf(0, 1, 2))
            assertThat(c1.assigned()).containsExactly(setOf(0, 1, 2, 3, 4, 5), setOf(0, 1, 2), setOf(0, 1))
            assertThat(c2.revoked()).hasSize(1).allMatch { it.size == 3 }
        }
}
