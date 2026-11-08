package sfz.repl.l08.demo

import java.time.LocalTime
import java.time.temporal.ChronoUnit

/**
 * Five writes to payment pay-81723 and to merchant M-0042, each with the wall-clock time it was made
 * and the writes its writer had seen (directly, or carried to it by a message).
 *
 * The relation between two writes comes only from what was seen. The clock gap is printed next to
 * it so you can see how little the clock tells you.
 */
private class Event(val id: String, val what: String, val at: String, val seen: Set<String>) {
    val time: LocalTime = LocalTime.parse(at)
}

private fun relation(a: Event, b: Event) = when {
    a.id in b.seen -> "happens before: ${b.id} saw it, so ${b.id} may replace it"
    b.id in a.seen -> "happens after: it saw ${b.id}, so it may replace ${b.id}"
    else -> "CONCURRENT: neither saw the other; keep one and the other is lost"
}

private fun gap(a: Event, b: Event): String {
    val ms = ChronoUnit.MILLIS.between(a.time, b.time)
    return if (kotlin.math.abs(ms) >= 60_000) "%+d min".format(ms / 60_000) else "%+d ms".format(ms)
}

fun main() {
    val authorize = Event("eu:1", "authorize pay-81723", "10:00:00.000", emptySet())
    // the authorization reached the us service at 10:00:00.001, before it captured
    val capture = Event("us:1", "capture pay-81723", "10:00:00.002", setOf("eu:1"))
    // the ap service had heard of neither
    val void = Event("ap:1", "void pay-81723", "10:00:00.001", emptySet())
    // an agent's laptop, offline since 08:30, edits the merchant's payout account
    val laptop = Event("laptop:1", "M-0042 payout account", "09:00:00.000", emptySet())
    // the eu back office edits the same field an hour later, never having heard of the laptop's edit
    val office = Event("eu:2", "M-0042 payout account", "10:00:00.000", setOf("eu:1"))

    val pairs = listOf(authorize to capture, capture to void, authorize to void, laptop to office)
    for ((a, b) in pairs) {
        println("${a.id} (${a.what}, ${a.at}) vs ${b.id} (${b.what}, ${b.at})")
        println("    clock gap ${gap(a, b)}: ${relation(a, b)}")
    }
}
