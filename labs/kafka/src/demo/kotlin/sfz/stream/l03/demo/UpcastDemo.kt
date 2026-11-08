package sfz.stream.l03.demo

import java.math.BigDecimal

/**
 * Lesson stream-03, Try it 4: three ways to read an event that last year's code wrote. The stored
 * events are maps, as JSON objects would be; the current reader wants MoneyWithdrawn version 2,
 * {accountId, amountMinor, currency}. Version 1 was {accountId, amount} with euros as text.
 */

data class Stored(val position: Long, val type: String, val schemaVersion: Int, val data: Map<String, String>)

val storedLog = listOf(
    Stored(1, "MoneyWithdrawn", 1, mapOf("accountId" to "acct-17", "amount" to "80.00")),        // last year
    Stored(2, "MoneyWithdrawn", 2, mapOf("accountId" to "acct-17", "amountMinor" to "1250", "currency" to "EUR")),
)

/** Today's reader: it knows only version 2. */
fun strictRead(e: Stored): Long = e.data["amountMinor"]?.toLong() ?: error("position ${e.position}: no field amountMinor")

/** A weak schema: read what you can, fall back on what you know about older shapes. */
fun tolerantRead(e: Stored): Long =
    e.data["amountMinor"]?.toLong() ?: BigDecimal(e.data.getValue("amount")).movePointRight(2).longValueExact()

/** An upcaster: turn version 1 into version 2 as it is read, so the rest of the code sees one shape. */
fun upcast(e: Stored): Stored =
    if (e.type == "MoneyWithdrawn" && e.schemaVersion == 1) {
        e.copy(
            schemaVersion = 2,
            data = mapOf(
                "accountId" to e.data.getValue("accountId"),
                "amountMinor" to BigDecimal(e.data.getValue("amount")).movePointRight(2).longValueExact().toString(),
                "currency" to "EUR",
            ),
        )
    } else e

fun main() {
    for (e in storedLog) {
        val strict = runCatching { strictRead(e) }.fold({ "$it" }, { "fails: ${it.message}" })
        println("position ${e.position}, schema ${e.schemaVersion}: strict reader $strict")
    }
    println("tolerant reader:        ${storedLog.map(::tolerantRead)}")
    println("upcast, then strict:    ${storedLog.map(::upcast).map(::strictRead)}")
    println("upcast event 1:         ${upcast(storedLog[0])}")
    println("stored event 1 is still ${storedLog[0]}")
    // copy and replace: write a new stream with every event upcast, check it, then point readers at it
    val copied = storedLog.map(::upcast)
    println("copy and replace:       new stream of ${copied.size} events, all schema ${copied.map { it.schemaVersion }.distinct()}")
}
