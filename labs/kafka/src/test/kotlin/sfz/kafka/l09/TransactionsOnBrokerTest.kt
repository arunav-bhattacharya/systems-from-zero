package sfz.kafka.l09

import org.apache.kafka.clients.consumer.ConsumerConfig
import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.producer.ProducerConfig
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.errors.ProducerFencedException
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import sfz.kafka.support.KafkaSupport
import java.time.Duration
import java.util.UUID

/**
 * Your transformer against a Kafka 4.4 broker: real transactions, real markers, and two readers of the output,
 * one `read_committed` and one `read_uncommitted`.
 */
class TransactionsOnBrokerTest {
    companion object {
        @JvmStatic
        @BeforeAll
        fun startBroker() = KafkaSupport.start()
    }

    private fun id() = UUID.randomUUID().toString().take(8)

    /** Writes pay-00 .. pay-(n-1) to partition 0 of a new topic and returns the topic. */
    private fun paymentsTopic(n: Int): String {
        val topic = KafkaSupport.newTopic("payments", 1)
        KafkaSupport.producer().use { p -> for (i in 0 until n) p.send(ProducerRecord(topic, 0, "acct-${i % 3}", "pay-%02d".format(i))).get() }
        return topic
    }

    private fun transactional(txnId: String) = KafkaSupport.producer(mapOf(ProducerConfig.TRANSACTIONAL_ID_CONFIG to txnId))

    private fun groupConsumer(group: String, topic: String): KafkaConsumer<String, String> =
        KafkaSupport.consumer(mapOf(ConsumerConfig.GROUP_ID_CONFIG to group, ConsumerConfig.MAX_POLL_RECORDS_CONFIG to 10))
            .also { it.assign(listOf(TopicPartition(topic, 0))) }

    /**
     * Every value in [topic] partition 0, read from the beginning with the given isolation level. It reads up to the
     * log end as it is now. A read_committed reader gets there once the last transaction's marker is written (the
     * broker writes markers just after commitTransaction returns), so it waits for that, up to 15 seconds.
     */
    private fun readAll(topic: String, isolation: String): List<String> {
        val tp = TopicPartition(topic, 0)
        val logEnd = KafkaSupport.consumer().use { it.endOffsets(listOf(tp)).getValue(tp) }
        return KafkaSupport.consumer(mapOf(ConsumerConfig.ISOLATION_LEVEL_CONFIG to isolation)).use { c ->
            c.assign(listOf(tp))
            val got = mutableListOf<ConsumerRecord<String, String>>()
            val deadline = System.nanoTime() + Duration.ofSeconds(15).toNanos()
            while (c.position(tp) < logEnd && System.nanoTime() < deadline) got += c.poll(Duration.ofMillis(200))
            got.map { it.value() }
        }
    }

    private fun runUntil(t: LedgerTransformer, payments: Int) {
        var done = 0
        val deadline = System.nanoTime() + Duration.ofSeconds(30).toNanos()
        while (done < payments && System.nanoTime() < deadline) done += t.processOnce(Duration.ofMillis(200))
        assertThat(done).isEqualTo(payments)
    }

    @Test
    fun `entries and offsets commit together`() {
        val input = paymentsTopic(10)
        val output = KafkaSupport.newTopic("ledger-entries", 1)
        val group = "ledger-${id()}"
        groupConsumer(group, input).use { c ->
            transactional("ledger-${id()}").use { p ->
                val t = LedgerTransformer(c, p, output) { r -> listOf("debit:${r.value()}", "fee:${r.value()}") }
                t.init()
                runUntil(t, 10)
            }
        }
        assertThat(readAll(output, "read_committed")).hasSize(20).contains("debit:pay-00", "fee:pay-09")
        val committed = KafkaSupport.admin().use { it.listConsumerGroupOffsets(group).partitionsToOffsetAndMetadata().get() }
        assertThat(committed[TopicPartition(input, 0)]?.offset()).isEqualTo(10L) // committed by the transaction
    }

    @Test
    fun `an aborted batch is invisible to read_committed and visible to read_uncommitted`() {
        val input = paymentsTopic(10)
        val output = KafkaSupport.newTopic("ledger-entries", 1)
        val group = "ledger-${id()}"
        groupConsumer(group, input).use { c ->
            transactional("ledger-${id()}").use { p ->
                var crash = true
                val t = LedgerTransformer(c, p, output) { r ->
                    if (crash && r.value() == "pay-07") {
                        p.flush()                                  // the 14 entries before it reach the broker ...
                        throw IllegalStateException("simulated crash")  // ... then the batch fails
                    }
                    listOf("debit:${r.value()}", "fee:${r.value()}")
                }
                t.init()
                assertThatThrownBy { t.processOnce(Duration.ofSeconds(5)) }.hasMessage("simulated crash")

                assertThat(readAll(output, "read_uncommitted")).hasSize(14)  // the aborted entries are in the log
                assertThat(readAll(output, "read_committed")).isEmpty()      // and nobody committed sees them

                crash = false
                runUntil(t, 10)                                              // the rewound batch, again, in full
            }
        }
        val committedView = readAll(output, "read_committed")
        assertThat(committedView).hasSize(20).doesNotHaveDuplicates()        // each payment's entries exactly once
        assertThat(readAll(output, "read_uncommitted")).hasSize(34)          // 14 aborted + 20 committed
    }

    @Test
    fun `a second instance with the same transactional id fences the first`() {
        val input = paymentsTopic(20)
        val output = KafkaSupport.newTopic("ledger-entries", 1)
        val group = "ledger-${id()}"
        val txnId = "ledger-${id()}"
        val entries = { r: ConsumerRecord<String, String> -> listOf("debit:${r.value()}") }
        groupConsumer(group, input).use { c1 ->
            transactional(txnId).use { p1 ->
                val first = LedgerTransformer(c1, p1, output, entries)
                first.init()
                val firstBatch = first.processOnce(Duration.ofSeconds(5)) // committed: entries and offsets
                assertThat(firstBatch).isPositive()

                // the first instance stalls; a new one with the same transactional.id starts and takes over
                groupConsumer(group, input).use { c2 ->
                    transactional(txnId).use { p2 ->
                        val second = LedgerTransformer(c2, p2, output, entries)
                        second.init() // a new epoch for the transactional.id: the first producer is now a zombie

                        // the zombie wakes up and tries its next batch: the broker refuses it
                        assertThatThrownBy { first.processOnce(Duration.ofSeconds(5)) }
                            .isInstanceOf(ProducerFencedException::class.java)

                        runUntil(second, 20 - firstBatch) // the new instance carries on from the committed offset
                    }
                }
            }
        }
        val committedView = readAll(output, "read_committed")
        assertThat(committedView).hasSize(20).doesNotHaveDuplicates() // the zombie added nothing
    }
}
