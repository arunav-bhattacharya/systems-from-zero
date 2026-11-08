package sfz.msg.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class ExchangeTest {
    private val auth = Message("acct-17", 0)

    @Test
    fun `a fanout exchange puts a copy in every bound queue and ignores the key`() {
        val ledger = MiniQueue("ledger")
        val fraud = MiniQueue("fraud-check")
        val notify = MiniQueue("notify")
        val payments = Exchange("payments", Exchange.Type.FANOUT)
        payments.bind(ledger, "")
        payments.bind(fraud, "")
        payments.bind(notify, "anything")
        assertThat(payments.publish("whatever", auth)).isEqualTo(3)
        assertThat(listOf(ledger, fraud, notify).map { it.ready }).containsExactly(1, 1, 1)
    }

    @Test
    fun `a direct exchange routes by an exact match of routing key and binding key`() {
        val eu = MiniQueue("settle-eu")
        val us = MiniQueue("settle-us")
        val settle = Exchange("settle", Exchange.Type.DIRECT)
        settle.bind(eu, "EUR")
        settle.bind(us, "USD")
        assertThat(settle.route("EUR")).containsExactly(eu)
        assertThat(settle.publish("USD", auth)).isEqualTo(1)
        assertThat(eu.ready to us.ready).isEqualTo(0 to 1)
    }

    @Test
    fun `a queue bound twice still gets one copy`() {
        val audit = MiniQueue("audit")
        val ledger = MiniQueue("ledger")
        val ex = Exchange("payments", Exchange.Type.DIRECT)
        ex.bind(audit, "EUR")
        ex.bind(ledger, "EUR")
        ex.bind(audit, "EUR")
        assertThat(ex.route("EUR")).containsExactly(audit, ledger)
        ex.publish("EUR", auth)
        assertThat(audit.ready).isEqualTo(1)
    }

    @Test
    fun `a message no binding matches goes nowhere`() {
        val eu = MiniQueue("settle-eu")
        val settle = Exchange("settle", Exchange.Type.DIRECT)
        settle.bind(eu, "EUR")
        assertThat(settle.publish("GBP", auth)).isZero()
        assertThat(eu.ready).isZero()
    }
}
