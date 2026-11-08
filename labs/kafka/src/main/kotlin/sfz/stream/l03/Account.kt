package sfz.stream.l03

/**
 * Lesson stream-03, exercises 1 to 3: an event-sourced account.
 *
 * The types and [Codec] at the top are given. Write [Account.evolve], [Account.decide],
 * [AccountService.load], [AccountService.execute] and [Upcaster.upcast].
 *
 * Check it: ./gradlew :kafka:test --tests 'sfz.stream.l03.*'   (from the labs folder)
 */

/** Events: facts that already happened, named in the past tense. Amounts are in cents. */
sealed interface AccountEvent {
    val accountId: String
}

data class AccountOpened(override val accountId: String, val owner: String) : AccountEvent
data class MoneyDeposited(override val accountId: String, val amountMinor: Long) : AccountEvent
data class MoneyWithdrawn(override val accountId: String, val amountMinor: Long, val currency: String) : AccountEvent

/** Commands: requests, in the imperative. The account may refuse them. */
sealed interface AccountCommand {
    val accountId: String
}

data class OpenAccount(override val accountId: String, val owner: String) : AccountCommand
data class Deposit(override val accountId: String, val amountMinor: Long) : AccountCommand
data class Withdraw(override val accountId: String, val amountMinor: Long) : AccountCommand

/** A command the account refused. Nothing is appended. */
class Rejected(message: String) : RuntimeException(message)

/** What the account needs to know to decide: the fold of its events. */
data class AccountState(val opened: Boolean = false, val owner: String? = null, val balanceMinor: Long = 0)

/**
 * Turns events into the store's form and back (given). The current schema of `MoneyWithdrawn` is
 * version 2: `{accountId, amountMinor, currency}`. Version 1, written by last year's service, was
 * `{accountId, amount}` with the amount in euros as a decimal string ("80.00"); [decode] refuses it,
 * so it must go through [Upcaster.upcast] first.
 */
object Codec {
    fun stream(accountId: String): String = "account-$accountId"

    fun encode(e: AccountEvent): NewEvent = when (e) {
        is AccountOpened -> NewEvent("AccountOpened", 1, mapOf("accountId" to e.accountId, "owner" to e.owner))
        is MoneyDeposited -> NewEvent("MoneyDeposited", 1, mapOf("accountId" to e.accountId, "amountMinor" to e.amountMinor.toString()))
        is MoneyWithdrawn -> NewEvent(
            "MoneyWithdrawn", 2,
            mapOf("accountId" to e.accountId, "amountMinor" to e.amountMinor.toString(), "currency" to e.currency),
        )
    }

    fun decode(s: StoredEvent): AccountEvent {
        val d = s.data
        return when (s.type) {
            "AccountOpened" -> AccountOpened(d.getValue("accountId"), d.getValue("owner"))
            "MoneyDeposited" -> MoneyDeposited(d.getValue("accountId"), d.getValue("amountMinor").toLong())
            "MoneyWithdrawn" -> {
                check(s.schemaVersion == 2) { "MoneyWithdrawn schema ${s.schemaVersion} at position ${s.position}: upcast it first" }
                MoneyWithdrawn(d.getValue("accountId"), d.getValue("amountMinor").toLong(), d.getValue("currency"))
            }
            else -> error("unknown event type ${s.type}")
        }
    }
}

object Account {

    /**
     * Exercise 1a. The state after [event]. Opening sets `opened` and the owner; a deposit adds to
     * the balance and a withdrawal subtracts. Never validate here: an event is a fact, and a fact
     * that is already in the log can't be refused.
     */
    fun evolve(state: AccountState, event: AccountEvent): AccountState {
        TODO("exercise 1a: apply one event to the state")
    }

    /**
     * Exercise 1b. Decides what happens when [command] meets [state]: the events to append, or a
     * [Rejected] exception. The rules:
     * - OpenAccount on an account that is already open is rejected; otherwise AccountOpened.
     * - Deposit and Withdraw on an account that isn't open are rejected, and so is an amount of 0 or less.
     * - Withdraw of more than the balance is rejected ("insufficient funds"); otherwise MoneyWithdrawn in EUR.
     * - Deposit gives MoneyDeposited.
     */
    fun decide(state: AccountState, command: AccountCommand): List<AccountEvent> {
        TODO("exercise 1b: validate the command against the state")
    }

    /** The state after all of [events], oldest first (given). */
    fun replay(events: List<AccountEvent>): AccountState = events.fold(AccountState(), ::evolve)
}

class AccountService(private val store: EventStore) {

    /** An account as one command handler loaded it: its state and the stream version it saw. */
    data class Loaded(val accountId: String, val state: AccountState, val version: Long)

    /**
     * Exercise 2a. Reads the account's stream ([Codec.stream]), upcasts each stored event
     * ([Upcaster.upcast]), decodes it ([Codec.decode]) and folds the events with [Account.evolve].
     * The version is the number of events read: the version of the last one, or 0.
     */
    fun load(accountId: String): Loaded {
        TODO("exercise 2a: read, upcast, decode, fold")
    }

    /**
     * Exercise 2b. Decides [command] against what [loaded] saw and appends the new events with
     * `expectedVersion = loaded.version`. If another handler appended to the stream since [loaded]
     * was read, the store throws [WrongExpectedVersion] and nothing is appended. Returns the events.
     */
    fun execute(loaded: Loaded, command: AccountCommand): List<AccountEvent> {
        TODO("exercise 2b: decide, then append with the expected version")
    }

    /** Loads, decides and appends; after a version conflict it loads the fresh state and tries once more (given). */
    fun handle(command: AccountCommand): List<AccountEvent> =
        try {
            execute(load(command.accountId), command)
        } catch (e: WrongExpectedVersion) {
            execute(load(command.accountId), command)
        }
}

object Upcaster {

    /**
     * Exercise 3. Rewrites an old event into the current schema as it is read; the stored event
     * itself never changes. `MoneyWithdrawn` schema 1 `{accountId, amount: "80.00"}` becomes schema 2
     * `{accountId, amountMinor: "8000", currency: "EUR"}` (version 1 only ever handled euros). Keep
     * everything else about the event (stream, version, position, type). Return any other event as it is.
     */
    fun upcast(e: StoredEvent): StoredEvent {
        TODO("exercise 3: MoneyWithdrawn v1 -> v2")
    }
}
