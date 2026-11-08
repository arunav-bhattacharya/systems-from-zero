package sfz.derive.l03.demo

import kotlin.random.Random

/**
 * Try it, derive-03 section 5: how long must the ledger remember a request id?
 *
 * 100,000 transfers, one id each, a tap every 10 ms. 3% of them are sent again later, after a
 * delay that is usually seconds, but some phones were in the background for an hour or offline
 * for days. The ledger forgets ids older than its window (pruning once a minute), so a retry
 * after the window is a new transfer. The last column sizes the id table for a service doing
 * 1,000 transfers a second, at an assumed 100 bytes per id (row plus index entry).
 */
fun main() {
    val random = Random(5)
    val n = 100_000
    val minute = 60_000L
    val hour = 60 * minute
    val retries = (0 until n).filter { random.nextDouble() < 0.03 }.map { i ->
        val r = random.nextDouble()
        val delay = when {
            r < 0.90 -> random.nextLong(30_000)                 // seconds: a timeout and a retry
            r < 0.98 -> random.nextLong(2 * hour)               // the app was in the background
            r < 0.995 -> random.nextLong(24 * hour)             // offline overnight
            else -> 24 * hour + random.nextLong(48 * hour)      // offline for days
        }
        i to delay
    }
    val events = ((0 until n).map { it * 10L to it } + retries.map { (i, d) -> i * 10L + d to i }).sortedBy { it.first }
    println("${"%,d".format(n)} transfers, ${"%,d".format(retries.size)} sent again later")
    println("%-10s %16s %26s".format("window", "duplicate rows", "id table at 1,000/s"))
    for ((label, window) in listOf("1 minute" to minute, "1 hour" to hour, "24 hours" to 24 * hour, "7 days" to 7 * 24 * hour)) {
        val ledger = Ledger(mapOf("a" to Long.MAX_VALUE / 2))
        var lastPrune = 0L
        for ((t, i) in events) {
            if (t - lastPrune >= minute) { ledger.prune(olderThan = t - window); lastPrune = t }
            ledger.postOnce(Row("req-$i", "a", "b", 1), now = t)
        }
        val ids = window / 1_000 * 1_000                         // ids written within one window
        val mb = ids * 100.0 / 1e6
        val size = if (mb < 1_000) "%,.0f MB".format(mb) else "%,.1f GB".format(mb / 1_000)
        println("%-10s %16d %26s".format(label, ledger.rows.size - n, "%,d ids, %s".format(ids, size)))
    }
}
