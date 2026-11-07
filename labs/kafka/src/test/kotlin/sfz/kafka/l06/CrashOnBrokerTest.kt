package sfz.kafka.l06

import org.apache.kafka.clients.consumer.ConsumerConfig
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import sfz.kafka.support.KafkaSupport
import java.time.Duration
import java.util.UUID

/**
 * Your consumer against a Kafka 4.4 broker and a real consumer group. It crashes in the middle of a poll's batch,
 * a second consumer in the same group takes over from the committed offsets, and the ledger must end up with
 * every payment exactly once.
 */
class CrashOnBrokerTest {
    companion object {
        @JvmStatic
        @BeforeAll
        fun startBroker() = KafkaSupport.start()
    }

    private val poll = Duration.ofMillis(200)

    @Test
    fun `a consumer that dies mid-batch loses nothing, and the idempotency key stops double payments`() {
        val topic = KafkaSupport.newTopic("payments", 3)
        val payments = (0 until 100).map { Payment("pay-%03d".format(it), "acct-${it % 10}", 100L * (it + 1)) }
        // the producer side resent 5 payments after timeouts: new records, same idempotency keys
        val resent = payments.filter { it.idempotencyKey().endsWith("7") }.take(5)
        KafkaSupport.producer().use { p ->
            (payments + resent).map { p.send(ProducerRecord(topic, it.account(), it.toValue())) }.forEach { it.get() }
        }

        val group = "ledger-${UUID.randomUUID().toString().take(8)}"
        val config = mapOf<String, Any>(
            ConsumerConfig.GROUP_ID_CONFIG to group,
            ConsumerConfig.MAX_POLL_RECORDS_CONFIG to 10, // small batches, so the crash lands inside one
        )
        val ledger = IdempotentLedger()

        // consumer 1 dies on the 4th record of some poll, after at least 30 records: 3 applied, none committed
        var inThisPoll = 0
        var calls = 0
        val crashing = PaymentSink { p ->
            calls++
            inThisPoll++
            if (calls > 30 && inThisPoll == 4) throw IllegalStateException("simulated crash")
            ledger.apply(p)
        }
        KafkaSupport.consumer(config).use { c ->
            c.subscribe(listOf(topic))
            assertThatThrownBy {
                val deadline = System.nanoTime() + Duration.ofSeconds(30).toNanos()
                while (System.nanoTime() < deadline) {
                    inThisPoll = 0
                    PaymentConsumer.pollOnce(c, crashing, poll)
                }
            }.hasMessage("simulated crash")
        } // closing leaves the group at once; a killed process would be noticed after the session timeout

        // consumer 2, same group: it resumes from the committed offsets and runs until it has read everything
        val tps = (0 until 3).map { TopicPartition(topic, it) }
        val end = KafkaSupport.consumer().use { it.endOffsets(tps) }
        KafkaSupport.consumer(config).use { c ->
            c.subscribe(listOf(topic))
            val deadline = System.nanoTime() + Duration.ofSeconds(30).toNanos()
            while (System.nanoTime() < deadline) {
                PaymentConsumer.pollOnce(c, ledger, poll)
                val committed = c.committed(tps.toSet())
                if (tps.all { committed[it]?.offset() == end[it] }) break
            }
        }

        // every payment exactly once, and every account balance right
        assertThat(ledger.appliedCount()).isEqualTo(100)
        for (acct in 0 until 10) {
            val expected = payments.filter { it.account() == "acct-$acct" }.sumOf { it.amountCents() }
            assertThat(ledger.balanceCents("acct-$acct")).isEqualTo(expected)
        }
        // 105 records + the 3 applied but uncommitted before the crash = 108 deliveries for 100 payments
        assertThat(ledger.duplicatesSkipped()).isEqualTo(8)

        // and the group's committed offsets are at the end of every partition: lag 0
        val committed = KafkaSupport.admin().use { it.listConsumerGroupOffsets(group).partitionsToOffsetAndMetadata().get() }
        assertThat(tps.associateWith { committed[it]?.offset() }).isEqualTo(end)
    }
}
