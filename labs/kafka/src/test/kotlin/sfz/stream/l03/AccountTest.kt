package sfz.stream.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows

/**
 * Lesson stream-03, exercises 1 and 2, in src/main/kotlin/sfz/stream/l03/Account.kt. Account
 * acct-17 is opened with 100.00, and two handlers try to withdraw 80.00 at the same time.
 */
class AccountTest {

    private val store = EventStore()
    private val service = AccountService(store)

    private fun openWith100() {
        service.handle(OpenAccount("acct-17", "Mira Okafor"))
        service.handle(Deposit("acct-17", 10_000))
    }

    @Test
    fun `the state is the fold of the account's events`() {
        val state = Account.replay(
            listOf(
                AccountOpened("acct-17", "Mira Okafor"),
                MoneyDeposited("acct-17", 10_000),
                MoneyWithdrawn("acct-17", 3_000, "EUR"),
                MoneyDeposited("acct-17", 500),
            ),
        )
        assertThat(state).isEqualTo(AccountState(opened = true, owner = "Mira Okafor", balanceMinor = 7_500))
    }

    @Test
    fun `evolve never refuses an event, even one that overdraws`() {
        val state = Account.evolve(AccountState(opened = true, balanceMinor = 1_000), MoneyWithdrawn("acct-17", 4_000, "EUR"))
        assertThat(state.balanceMinor).isEqualTo(-3_000)   // a fact in the log is applied as it is
    }

    @Test
    fun `decide turns valid commands into events`() {
        val open = AccountState(opened = true, owner = "Mira Okafor", balanceMinor = 10_000)
        assertThat(Account.decide(AccountState(), OpenAccount("acct-17", "Mira Okafor"))).containsExactly(AccountOpened("acct-17", "Mira Okafor"))
        assertThat(Account.decide(open, Deposit("acct-17", 250))).containsExactly(MoneyDeposited("acct-17", 250))
        assertThat(Account.decide(open, Withdraw("acct-17", 10_000))).containsExactly(MoneyWithdrawn("acct-17", 10_000, "EUR"))
    }

    @Test
    fun `decide rejects what the rules forbid`() {
        val open = AccountState(opened = true, owner = "Mira Okafor", balanceMinor = 10_000)
        assertThrows<Rejected> { Account.decide(open, OpenAccount("acct-17", "Someone Else")) }
        assertThrows<Rejected> { Account.decide(AccountState(), Deposit("acct-17", 100)) }
        assertThrows<Rejected> { Account.decide(open, Deposit("acct-17", 0)) }
        assertThrows<Rejected> { Account.decide(open, Withdraw("acct-17", -5)) }
        assertThrows<Rejected> { Account.decide(open, Withdraw("acct-17", 10_001)) }
    }

    @Test
    fun `load folds the stream and reports the version it saw`() {
        openWith100()
        val loaded = service.load("acct-17")
        assertThat(loaded.state.balanceMinor).isEqualTo(10_000)
        assertThat(loaded.version).isEqualTo(2)
        assertThat(service.load("acct-99").version).describedAs("a stream that doesn't exist").isEqualTo(0)
    }

    @Test
    fun `without a version check, two withdrawals that each looked fine overdraw the account`() {
        openWith100()
        val seenByA = service.load("acct-17").state
        val seenByB = service.load("acct-17").state            // both read 100.00
        val fromA = Account.decide(seenByA, Withdraw("acct-17", 8_000))
        val fromB = Account.decide(seenByB, Withdraw("acct-17", 8_000))
        val both = Account.replay(store.read("account-acct-17").map(Codec::decode) + fromA + fromB)
        assertThat(both.balanceMinor).describedAs("what appending both would mean").isEqualTo(-6_000)
    }

    @Test
    fun `with the expected version, the second handler's append is refused`() {
        openWith100()
        val a = service.load("acct-17")
        val b = service.load("acct-17")
        service.execute(a, Withdraw("acct-17", 8_000))
        val conflict = assertThrows<WrongExpectedVersion> { service.execute(b, Withdraw("acct-17", 8_000)) }
        assertThat(conflict.expected to conflict.actual).isEqualTo(2L to 3L)
        assertThat(store.read("account-acct-17")).hasSize(3)
        assertThat(service.load("acct-17").state.balanceMinor).isEqualTo(2_000)
    }

    @Test
    fun `a retry after the conflict decides on fresh state and is rejected`() {
        openWith100()
        val stale = service.load("acct-17")
        service.handle(Withdraw("acct-17", 8_000))                       // another handler gets in first
        assertThrows<WrongExpectedVersion> { service.execute(stale, Withdraw("acct-17", 8_000)) }
        assertThrows<Rejected> { service.handle(Withdraw("acct-17", 8_000)) }   // 20.00 left: no
        assertThat(service.load("acct-17").state.balanceMinor).isEqualTo(2_000)
    }
}
