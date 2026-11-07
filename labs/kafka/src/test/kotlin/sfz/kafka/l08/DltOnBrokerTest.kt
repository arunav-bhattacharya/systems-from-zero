package sfz.kafka.l08

import org.apache.kafka.clients.admin.NewTopic
import org.apache.kafka.clients.consumer.ConsumerConfig
import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import sfz.kafka.support.KafkaSupport
import java.time.Duration
import java.util.UUID

/**
 * Your consumer against a Kafka 4.4 broker: 3 partitions of payments with one poison pill, a real dead-letter topic,
 * and a real consumer group. The test reads the dead letters back from the broker, headers and all.
 */
class DltOnBrokerTest {
    companion object {
        @JvmStatic
        @BeforeAll
        fun startBroker() = KafkaSupport.start()
    }

    @Test
    fun `the poison pill ends up in the DLT with its origin, and the group finishes with lag 0`() {
        val topic = KafkaSupport.newTopic("payments", 3)
        val dltTopic = DeadLetters.topicFor(topic) // payments-1a2b3c4d.DLT, as many partitions as the original
        KafkaSupport.admin().use { it.createTopics(listOf(NewTopic(dltTopic, 3, 1.toShort()))).all().get() }
        KafkaSupport.awaitLeaders(dltTopic, 3)
        val poisonAt = KafkaSupport.producer().use { p ->
            for (i in 0 until 30) p.send(ProducerRecord(topic, i % 3, "acct-$i", "pay-%04d,acct-$i,1000".format(i))).get()
            p.send(ProducerRecord(topic, 1, "acct-99", "pay-0099,acct-99,12x50")).get().offset() // the poison pill
        }

        val processed = mutableListOf<String>()
        val group = "ledger-${UUID.randomUUID().toString().take(8)}"
        KafkaSupport.consumer(mapOf(ConsumerConfig.GROUP_ID_CONFIG to group, ConsumerConfig.MAX_POLL_RECORDS_CONFIG to 7)).use { c ->
            KafkaSupport.producer().use { dlt ->
                c.subscribe(listOf(topic))
                val rc = RetryingConsumer(c, dlt, dltTopic, 3, { Duration.ofMillis(10) }) { r: ConsumerRecord<String, String> ->
                    r.value().split(",")[2].toLong() // the poison pill throws NumberFormatException
                    processed += r.key()
                }
                var handled = 0
                val deadline = System.nanoTime() + Duration.ofSeconds(30).toNanos()
                while (handled < 31 && System.nanoTime() < deadline) handled += rc.pollOnce(Duration.ofMillis(200))
                assertThat(handled).isEqualTo(31)
            }
        }

        assertThat(processed).hasSize(30).doesNotContain("acct-99")

        // read the DLT back from the broker
        val dlts = (0 until 3).map { TopicPartition(dltTopic, it) }
        val dead = KafkaSupport.consumer().use { c ->
            c.assign(dlts)
            val got = mutableListOf<ConsumerRecord<String, String>>()
            val deadline = System.nanoTime() + Duration.ofSeconds(10).toNanos()
            while (got.isEmpty() && System.nanoTime() < deadline) got += c.poll(Duration.ofMillis(200))
            got
        }
        assertThat(dead).hasSize(1)
        val h = dead.single().headers()
        assertThat(dead.single().key()).isEqualTo("acct-99")
        assertThat(DeadLetters.header(h, DeadLetters.ORIGINAL_TOPIC)).isEqualTo(topic)
        assertThat(DeadLetters.header(h, DeadLetters.ORIGINAL_PARTITION)).isEqualTo("1")
        assertThat(DeadLetters.header(h, DeadLetters.ORIGINAL_OFFSET)).isEqualTo(poisonAt.toString())
        assertThat(DeadLetters.header(h, DeadLetters.EXCEPTION_CLASS)).isEqualTo("java.lang.NumberFormatException")

        // the group's bookmarks are at the end of every partition, poison pill included
        val tps = (0 until 3).map { TopicPartition(topic, it) }
        val end = KafkaSupport.consumer().use { it.endOffsets(tps) }
        val committed = KafkaSupport.admin().use { it.listConsumerGroupOffsets(group).partitionsToOffsetAndMetadata().get() }
        assertThat(tps.associateWith { committed[it]?.offset() }).isEqualTo(end)
    }
}
