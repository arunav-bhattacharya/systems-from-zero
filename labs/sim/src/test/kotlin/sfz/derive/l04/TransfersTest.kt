package sfz.derive.l04

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** Exercise 3: a transfer across two partitions, made safe by one append, request ids and dedupe. */
class TransfersTest {
    private fun processor() = WalletProcessor(mapOf("w-a" to 1_000L, "w-b" to 0L))

    @Test
    fun `an affordable transfer is accepted, debited here, and its credit is sent with the same id`() {
        val p = processor()
        val sent = ArrayList<Credit>()
        val replies = ArrayList<Outcome>()
        p.handle(Requested(Transfer("t-1", "w-a", "w-b", 300)), sent::add, replies::add)
        assertThat(replies).containsExactly(Accepted("t-1"))
        assertThat(p.balances["w-a"]).isEqualTo(700)
        assertThat(sent).containsExactly(Credit("t-1", "w-b", 300))
        assertThat(p.balances["w-b"]).isEqualTo(0)              // the credit has not been read yet
    }

    @Test
    fun `a transfer the wallet cannot afford is declined and moves nothing`() {
        val p = processor()
        val sent = ArrayList<Credit>()
        val replies = ArrayList<Outcome>()
        p.handle(Requested(Transfer("t-1", "w-a", "w-b", 1_001)), sent::add, replies::add)
        assertThat(replies).containsExactly(Declined("t-1", "insufficient funds"))
        assertThat(sent).isEmpty()
        assertThat(p.balances["w-a"]).isEqualTo(1_000)
    }

    @Test
    fun `a request appended twice is decided once and answered the same way twice`() {
        val p = processor()
        val sent = ArrayList<Credit>()
        val replies = ArrayList<Outcome>()
        val req = Requested(Transfer("t-1", "w-a", "w-b", 300))
        p.handle(req, sent::add, replies::add)
        p.handle(req, sent::add, replies::add)
        assertThat(replies).containsExactly(Accepted("t-1"), Accepted("t-1"))
        assertThat(sent).hasSize(1)
        assertThat(p.balances["w-a"]).isEqualTo(700)
    }

    @Test
    fun `a credit delivered twice is applied once`() {
        val p = processor()
        p.handle(Credit("t-1", "w-b", 300), {}, {})
        p.handle(Credit("t-1", "w-b", 300), {}, {})
        assertThat(p.balances["w-b"]).isEqualTo(300)
        assertThat(p.hasCredit("t-1")).isTrue()
    }

    @Test
    fun `no money is created or lost, with crashes, replays and client retries`() {
        val run = runTransfers(TransferConfig())
        assertThat(run.crashes).isGreaterThan(0)
        assertThat(run.creditsSent).isGreaterThan(run.accepted)               // replays really sent duplicates
        assertIntegrity(run)
    }

    @Test
    fun `without crashes every credit is sent exactly once`() {
        val run = runTransfers(TransferConfig(crashChance = 0.0))
        assertThat(run.crashes).isZero()
        assertThat(run.creditsSent).isEqualTo(run.accepted)
        assertIntegrity(run)
    }

    @Test
    fun `the broken design, two separate non-idempotent steps, creates and loses money under the same faults`() {
        val run = runSeparateSteps(TransferConfig())
        assertThat(run.halfWritten).isGreaterThan(0)                          // debits whose credit was never written
        assertThat(run.reapplied).isGreaterThan(0)                            // steps applied twice after a crash
        assertThat(run.totalMoney).isNotEqualTo(run.config.expectedTotal)
    }

    @Test
    fun `even with no faults at all, a debit refused on its own lets its credit create money`() {
        val calm = TransferConfig(crashChance = 0.0, clientRetryChance = 0.0, apiCrashChance = 0.0)
        val run = runSeparateSteps(calm)
        assertThat(run.declinedDebits).isGreaterThan(0)
        assertThat(run.totalMoney).isGreaterThan(calm.expectedTotal)
        assertIntegrity(runTransfers(calm))                                   // one logged request: exact
    }

    @Property(tries = 20)
    fun `for any seed, money is conserved and every request is decided once`(@ForAll seed: Long) {
        assertIntegrity(runTransfers(TransferConfig(transfers = 300, seed = seed, crashChance = 0.02)))
    }

    private fun assertIntegrity(run: TransferRun) {
        val c = run.config
        assertThat(run.outcomes).hasSize(run.transfers.size)                  // every request got an answer
        assertThat(run.conflictingReplies).isZero()                           // and never two different ones
        assertThat(run.totalMoney).isEqualTo(c.expectedTotal)                 // nothing created, nothing lost
        assertThat(run.balances.values).allMatch { it >= 0 }                  // no wallet below zero
        val expected = (0 until c.wallets).associate { wallet(it) to c.initialBalance }.toMutableMap()
        for (t in run.transfers) if (run.outcomes[t.requestId] is Accepted) {
            expected[t.from] = expected.getValue(t.from) - t.amount
            expected[t.to] = expected.getValue(t.to) + t.amount
        }
        assertThat(run.balances).isEqualTo(expected)                          // each accepted transfer applied once
    }
}
