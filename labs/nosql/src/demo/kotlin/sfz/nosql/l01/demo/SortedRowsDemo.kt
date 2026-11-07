package sfz.nosql.l01.demo

import java.util.TreeMap
import java.util.TreeSet

/** Bigtable keeps rows sorted by key. See what that order looks like, and what a prefix read returns. */
fun main() {
    // row key = merchant # time # payment id, written in the order the payments arrived
    val rows = TreeMap<String, String>()
    rows["M-0042#2026-11-07T10:30:12#pay-81730"] = "4250 EUR"
    rows["M-0043#2026-11-07T08:01:44#pay-81690"] = "1200 EUR"
    rows["M-0042#2026-11-06T23:59:58#pay-81655"] = "999 EUR"
    rows["M-0042#2026-11-07T08:15:03#pay-81701"] = "18000 EUR"
    rows["M-0041#2026-11-07T09:12:00#pay-81712"] = "450 EUR"
    rows["M-0042#2026-11-07T09:40:27#pay-81720"] = "7300 EUR"

    println("All rows, in the order the map keeps them:")
    rows.forEach { (key, value) -> println("  $key  $value") }

    // a range read: jump to the first key >= the prefix, walk forward, stop at the first miss
    val prefix = "M-0042#2026-11-07"
    println("Rows starting with $prefix:")
    rows.tailMap(prefix).entries
        .takeWhile { it.key.startsWith(prefix) }
        .forEach { println("  ${it.key}  ${it.value}") }

    // the classic row-key bug: numbers stored as text sort as text
    println("Unpadded: " + TreeSet(listOf("acct#9", "acct#10", "acct#2", "acct#100")))
    println("Padded:   " + TreeSet(listOf(9, 10, 2, 100).map { "acct#%06d".format(it) }))
}
