package sfz.stream.l03

/**
 * Lesson stream-03, exercises 4 and 5: read models built from the log, and what compaction does to
 * a log of events. [Projection], [Balances] and [Projector] are given.
 *
 * Check it: ./gradlew :kafka:solutionTest --tests 'sfz.stream.l03.*'   (from the labs folder)
 */

/** A read model: it sees every event once, in log order, and keeps whatever shape its readers need. */
interface Projection {
    fun apply(position: Long, event: AccountEvent)
}

/** The balance screen's read model (given): one number per account. */
class Balances : Projection {
    val byAccount: MutableMap<String, Long> = linkedMapOf()

    override fun apply(position: Long, event: AccountEvent) {
        when (event) {
            is AccountOpened -> byAccount[event.accountId] = 0
            is MoneyDeposited -> byAccount.merge(event.accountId, event.amountMinor, Long::plus)
            is MoneyWithdrawn -> byAccount.merge(event.accountId, -event.amountMinor, Long::plus)
        }
    }
}

/**
 * Exercise 4. The fraud team's new read model, added long after the events were written: every
 * withdrawal of at least [thresholdMinor] cents, in log order, as a [Row]. Ignore other events.
 */
class LargeWithdrawals(val thresholdMinor: Long = 50_000) : Projection {
    data class Row(val position: Long, val accountId: String, val amountMinor: Long)

    val rows: MutableList<Row> = mutableListOf()

    override fun apply(position: Long, event: AccountEvent) {
        if (event is MoneyWithdrawn && event.amountMinor >= thresholdMinor) {
            rows += Row(position, event.accountId, event.amountMinor)
        }
    }
}

object Projector {
    /** Builds [projection] from position 0: every event in the store, upcast and decoded, in order (given). */
    fun <P : Projection> rebuild(store: EventStore, projection: P): P {
        for (stored in store.readAll()) projection.apply(stored.position, Codec.decode(Upcaster.upcast(stored)))
        return projection
    }
}

/**
 * Exercise 5. Turns events into state records, as change data capture would: one record per event,
 * keyed by account id, whose value is that account's whole balance after the event. Because each
 * record carries the full state, a topic of them can be compacted to the last record per key.
 */
fun balanceRecords(events: List<AccountEvent>): List<Pair<String, Long>> {
    val state = HashMap<String, AccountState>()
    return events.map { e ->
        val after = Account.evolve(state[e.accountId] ?: AccountState(), e)
        state[e.accountId] = after
        e.accountId to after.balanceMinor          // the full balance, not the change: the latest record says it all
    }
}
