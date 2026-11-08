package sfz.stream.l02

import org.apache.kafka.clients.producer.ProducerRecord
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.stream.l02.OutboxRelay.ChangeEvent
import sfz.stream.l02.OutboxRelay.WalEntry

/** Your outbox router and WAL reader. The records match what Debezium 3.7 wrote in this lesson's Try-it. */
class OutboxRelayTest {
    private fun outboxRow(id: String, account: String, payment: String) = mapOf(
        "id" to id, "aggregatetype" to "payment", "aggregateid" to account, "type" to "PaymentAuthorized",
        "payload" to """{"amount": 4000, "paymentId": "$payment"}""",
    )

    private fun paymentRow(payment: String, account: String) = mapOf("id" to payment, "account" to account, "amount" to "4000")

    private fun ProducerRecord<String, String>.header(key: String) = headers().lastHeader(key)?.value()?.let { String(it) }

    private fun ProducerRecord<String, String>.eventId() = header("id")

    @Test
    fun `an outbox insert becomes a record on outbox-event-payment, keyed by the aggregate id`() {
        val r = OutboxRelay.route(ChangeEvent("outbox", "c", outboxRow("e-1", "acct-17", "pay-1")))!!
        assertThat(r.topic()).isEqualTo("outbox.event.payment")
        assertThat(r.key()).isEqualTo("acct-17")
        assertThat(r.value()).isEqualTo("""{"amount": 4000, "paymentId": "pay-1"}""")
        assertThat(r.headers().map { it.key() }).containsExactly("id", "eventType")
        assertThat(r.header("id")).isEqualTo("e-1")
        assertThat(r.header("eventType")).isEqualTo("PaymentAuthorized")
    }

    @Test
    fun `only inserts and snapshot reads of the outbox are routed`() {
        assertThat(OutboxRelay.route(ChangeEvent("payment", "c", paymentRow("pay-1", "acct-17")))).isNull()
        assertThat(OutboxRelay.route(ChangeEvent("outbox", "u", outboxRow("e-1", "acct-17", "pay-1")))).isNull()
        assertThat(OutboxRelay.route(ChangeEvent("outbox", "d", outboxRow("e-1", "acct-17", "pay-1")))).isNull()
        assertThat(OutboxRelay.route(ChangeEvent("outbox", "r", outboxRow("e-1", "acct-17", "pay-1")))!!.eventId()).isEqualTo("e-1")
    }

    @Test
    fun `a committed transaction's outbox rows come out, its other rows don't`() {
        val wal = listOf(
            WalEntry(100, 767, "change", ChangeEvent("payment", "c", paymentRow("pay-1", "acct-17"))),
            WalEntry(110, 767, "change", ChangeEvent("outbox", "c", outboxRow("e-1", "acct-17", "pay-1"))),
            WalEntry(120, 767, "commit", null),
        )
        assertThat(OutboxRelay.relay(wal, 0).map { it.eventId() }).containsExactly("e-1")
    }

    @Test
    fun `a rolled-back transaction writes nothing, even though its rows reached the WAL`() {
        val wal = listOf(
            WalEntry(100, 768, "change", ChangeEvent("payment", "c", paymentRow("pay-2", "acct-42"))),
            WalEntry(110, 768, "change", ChangeEvent("outbox", "c", outboxRow("e-2", "acct-42", "pay-2"))),
            WalEntry(120, 768, "abort", null),
        )
        assertThat(OutboxRelay.relay(wal, 0)).isEmpty()
    }

    @Test
    fun `interleaved transactions come out in commit order`() {
        val wal = listOf(
            WalEntry(100, 1, "change", ChangeEvent("outbox", "c", outboxRow("a-1", "acct-1", "pay-a1"))),
            WalEntry(110, 2, "change", ChangeEvent("outbox", "c", outboxRow("b-1", "acct-2", "pay-b1"))),
            WalEntry(120, 1, "change", ChangeEvent("outbox", "c", outboxRow("a-2", "acct-1", "pay-a2"))),
            WalEntry(130, 2, "commit", null),   // transaction 2 commits first
            WalEntry(140, 1, "commit", null),
        )
        assertThat(OutboxRelay.relay(wal, 0).map { it.eventId() }).containsExactly("b-1", "a-1", "a-2")
    }

    private val twoTransactions = listOf(
        WalEntry(100, 1, "change", ChangeEvent("outbox", "c", outboxRow("e-1", "acct-1", "pay-1"))),
        WalEntry(110, 1, "commit", null),
        WalEntry(120, 2, "change", ChangeEvent("outbox", "c", outboxRow("e-2", "acct-1", "pay-2"))),
        WalEntry(130, 2, "commit", null),
    )

    @Test
    fun `a restart resumes after the stored offset`() {
        assertThat(OutboxRelay.relay(twoTransactions, 110).map { it.eventId() }).containsExactly("e-2")
        assertThat(OutboxRelay.relay(twoTransactions, 130)).isEmpty()
    }

    @Test
    fun `a restart from an older offset repeats events, with the same ids for consumers to dedupe on`() {
        val first = OutboxRelay.relay(twoTransactions, 0).map { it.eventId() }
        val again = OutboxRelay.relay(twoTransactions, 0).map { it.eventId() } // the offset flush was lost in a crash
        assertThat(first + again).containsExactly("e-1", "e-2", "e-1", "e-2")
    }
}
