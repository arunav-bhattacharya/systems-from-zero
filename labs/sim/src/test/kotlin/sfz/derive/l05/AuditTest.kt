package sfz.derive.l05

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** Exercises 1 and 2: recompute the derived view from the log, then diff it against the live one. */
class AuditTest {
    private val log = Ledger.log(seed = 5)                    // 5,000 postings over 500 accounts

    @Test
    fun `recomputing from the log gives each account the sum of its postings`() {
        val view = recompute(listOf(Posting(0, "a", 1_250), Posting(1, "b", 700), Posting(2, "a", -250)))
        assertThat(view).isEqualTo(mapOf("a" to 1_000L, "b" to 700L))
    }

    @Test
    fun `a healthy live view and the recomputed one agree exactly`() {
        assertThat(diff(liveBalances(log), recompute(log))).isEmpty()
    }

    @Test
    fun `dropped records show up as accounts short by exactly the dropped amounts`() {
        val drift = diff(liveBalances(log, Fault.DropEvery(1_000)), recompute(log))
        val dropped = log.filter { (it.offset + 1) % 1_000 == 0 }
        assertThat(drift.map { it.account }).containsExactlyElementsOf(dropped.map { it.account }.toSortedSet())
        assertThat(drift.sumOf { it.delta }).isEqualTo(-dropped.sumOf { it.cents })
    }

    @Test
    fun `a non-idempotent redelivery shows up as accounts over by exactly the replayed amounts`() {
        val replayed = setOf(10, 11, 12, 4_000)
        val drift = diff(liveBalances(log, Fault.Redeliver(replayed)), recompute(log))
        val expected = log.filter { it.offset in replayed }.groupBy { it.account }.mapValues { (_, ps) -> ps.sumOf { it.cents } }
        assertThat(drift.associate { it.account to it.delta }).isEqualTo(expected)
    }

    @Test
    fun `one flipped bit is one account off by a power of two`() {
        val drift = diff(liveBalances(log, Fault.FlipBit(account(123), bit = 20)), recompute(log))
        assertThat(drift).hasSize(1)
        assertThat(drift[0].account).isEqualTo(account(123))
        assertThat(Math.abs(drift[0].delta)).isEqualTo(1L shl 20)
    }

    @Test
    fun `truncated cents spread across many accounts, each off by less than a unit per posting`() {
        val drift = diff(liveBalances(log, Fault.TruncateCents(from = 2_500)), recompute(log))
        assertThat(drift.size).isGreaterThan(300)
        val postings = log.filter { it.offset >= 2_500 }.groupingBy { it.account }.eachCount()
        for (d in drift) assertThat(Math.abs(d.delta)).isLessThan(100L * postings.getValue(d.account))
    }

    @Test
    fun `a row missing on one side is a drift too`() {
        val drift = diff(mapOf("a" to 5L), mapOf("a" to 5L, "b" to 7L))
        assertThat(drift).containsExactly(Drift("b", null, 7L))
        assertThat(drift[0].delta).isEqualTo(-7)
    }

    @Test
    fun `the drifts come back sorted by account`() {
        val drift = diff(liveBalances(log, Fault.TruncateCents(from = 0)), recompute(log))
        assertThat(drift.map { it.account }).isSorted()
    }
}
