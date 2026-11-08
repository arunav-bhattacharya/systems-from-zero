package sfz.msg.l05

import org.apache.kafka.clients.admin.NewPartitions
import org.apache.kafka.clients.producer.ProducerConfig
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import sfz.kafka.support.KafkaSupport
import java.time.Duration

/**
 * The same rules on a real Kafka 4.4 producer and broker: 1,000 payments over 10 account keys into 6 partitions.
 * Each payment's value starts with its send order, so the consumer side can check order.
 */
class KeysOnBrokerTest {
    companion object {
        @JvmStatic
        @BeforeAll
        fun startBroker() = KafkaSupport.start()

        val accounts = (1..10).map { "acct-$it" }
        val pad = "x".repeat(80) // about 100-byte values, like a small payment event
    }

    /** Sends one record per (key, seq) pair in order and returns the partition the producer chose for each. */
    private fun send(topic: String, keys: List<String?>, extra: Map<String, Any> = emptyMap()): List<Int> =
        KafkaSupport.producer(extra).use { p ->
            keys.mapIndexed { seq, key -> p.send(ProducerRecord(topic, key, "$seq,$pad")) }.map { it.get().partition() }
        }

    /** Reads every record of the topic, partition by partition as the consumer delivers them. */
    private fun readAll(topic: String, partitions: Int, count: Int): List<Seen> =
        KafkaSupport.consumer().use { c ->
            val tps = (0 until partitions).map { TopicPartition(topic, it) }
            c.assign(tps)
            c.seekToBeginning(tps)
            val seen = mutableListOf<Seen>()
            val deadline = System.nanoTime() + Duration.ofSeconds(20).toNanos()
            while (seen.size < count && System.nanoTime() < deadline) {
                for (r in c.poll(Duration.ofMillis(200))) {
                    seen += Seen(r.key(), r.value().substringBefore(',').toInt(), r.partition(), r.offset())
                }
            }
            assertThat(seen).hasSize(count)
            seen
        }

    @Test
    fun `the producer puts every keyed record where your partitionFor says, and per-key order survives`() {
        val topic = KafkaSupport.newTopic("payments", 6)
        val keys = (0 until 1_000).map { accounts[it % 10] }
        val chosen = send(topic, keys)

        // the real producer agrees with your arithmetic, record by record
        assertThat(chosen).isEqualTo(keys.map { KeyPartitioner.partitionFor(it, 6) })

        val seen = readAll(topic, 6, 1_000)
        assertThat(KeyOrdering.partitionsByKey(seen).values).allMatch { it.size == 1 } // one key, one partition
        assertThat(KeyOrdering.keysOutOfOrder(seen)).isEmpty()                         // so each key stays in order
        assertThat(KeyOrdering.firstGlobalBreak(seen)).isPositive()                     // but the whole stream does not
    }

    @Test
    fun `records without a key stick to one partition for a while, then move on`() {
        val topic = KafkaSupport.newTopic("payments", 6)
        val chosen = send(topic, List(1_000) { null })
        val switches = chosen.zipWithNext().count { (a, b) -> a != b }
        assertThat(chosen.toSet()).hasSizeGreaterThan(1) // spread over several partitions ...
        assertThat(switches).isLessThan(50)              // ... in long runs, not one record each (about 16 KB per run)
    }

    @Test
    fun `partitioner ignore keys spreads one key over several partitions and per-key order is gone`() {
        val topic = KafkaSupport.newTopic("payments", 6)
        val keys = (0 until 1_000).map { accounts[it % 10] }
        send(topic, keys, mapOf(ProducerConfig.PARTITIONER_IGNORE_KEYS_CONFIG to true))
        val seen = readAll(topic, 6, 1_000)
        assertThat(KeyOrdering.partitionsByKey(seen).values).anyMatch { it.size > 1 }
    }

    @Test
    fun `after the topic grows from 6 to 8 partitions, exactly the keys you predicted move`() {
        val topic = KafkaSupport.newTopic("payments", 6)
        val many = (1..40).map { "acct-$it" }
        send(topic, many)

        KafkaSupport.admin().use { admin ->
            admin.createPartitions(mapOf(topic to NewPartitions.increaseTo(8))).all().get()
        }
        KafkaSupport.awaitLeaders(topic, 8)
        // a new producer, once its metadata shows 8 partitions
        val deadline = System.nanoTime() + Duration.ofSeconds(10).toNanos()
        while (KafkaSupport.producer().use { it.partitionsFor(topic).size } < 8 && System.nanoTime() < deadline) {
            Thread.sleep(200)
        }
        val after = send(topic, many)
        assertThat(after).isEqualTo(many.map { KeyPartitioner.partitionFor(it, 8) })

        val seen = readAll(topic, 8, 80)
        val split = KeyOrdering.partitionsByKey(seen).filterValues { it.size == 2 }.keys
        assertThat(split).isEqualTo(KeyOrdering.movedKeys(many, 6, 8))
        assertThat(split).isNotEmpty()
    }
}
