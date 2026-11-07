package sfz.kafka.l06

import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.ConsumerRecords
import org.apache.kafka.clients.consumer.MockConsumer
import org.apache.kafka.clients.consumer.OffsetAndMetadata
import org.apache.kafka.common.TopicPartition
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import java.time.Duration

/**
 * The poll loop against MockConsumer, the in-memory Consumer that ships with kafka-clients. No broker needed.
 * The ledger object outlives each consumer, the way a database outlives a crashed service.
 */
class PaymentConsumerTest {
    private val tp0 = TopicPartition("payments", 0)
    private val tp1 = TopicPartition("payments", 1)
    private val poll = Duration.ofMillis(10)

    /** pay-00, pay-01, ... for acct-0, acct-1, acct-2 in turn; pay-07 is 10.07 EUR. */
    private fun payments(n: Int) = (0 until n).map { Payment("pay-%02d".format(it), "acct-${it % 3}", 1000L + it) }

    private fun record(tp: TopicPartition, offset: Long, p: Payment) =
        ConsumerRecord(tp.topic(), tp.partition(), offset, p.account(), p.toValue())

    /** A fresh consumer on partition 0, whose log holds [log] at offsets 0, 1, 2, ..., positioned at [from]. */
    private fun consumerOn(log: List<Payment>, from: Long, maxPollRecords: Long = 500): MockConsumer<String, String> {
        val c = MockConsumer<String, String>("earliest")
        c.assign(listOf(tp0))
        c.updateBeginningOffsets(mapOf(tp0 to 0L))
        c.seek(tp0, from)
        c.setMaxPollRecords(maxPollRecords)
        log.forEachIndexed { offset, p -> c.addRecord(record(tp0, offset.toLong(), p)) }
        return c
    }

    private fun MockConsumer<String, String>.committedOffset(): Long? = committed(setOf(tp0))[tp0]?.offset()

    /** A sink that applies [limit] payments to [ledger], then throws, as if the process died at that moment. */
    private class CrashAfter(private val ledger: IdempotentLedger, private val limit: Int) : PaymentSink {
        var calls = 0
        override fun apply(payment: Payment): Boolean {
            if (++calls > limit) throw IllegalStateException("simulated crash")
            return ledger.apply(payment)
        }
    }

    @Test
    fun `the ledger applies a payment once per idempotency key`() {
        val ledger = IdempotentLedger()
        val p = Payment("pay-42", "acct-7", 4000)
        assertThat(ledger.apply(p)).isTrue()
        assertThat(ledger.apply(p)).isFalse()
        assertThat(ledger.apply(Payment("pay-43", "acct-7", 250))).isTrue()
        assertThat(ledger.balanceCents("acct-7")).isEqualTo(4250)
        assertThat(ledger.balanceCents("acct-8")).isZero()
        assertThat(ledger.appliedCount()).isEqualTo(2)
        assertThat(ledger.duplicatesSkipped()).isEqualTo(1)
    }

    @Test
    fun `the offset to commit is the last offset of each partition plus one`() {
        val ps = payments(3)
        val records = ConsumerRecords(
            mapOf(tp0 to listOf(record(tp0, 5, ps[0]), record(tp0, 6, ps[1])), tp1 to listOf(record(tp1, 9, ps[2]))),
            emptyMap(),
        )
        assertThat(PaymentConsumer.offsetsToCommit(records))
            .containsExactlyInAnyOrderEntriesOf(mapOf(tp0 to OffsetAndMetadata(7), tp1 to OffsetAndMetadata(10)))
    }

    @Test
    fun `pollOnce applies the whole batch, then commits the next offset to read`() {
        val c = consumerOn(payments(5), 0)
        val ledger = IdempotentLedger()
        assertThat(PaymentConsumer.pollOnce(c, ledger, poll)).isEqualTo(5)
        assertThat(ledger.appliedCount()).isEqualTo(5)
        assertThat(c.committedOffset()).isEqualTo(5)
    }

    @Test
    fun `an empty poll commits nothing`() {
        val c = consumerOn(emptyList(), 0)
        assertThat(PaymentConsumer.pollOnce(c, IdempotentLedger(), poll)).isZero()
        assertThat(c.committedOffset()).isNull()
    }

    @Test
    fun `a crash in the middle of a batch loses no payment and applies none twice`() {
        val log = payments(10)
        val ledger = IdempotentLedger()

        // consumer 1: the first batch (0..4) is applied and committed; the second crashes after pay-05..pay-07
        val first = consumerOn(log, 0, maxPollRecords = 5)
        PaymentConsumer.pollOnce(first, ledger, poll)
        assertThat(first.committedOffset()).isEqualTo(5)
        assertThatThrownBy { PaymentConsumer.pollOnce(first, CrashAfter(ledger, 3), poll) }.hasMessage("simulated crash")
        assertThat(first.committedOffset()).isEqualTo(5) // the crashed batch was not committed
        assertThat(ledger.appliedCount()).isEqualTo(8)

        // consumer 2 starts where the group's committed offset says: 5. pay-05..07 come again.
        val second = consumerOn(log, first.committedOffset()!!, maxPollRecords = 5)
        assertThat(PaymentConsumer.pollOnce(second, ledger, poll)).isEqualTo(5)
        assertThat(second.committedOffset()).isEqualTo(10)

        assertThat(ledger.appliedCount()).isEqualTo(10)    // nothing lost
        assertThat(ledger.duplicatesSkipped()).isEqualTo(3) // pay-05, pay-06, pay-07 were delivered twice ...
        assertThat(ledger.balanceCents("acct-0")).isEqualTo(1000L + 1003 + 1006 + 1009) // ... and counted once
    }

    @Test
    fun `committing before processing would lose the rest of the batch on a crash`() {
        val log = payments(10)
        val ledger = IdempotentLedger()
        val first = consumerOn(log, 0, maxPollRecords = 10)
        val records = first.poll(poll)
        first.commitSync(PaymentConsumer.offsetsToCommit(records)) // the wrong order: commit first ...
        val crashing = CrashAfter(ledger, 7)
        assertThatThrownBy { records.forEach { crashing.apply(Payment.parse(it.value())) } } // ... then crash at pay-07
        val second = consumerOn(log, first.committedOffset()!!)
        PaymentConsumer.pollOnce(second, ledger, poll)
        assertThat(ledger.appliedCount()).isEqualTo(7) // pay-07, pay-08 and pay-09 are gone for good
    }

    @Test
    fun `a payment the producer sent twice is applied once`() {
        val ps = payments(4)
        val log = ps + ps[2] // the producer timed out on pay-02 and sent it again: a new record, the same key
        val ledger = IdempotentLedger()
        assertThat(PaymentConsumer.pollOnce(consumerOn(log, 0), ledger, poll)).isEqualTo(5)
        assertThat(ledger.appliedCount()).isEqualTo(4)
        assertThat(ledger.duplicatesSkipped()).isEqualTo(1)
    }

    @Test
    fun `run keeps polling until another thread calls wakeup`() {
        val c = consumerOn(payments(5), 0)
        c.schedulePollTask { }             // poll 1 returns the five records
        c.schedulePollTask { }             // poll 2 returns nothing
        c.schedulePollTask { c.wakeup() }  // poll 3 is woken up and throws WakeupException
        val ledger = IdempotentLedger()
        assertThat(PaymentConsumer.run(c, ledger)).isEqualTo(5)
        assertThat(c.committedOffset()).isEqualTo(5)
        assertThat(c.closed()).isFalse() // closing is the caller's job
    }
}
