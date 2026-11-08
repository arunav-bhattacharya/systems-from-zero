package sfz.cons.l06

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout

@Timeout(20)
class UncertaintyTest {
    private fun stats(policy: Policy, epsilon: Long, seed: Long = 1) = Cluster(policy, epsilon, seed).run(10_000)

    // ---------------------------------------------------------------- one transaction, one audit

    @Test
    fun `commit wait holds the client until the timestamp is surely past, overlapping the commit`() {
        val c = Cluster(Policy.COMMIT_WAIT, epsilonMs = 10)
        c.sim.launch { c.settle(1) }
        c.sim.runUntil(19)
        assertThat(c.payouts.versionsOf("batch").last().committed).`as`("decided at 8 ms, still waiting").isFalse()
        c.sim.runUntil(20)
        val v = c.payouts.versionsOf("batch").last()
        assertThat(v.committed).`as`("2 x epsilon after the timestamp was chosen").isTrue()
        assertThat(v.ts).`as`("TrueTime's latest on a clock 10 ms ahead, at time 0").isEqualTo(20)

        val short = Cluster(Policy.COMMIT_WAIT, epsilonMs = 3)
        short.sim.launch { short.settle(1) }
        short.sim.runUntil(8)
        assertThat(short.payouts.versionsOf("batch").last().committed)
            .`as`("2 x 3 ms is less than the 8 ms commit takes anyway: no added wait").isTrue()
    }

    @Test
    fun `trusting a fast clock hides a payment that committed before the audit began`() {
        val c = Cluster(Policy.TRUST_CLOCK, epsilonMs = 10)
        c.sim.launch { c.settle(1) }                      // committed at the writer's 10 ms, acknowledged at 8 ms
        var seen: Audit? = null
        c.sim.at(9) { c.sim.launch { seen = c.audit(c.readers[0]) } }   // a clock 10 ms behind reads at -1
        c.sim.runUntil(100)
        assertThat(seen).isEqualTo(Audit(payout = 0, ledger = 0, restarts = 0, waitedMs = 0))
    }

    @Test
    fun `restarting above an uncertain version finds the payment`() {
        val c = Cluster(Policy.RESTART, epsilonMs = 10)
        c.sim.launch { c.settle(1) }
        var seen: Audit? = null
        c.sim.at(9) { c.sim.launch { seen = c.audit(c.readers[0]) } }
        c.sim.runUntil(100)
        assertThat(seen).isEqualTo(Audit(payout = 1, ledger = 1, restarts = 1, waitedMs = 0))
    }

    @Test
    fun `a reader that meets an intent waits for it instead of reading half a transaction`() {
        val c = Cluster(Policy.TRUST_CLOCK, epsilonMs = 0)
        c.sim.launch { c.settle(1) }                      // acknowledged at 8; payouts resolves at 8, ledger at 9
        var seen: Audit? = null
        c.sim.at(6) { c.sim.launch { seen = c.audit(c.readers[0]) } }   // reads at 8, after payouts resolved
        c.sim.runUntil(100)
        assertThat(seen).isEqualTo(Audit(payout = 1, ledger = 1, restarts = 0, waitedMs = 1))
    }

    // ---------------------------------------------------------------- ten seconds of traffic

    @Test
    fun `trusting the clocks is fast and stale`() {
        val s = stats(Policy.TRUST_CLOCK, epsilon = 10)
        assertThat(s.staleReads).isGreaterThan(0)
        assertThat(s.fracturedReads).`as`("intents still keep each audit atomic").isZero()
        assertThat(s.restarts).isZero()
        assertThat(s.meanWriteMs).isEqualTo(8.0)
    }

    @Test
    fun `commit wait makes every write wait and no read restart`() {
        val s = stats(Policy.COMMIT_WAIT, epsilon = 10)
        assertThat(s.staleReads).isZero()
        assertThat(s.fracturedReads).isZero()
        assertThat(s.restarts).isZero()
        assertThat(s.meanWriteMs).`as`("2 x epsilon").isEqualTo(20.0)
    }

    @Test
    fun `restarts make some reads pay and no write wait`() {
        val s = stats(Policy.RESTART, epsilon = 10)
        assertThat(s.staleReads).isZero()
        assertThat(s.fracturedReads).isZero()
        assertThat(s.restarts).isGreaterThan(0)
        assertThat(s.meanWriteMs).isEqualTo(8.0)
    }

    @Test
    fun `with perfect clocks the three policies cost the same and none is stale`() {
        val all = Policy.entries.map { stats(it, epsilon = 0) }
        assertThat(all.map { it.staleReads }).containsOnly(0)
        assertThat(all.map { it.restarts }).containsOnly(0)
        assertThat(all.map { it.meanWriteMs }).containsOnly(8.0)
    }

    @Test
    fun `the price grows with the clock bound`() {
        val bounds = listOf(2L, 10L, 50L)
        val restarts = bounds.map { stats(Policy.RESTART, it).restarts }
        assertThat(restarts).isSorted()
        assertThat(restarts.first()).isLessThan(restarts.last())
        val waits = bounds.map { stats(Policy.COMMIT_WAIT, it).meanWriteMs }
        assertThat(waits).containsExactly(8.0, 20.0, 100.0)
    }
}
