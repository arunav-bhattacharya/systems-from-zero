package sfz.stream.l03.demo

/**
 * Lesson stream-03, Try it 1: one account as a table row, and the same account as a log of events.
 * The row holds the answer; the log also holds the reasons, and every earlier answer.
 */

sealed interface Event { val text: String }
data class Opened(val owner: String) : Event { override val text = "AccountOpened   owner=$owner" }
data class Deposited(val cents: Long, val ref: String) : Event { override val text = "MoneyDeposited  +${eur(cents)}  ref=$ref" }
data class Withdrawn(val cents: Long, val ref: String) : Event { override val text = "MoneyWithdrawn  -${eur(cents)}  ref=$ref" }

fun eur(cents: Long) = "%d.%02d".format(cents / 100, cents % 100)

/** The state is a fold: start from nothing and apply each event in order. */
fun balance(events: List<Event>): Long = events.fold(0L) { b, e ->
    when (e) {
        is Opened -> 0
        is Deposited -> b + e.cents
        is Withdrawn -> b - e.cents
    }
}

fun main() {
    val log = listOf(
        Opened("Mira Okafor"),
        Deposited(10_000, "salary-0301"),
        Withdrawn(3_000, "card pay-981"),
        Withdrawn(4_500, "card pay-982"),
        Deposited(4_500, "refund of pay-982"),
        Withdrawn(5_000, "transfer tx-77"),
    )
    println("the table:  accounts(id = 'acct-17', balance = ${eur(balance(log))})")
    println()
    println("the log:    stream account-acct-17")
    log.forEachIndexed { i, e ->
        println("  v${i + 1}  %-46s balance %7s".format(e.text, eur(balance(log.take(i + 1)))))
    }
    println()
    // a question the table can't answer: what was the balance before the transfer?
    println("balance as of v5 (before tx-77): ${eur(balance(log.take(5)))}")
    println("events that mention pay-982:     ${log.withIndex().filter { "pay-982" in it.value.text }.map { "v${it.index + 1}" }}")
}
