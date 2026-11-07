package sfz.kafka.l02

import org.apache.kafka.clients.admin.AlterConfigOp
import org.apache.kafka.clients.admin.ConfigEntry
import org.apache.kafka.clients.admin.OffsetSpec
import org.apache.kafka.clients.consumer.OffsetOutOfRangeException
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.config.ConfigResource
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import sfz.kafka.support.KafkaSupport
import java.time.Duration

/**
 * The same retention rule on a real Kafka 4.4 broker. This test needs no code from you: it shows that the
 * broker does what your SegmentedLog does. (The test broker checks retention every second.)
 */
class RetentionOnBrokerTest {
    companion object {
        @JvmStatic
        @BeforeAll
        fun startBroker() = KafkaSupport.start()
    }

    private fun earliest(tp: TopicPartition): Long = KafkaSupport.admin().use { admin ->
        admin.listOffsets(mapOf(tp to OffsetSpec.earliest())).partitionResult(tp).get().offset()
    }

    @Test
    fun `retention deletes whole 1 MiB segments, so the earliest offset jumps past many records at once`() {
        // 1 MiB is the smallest segment.bytes Kafka 4.x accepts; 10 kB records put about 100 in a segment
        val topic = KafkaSupport.newTopic("ledger", configs = mapOf("segment.bytes" to "1048576"))
        val tp = TopicPartition(topic, 0)
        val now = System.currentTimeMillis()
        val twoHoursAgo = now - Duration.ofHours(2).toMillis()
        val value = "x".repeat(10_000)

        // offsets 0..249 carry a timestamp two hours old, offsets 250..399 carry "now"
        KafkaSupport.producer().use { p ->
            (0 until 400).map { i ->
                p.send(ProducerRecord(topic, 0, if (i < 250) twoHoursAgo else now, "acct-${i % 7}", value))
            }.forEach { it.get() }
        }
        assertThat(earliest(tp)).isEqualTo(0)

        // keep one hour: every record at offsets 0..249 is now past retention
        KafkaSupport.admin().use { admin ->
            val op = AlterConfigOp(ConfigEntry("retention.ms", "3600000"), AlterConfigOp.OpType.SET)
            admin.incrementalAlterConfigs(mapOf(ConfigResource(ConfigResource.Type.TOPIC, topic) to listOf(op))).all().get()
        }
        val deadline = System.nanoTime() + Duration.ofSeconds(20).toNanos()
        var start = 0L
        while (start == 0L && System.nanoTime() < deadline) {
            Thread.sleep(250)
            start = earliest(tp)
        }

        // it jumped by at least one whole segment (about 100 records), not record by record ...
        assertThat(start).isGreaterThanOrEqualTo(100)
        // ... and it stopped short of 250: the expired records start..249 share a segment with young ones
        assertThat(start).isLessThan(250)

        KafkaSupport.consumer().use { c ->
            c.assign(listOf(tp))
            c.seek(tp, start)
            val first = c.poll(Duration.ofSeconds(5)).records(tp).first()
            assertThat(first.offset()).isEqualTo(start)
            assertThat(first.timestamp()).isEqualTo(twoHoursAgo) // past retention, still readable
        }
    }

    @Test
    fun `a consumer that asks for a deleted offset gets OffsetOutOfRangeException when it has no reset policy`() {
        val topic = KafkaSupport.newTopic("ledger", configs = mapOf("segment.bytes" to "1048576"))
        val tp = TopicPartition(topic, 0)
        val old = System.currentTimeMillis() - Duration.ofHours(2).toMillis()
        val value = "x".repeat(10_000)
        KafkaSupport.producer().use { p ->
            (0 until 150).map { p.send(ProducerRecord(topic, 0, old, "acct-1", value)) }.forEach { it.get() }
            p.send(ProducerRecord(topic, 0, System.currentTimeMillis(), "acct-1", value)).get()
        }
        KafkaSupport.admin().use { admin ->
            val op = AlterConfigOp(ConfigEntry("retention.ms", "3600000"), AlterConfigOp.OpType.SET)
            admin.incrementalAlterConfigs(mapOf(ConfigResource(ConfigResource.Type.TOPIC, topic) to listOf(op))).all().get()
        }
        val deadline = System.nanoTime() + Duration.ofSeconds(20).toNanos()
        while (earliest(tp) == 0L && System.nanoTime() < deadline) Thread.sleep(250)
        assertThat(earliest(tp)).isGreaterThan(0)

        KafkaSupport.consumer(mapOf("auto.offset.reset" to "none")).use { c ->
            c.assign(listOf(tp))
            c.seek(tp, 0)
            assertThatThrownBy { repeat(20) { c.poll(Duration.ofMillis(250)) } }
                .isInstanceOf(OffsetOutOfRangeException::class.java)
        }
    }
}
