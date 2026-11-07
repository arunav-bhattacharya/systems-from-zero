package sfz.kafka.l09

import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.MockConsumer
import org.apache.kafka.clients.consumer.OffsetAndMetadata
import org.apache.kafka.clients.producer.MockProducer
import org.apache.kafka.common.Cluster
import org.apache.kafka.common.Node
import org.apache.kafka.common.PartitionInfo
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.errors.ProducerFencedException
import org.apache.kafka.common.serialization.StringSerializer
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import java.time.Duration

/**
 * The transaction calls, in the right order, against MockConsumer and MockProducer. MockProducer keeps a
 * transaction's records in `uncommittedRecords()` and moves them to `history()` only on commit.
 */
class LedgerTransformerTest {
    private val tp = TopicPartition("payments", 0)
    private val poll = Duration.ofMillis(10)

    private fun consumerWith(n: Int): MockConsumer<String, String> {
        val c = MockConsumer<String, String>("earliest")
        c.assign(listOf(tp))
        c.updateBeginningOffsets(mapOf(tp to 0L))
        addPayments(c, n)
        return c
    }

    /** MockConsumer forgets a record once poll has returned it; a real log keeps it, so a test re-adds it. */
    private fun addPayments(c: MockConsumer<String, String>, n: Int) {
        for (i in 0 until n) c.addRecord(ConsumerRecord("payments", 0, i.toLong(), "acct-$i", "pay-$i"))
    }

    private fun producer(): MockProducer<String, String> {
        val node = Node(0, "localhost", 9092)
        val cluster = Cluster("test", listOf(node), listOf(PartitionInfo("ledger-entries", 0, node, arrayOf(node), arrayOf(node))), emptySet(), emptySet())
        return MockProducer(cluster, true, null, StringSerializer(), StringSerializer())
    }

    /** Each payment becomes a debit and a fee entry. */
    private val twoEntries = { r: ConsumerRecord<String, String> -> listOf("debit:${r.value()}", "fee:${r.value()}") }

    @Test
    fun `init registers the transactional id`() {
        val p = producer()
        LedgerTransformer(consumerWith(0), p, "ledger-entries", twoEntries).init()
        assertThat(p.transactionInitialized()).isTrue()
    }

    @Test
    fun `a batch commits its entries and its offsets in one transaction`() {
        val c = consumerWith(3)
        val p = producer()
        val t = LedgerTransformer(c, p, "ledger-entries", twoEntries)
        t.init()
        assertThat(t.processOnce(poll)).isEqualTo(3)

        assertThat(p.transactionCommitted()).isTrue()
        assertThat(p.history().map { it.value() }).containsExactly("debit:pay-0", "fee:pay-0", "debit:pay-1", "fee:pay-1", "debit:pay-2", "fee:pay-2")
        assertThat(p.history().map { it.key() }).containsExactly("acct-0", "acct-0", "acct-1", "acct-1", "acct-2", "acct-2")
        // the offsets went into the transaction, for the consumer's group; the consumer itself committed nothing
        assertThat(p.consumerGroupOffsetsHistory().single().values.single()).isEqualTo(mapOf(tp to OffsetAndMetadata(3)))
        assertThat(c.committed(setOf(tp))[tp]).isNull()
    }

    @Test
    fun `an empty poll starts no transaction`() {
        val p = producer()
        val t = LedgerTransformer(consumerWith(0), p, "ledger-entries", twoEntries)
        t.init()
        assertThat(t.processOnce(poll)).isZero()
        assertThat(p.transactionInFlight()).isFalse()
        assertThat(p.commitCount()).isZero()
    }

    @Test
    fun `a failure aborts the transaction and rewinds the consumer to the start of the batch`() {
        val c = consumerWith(5)
        val p = producer()
        var crash = true
        val t = LedgerTransformer(c, p, "ledger-entries") { r ->
            if (crash && r.offset() == 3L) throw IllegalStateException("simulated crash")
            twoEntries(r)
        }
        t.init()
        assertThatThrownBy { t.processOnce(poll) }.hasMessage("simulated crash")

        assertThat(p.transactionAborted()).isTrue()
        assertThat(p.history()).isEmpty()                   // nothing of the batch was committed
        assertThat(p.consumerGroupOffsetsHistory()).isEmpty()
        assertThat(c.position(tp)).isEqualTo(0)             // the batch will be read again

        crash = false
        addPayments(c, 5)                                   // the log still holds the batch
        assertThat(t.processOnce(poll)).isEqualTo(5)        // the retry processes the whole batch once
        assertThat(p.history()).hasSize(10)
    }

    @Test
    fun `a fenced producer is not aborted, the exception goes to the caller`() {
        val c = consumerWith(2)
        val p = producer()
        val t = LedgerTransformer(c, p, "ledger-entries", twoEntries)
        t.init()
        p.fenceProducer()                                   // a newer instance with the same transactional.id started
        assertThatThrownBy { t.processOnce(poll) }.isInstanceOf(ProducerFencedException::class.java)
        assertThat(p.transactionAborted()).isFalse()
    }
}
