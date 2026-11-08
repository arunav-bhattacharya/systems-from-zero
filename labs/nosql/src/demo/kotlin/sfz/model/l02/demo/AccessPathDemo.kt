package sfz.model.l02.demo

import java.util.TreeMap

/** The key of payment number i: accountId # createdAt # paymentId. */
private fun keyOf(i: Int): String {
    val account = "A-%05d".format(i % 10_000)
    val createdAt = "2026-11-%02dT%02d:%02d".format(1 + i % 7, (i / 7) % 24, (i / 168) % 60)
    return "$account#$createdAt#pay-$i"
}

/** 200,000 payments in one sorted map, keyed account#time#payment. Three questions, three costs. */
fun main() {
    // the value is the merchant, which is NOT part of the key
    val payments = TreeMap<String, String>()
    for (i in 0 until 200_000) payments[keyOf(i)] = "M-%04d".format(i % 997)

    fun timed(label: String, block: () -> Pair<Int, Int>) {
        var result = 0 to 0
        val nanos = (1..21).map { // run it 21 times, report the median
            val t0 = System.nanoTime()
            result = block()
            System.nanoTime() - t0
        }.sorted()[10]
        println("%-34s found %4d, touched %,7d entries, about %,9d ns".format(label, result.first, result.second, nanos))
    }

    // 1. the full key: one lookup
    val oneKey = keyOf(160_042)
    timed("key lookup (full key)") {
        (if (payments[oneKey] != null) 1 else 0) to 1
    }

    // 2. the account is the key's prefix: one contiguous slice, read from the end for newest first
    timed("A-00042's newest 20 (range read)") {
        val slice = payments.subMap("A-00042#", true, "A-00042$", false).descendingMap() // '$' comes right after '#'
        val newest = slice.entries.take(20)
        newest.size to newest.size
    }

    // 3. the merchant is not in the key: nothing to jump to, so look at everything
    timed("merchant M-0042's payments (scan)") {
        var touched = 0
        var found = 0
        for ((_, merchant) in payments) {
            touched++
            if (merchant == "M-0042") found++
        }
        found to touched
    }
}
