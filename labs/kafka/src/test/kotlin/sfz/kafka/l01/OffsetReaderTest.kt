package sfz.kafka.l01

import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import sfz.kafka.support.KafkaSupport
import java.time.Duration

/** The same reads as MiniLogTest, against a real Kafka 4.4 broker in a container. */
class OffsetReaderTest {
    companion object {
        @JvmStatic
        @BeforeAll
        fun startBroker() = KafkaSupport.start()

        /** Makes a one-partition topic holding payment-0 .. payment-99 and returns its partition. */
        fun hundredPayments(): TopicPartition {
            val topic = KafkaSupport.newTopic("payments")
            KafkaSupport.producer().use { producer ->
                val offsets = (0 until 100).map { i ->
                    producer.send(ProducerRecord(topic, "acct-${i % 7}", "payment-$i"))
                }.map { it.get().offset() }
                // the broker hands out the offsets, one per record, in the order they arrive
                assertThat(offsets).isEqualTo((0L until 100L).toList())
            }
            return TopicPartition(topic, 0)
        }
    }

    @Test
    fun `reads all 100 records from offset 0 with offsets 0 to 99`() {
        val tp = hundredPayments()
        val records = KafkaSupport.consumer().use { OffsetReader.readFrom(it, tp, 0, 100, Duration.ofSeconds(10)) }
        assertThat(records.map { it.offset() }).isEqualTo((0L until 100L).toList())
        assertThat(records.map { it.value() }).isEqualTo((0 until 100).map { "payment-$it" })
    }

    @Test
    fun `a read from offset 50 starts at 50 and stops after max records`() {
        val tp = hundredPayments()
        val records = KafkaSupport.consumer().use { OffsetReader.readFrom(it, tp, 50, 10, Duration.ofSeconds(10)) }
        assertThat(records.map { it.offset() }).isEqualTo((50L until 60L).toList())
        assertThat(records.first().value()).isEqualTo("payment-50")
        assertThat(records.first().key()).isEqualTo("acct-1")
    }

    @Test
    fun `reading does not consume, so a second reader gets the same records`() {
        val tp = hundredPayments()
        val first = KafkaSupport.consumer().use { OffsetReader.readFrom(it, tp, 90, 10, Duration.ofSeconds(10)) }
        val second = KafkaSupport.consumer().use { OffsetReader.readFrom(it, tp, 90, 10, Duration.ofSeconds(10)) }
        assertThat(second.map { it.offset() to it.value() }).isEqualTo(first.map { it.offset() to it.value() })
        assertThat(second).hasSize(10)
    }

    @Test
    fun `a read at the end of the partition returns nothing once the timeout passes`() {
        val tp = hundredPayments()
        val records = KafkaSupport.consumer().use { OffsetReader.readFrom(it, tp, 100, 10, Duration.ofSeconds(1)) }
        assertThat(records).isEmpty()
    }
}
