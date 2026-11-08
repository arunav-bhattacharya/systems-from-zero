package sfz.stream.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * Lesson stream-03, exercises 3 to 5: old events read through an upcaster (Account.kt), a read
 * model added after the fact, and what compaction keeps (Projections.kt).
 *
 * The history: last year's service wrote MoneyWithdrawn with schema 1 (`amount` in euros); this
 * year's writes schema 2 (`amountMinor` in cents, plus `currency`).
 */
class ReadModelTest {

    private val store = EventStore().apply {
        appendRaw("account-acct-17", "AccountOpened", 1, mapOf("accountId" to "acct-17", "owner" to "Mira Okafor"))
        appendRaw("account-acct-17", "MoneyDeposited", 1, mapOf("accountId" to "acct-17", "amountMinor" to "250000"))
        appendRaw("account-acct-17", "MoneyWithdrawn", 1, mapOf("accountId" to "acct-17", "amount" to "800.00"))   // last year
        appendRaw("account-acct-42", "AccountOpened", 1, mapOf("accountId" to "acct-42", "owner" to "Tomas Lind"))
        appendRaw("account-acct-42", "MoneyDeposited", 1, mapOf("accountId" to "acct-42", "amountMinor" to "90000"))
        appendRaw("account-acct-17", "MoneyWithdrawn", 1, mapOf("accountId" to "acct-17", "amount" to "12.50"))    // last year
    }
    private val service = AccountService(store)

    @Test
    fun `the upcaster turns a version 1 withdrawal into version 2`() {
        val old = store.read("account-acct-17")[2]
        val new = Upcaster.upcast(old)
        assertThat(new.schemaVersion).isEqualTo(2)
        assertThat(new.data).isEqualTo(mapOf("accountId" to "acct-17", "amountMinor" to "80000", "currency" to "EUR"))
        assertThat(listOf(new.stream, new.version, new.position, new.type)).isEqualTo(listOf(old.stream, old.version, old.position, old.type))
        assertThat(old.schemaVersion).describedAs("the stored event is never changed").isEqualTo(1)
    }

    @Test
    fun `current events pass through the upcaster untouched`() {
        service.handle(Withdraw("acct-42", 60_000))
        val current = store.read("account-acct-42").last()
        assertThat(current.schemaVersion).isEqualTo(2)
        assertThat(Upcaster.upcast(current)).isEqualTo(current)
        assertThat(Upcaster.upcast(store.read("account-acct-42").first())).isEqualTo(store.read("account-acct-42").first())
    }

    @Test
    fun `an account with old and new events loads correctly`() {
        service.handle(Withdraw("acct-17", 100_000))                      // written today, schema 2
        val loaded = service.load("acct-17")
        assertThat(loaded.state.balanceMinor).isEqualTo(250_000 - 80_000 - 1_250 - 100_000)
        assertThat(loaded.version).describedAs("four old events and one new").isEqualTo(5)
    }

    @Test
    fun `a new read model is built from the whole history, old events included`() {
        service.handle(Withdraw("acct-42", 60_000))
        service.handle(Withdraw("acct-17", 49_999))
        val large = Projector.rebuild(store, LargeWithdrawals(thresholdMinor = 50_000))
        assertThat(large.rows).containsExactly(
            LargeWithdrawals.Row(3, "acct-17", 80_000),                   // from last year's schema 1 event
            LargeWithdrawals.Row(7, "acct-42", 60_000),
        )
    }

    @Test
    fun `rebuilding twice gives the same read model`() {
        repeat(200) { service.handle(Deposit("acct-42", 60_000)); service.handle(Withdraw("acct-42", 50_000 + it.toLong())) }
        val first = Projector.rebuild(store, LargeWithdrawals()).rows
        val second = Projector.rebuild(store, LargeWithdrawals()).rows
        assertThat(first).describedAs("last year's 800.00 and this year's 200").hasSize(201)
        assertThat(second).isEqualTo(first)                // same log, same order, same read model
    }

    @Test
    fun `compacting a topic of events by account keeps only each account's last event`() {
        val events = store.readAll().map { Codec.decode(Upcaster.upcast(it)) }
        val truth = events.groupBy { it.accountId }.mapValues { (_, e) -> Account.replay(e).balanceMinor }

        val compacted = compactByKey(events.map { it.accountId to it })   // cleanup.policy=compact on the event topic
        val afterCompaction = compacted.groupBy({ it.first }, { it.second }).mapValues { (_, e) -> Account.replay(e).balanceMinor }

        assertThat(truth).isEqualTo(mapOf("acct-17" to 168_750L, "acct-42" to 90_000L))
        assertThat(afterCompaction).describedAs("one withdrawal and one deposit are all that is left").isEqualTo(mapOf("acct-17" to -1_250L, "acct-42" to 90_000L))
    }

    @Test
    fun `compacting a topic of full balances loses nothing`() {
        val events = store.readAll().map { Codec.decode(Upcaster.upcast(it)) }
        val records = balanceRecords(events)
        assertThat(records).hasSize(events.size)
        assertThat(records.first()).isEqualTo("acct-17" to 0L)
        assertThat(compactByKey(records)).containsExactly("acct-42" to 90_000L, "acct-17" to 168_750L)
    }
}
