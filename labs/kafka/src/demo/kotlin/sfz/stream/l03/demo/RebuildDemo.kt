package sfz.stream.l03.demo

import kotlin.random.Random

/**
 * Lesson stream-03, Try it 3: what replay costs. One busy account with 200,000 events is loaded
 * from scratch and from a snapshot; then a brand-new read model is built over a log of 2,000,000
 * events. Events are stored as text and parsed on every read, as a real store would deserialize them.
 */

/** "D|acct-17|4000" or "W|acct-17|2500": a deposit or withdrawal, in cents. */
fun parse(line: String): Triple<Char, String, Long> {
    val a = line.indexOf('|')
    val b = line.indexOf('|', a + 1)
    return Triple(line[0], line.substring(a + 1, b), line.substring(b + 1).toLong())
}

fun applyTo(balance: Long, line: String): Long {
    val (type, _, cents) = parse(line)
    return if (type == 'D') balance + cents else balance - cents
}

/** Best of five runs, in milliseconds: the first runs also pay for the JIT compiler. */
fun timeMs(block: () -> Any): Double = (1..5).minOf { val t = System.nanoTime(); block(); (System.nanoTime() - t) / 1e6 }

fun main() {
    val random = Random(7)
    // one merchant settlement account with a long history
    val busy = List(200_000) { i -> if (i % 3 == 0) "W|acct-merchant-7|${random.nextLong(100, 900)}" else "D|acct-merchant-7|${random.nextLong(100, 900)}" }

    val full = timeMs { busy.fold(0L, ::applyTo) }
    val snapshotAt = busy.size - 100                                   // a snapshot every 1,000 events, the last one 100 events ago
    val snapshot = busy.take(snapshotAt).fold(0L, ::applyTo)            // stored once, read many times
    val fromSnapshot = timeMs { busy.drop(snapshotAt).fold(snapshot, ::applyTo) }
    check(busy.drop(snapshotAt).fold(snapshot, ::applyTo) == busy.fold(0L, ::applyTo))
    println("load acct-merchant-7 (200,000 events) from scratch:       %8.3f ms".format(full))
    println("load it from a snapshot at v%d + 100 events:          %8.3f ms".format(snapshotAt, fromSnapshot))

    // the whole store: 2,000,000 events over 50,000 accounts
    val log = List(2_000_000) { i -> "${if (i % 4 == 0) 'W' else 'D'}|acct-${random.nextInt(50_000)}|${random.nextLong(100, 90_000)}" }
    var large = 0
    val rebuild = timeMs {
        large = 0
        val balances = HashMap<String, Long>()
        for (line in log) {
            val (type, account, cents) = parse(line)
            balances.merge(account, if (type == 'D') cents else -cents, Long::plus)
            if (type == 'W' && cents >= 50_000) large++                      // the new "large withdrawals" view
        }
        balances
    }
    println("rebuild two read models from 2,000,000 events:            %8.1f ms  (%,d large withdrawals found)".format(rebuild, large))
}
