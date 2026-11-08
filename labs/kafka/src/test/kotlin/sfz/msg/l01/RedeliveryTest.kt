package sfz.msg.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * The measurements of the lesson: 1,000 payment events for 10 accounts, consumers that take 1 to 3 ticks per message,
 * and a consumer that crashes every 25 ticks just after finishing a message and before acking it (see [ConsumerSim]).
 * Each test reads the shared processing log with [OrderCheck].
 */
class RedeliveryTest {
    private val events = ConsumerSim.payments(1000, keys = 10)

    private class Outcome(val check: OrderCheck.Result, val distinct: Int, val redeliveries: Int)

    private fun runOne(consumers: List<String>, prefetch: Int, crashEvery: Int, autoAck: Boolean = false): Outcome {
        val q = MiniQueue("payments")
        events.forEach(q::publish)
        val sim = ConsumerSim(q, consumers, prefetch, autoAck)
        sim.run(crashing = consumers.last(), crashEvery = crashEvery)
        return Outcome(OrderCheck.check(sim.processed), sim.processed.toSet().size, sim.redeliveries)
    }

    @Test
    fun `one consumer that keeps crashing books some payments twice but never out of order`() {
        val o = runOne(listOf("A"), prefetch = 10, crashEvery = 25)
        assertThat(o.redeliveries).isPositive()
        assertThat(o.check.duplicates()).isPositive()             // each crash lost one ack
        assertThat(o.check.inversions()).isZero()                 // returns go back to the head, in order
        assertThat(o.distinct).isEqualTo(1000)                    // nothing lost
    }

    @Test
    fun `two competing consumers reorder an account's payments even when nothing fails`() {
        val o = runOne(listOf("A", "B"), prefetch = 10, crashEvery = 0)
        assertThat(o.check.duplicates()).isZero()
        assertThat(o.check.inversions()).isPositive()             // A is still on seq 4 when B finishes seq 5
    }

    @Test
    fun `redelivery makes competing consumers reorder far more`() {
        val calm = runOne(listOf("A", "B"), prefetch = 10, crashEvery = 0)
        val crashy = runOne(listOf("A", "B"), prefetch = 10, crashEvery = 25)
        assertThat(crashy.check.inversions()).isGreaterThan(2 * calm.check.inversions())
        assertThat(crashy.distinct).isEqualTo(1000)
    }

    @Test
    fun `a bigger prefetch means more redeliveries per crash and more inversions`() {
        val small = runOne(listOf("A", "B"), prefetch = 10, crashEvery = 25)
        val big = runOne(listOf("A", "B"), prefetch = 100, crashEvery = 25)
        assertThat(big.redeliveries).isGreaterThan(5 * small.redeliveries)
        assertThat(big.check.inversions()).isGreaterThan(small.check.inversions())
    }

    @Test
    fun `auto-ack turns crashes into lost payments`() {
        val o = runOne(listOf("A"), prefetch = 10, crashEvery = 25, autoAck = true)
        assertThat(o.redeliveries).isZero()                       // the broker forgot each message as it left
        assertThat(o.distinct).isLessThan(1000)
    }

    @Test
    fun `one queue per group of accounts, one consumer each, keeps every account in order through crashes`() {
        val even = MiniQueue("payments-even")
        val odd = MiniQueue("payments-odd")
        val byAccount = Exchange("payments", Exchange.Type.DIRECT)
        byAccount.bind(even, "even")
        byAccount.bind(odd, "odd")
        for (e in events) {
            val n = e.key.removePrefix("acct-").toInt()
            assertThat(byAccount.publish(if (n % 2 == 0) "even" else "odd", e)).isEqualTo(1)
        }
        val a = ConsumerSim(even, listOf("A"), prefetch = 10).apply { run(crashing = "A", crashEvery = 25) }
        val b = ConsumerSim(odd, listOf("B"), prefetch = 10).apply { run(crashing = "B", crashEvery = 25) }
        val check = OrderCheck.check(a.processed + b.processed)
        assertThat(check.inversions()).isZero()                   // each account lives in one queue with one reader
        assertThat(check.duplicates()).isPositive()               // redelivery still duplicates: dedupe on a key
        assertThat((a.processed + b.processed).toSet()).hasSize(1000)
    }

    @Test
    fun `fan-out gives every subscriber every message, competing consumers split them`() {
        val ledger = MiniQueue("ledger")
        val fraud = MiniQueue("fraud-check")
        val payments = Exchange("payments", Exchange.Type.FANOUT)
        payments.bind(ledger, "")
        payments.bind(fraud, "")
        events.forEach { payments.publish("", it) }

        val ledgerSim = ConsumerSim(ledger, listOf("ledger-1", "ledger-2"), prefetch = 10).apply { run() }
        val fraudSim = ConsumerSim(fraud, listOf("fraud-1"), prefetch = 10).apply { run() }

        assertThat(fraudSim.processed).hasSize(1000)              // its own copy of everything
        assertThat(ledgerSim.processed.toSet()).hasSize(1000)     // the ledger service also sees everything...
        val split = ledgerSim.processedBy.values.map { it.size }
        assertThat(split).allSatisfy { assertThat(it).isBetween(300, 700) }   // ...but each instance only part of it
        assertThat(split.sum()).isEqualTo(1000)
    }
}
