package sfz.derive.l02.demo

import kotlin.random.Random

/**
 * Try it, derive-02 section 3: 2,000 merchant dashboards, polled or pushed.
 *
 * Ten minutes of payments, 50 a second, spread over 2,000 merchants. Each payment reaches the
 * derived "today's takings" view 50 to 150 ms after it commits. Every merchant has one dashboard
 * open. Polling: each dashboard asks every N seconds (at its own phase) and the answer takes
 * 40 ms to come back. Pushing: the server sends a diff over an open connection when the view
 * changes, 20 to 80 ms on the wire. "Staleness" is how long the screen shows an old total after
 * the payment committed.
 */
fun main() {
    val merchants = 2_000
    val seconds = 600
    val random = Random(42)
    val payments = (0 until seconds * 50).map { random.nextLong(seconds * 1_000L) to random.nextInt(merchants) }
    val viewAt = payments.map { (t, _) -> t + 50 + random.nextLong(101) }      // when the view changes
    val phase = LongArray(merchants) { random.nextLong(60_000) }

    fun pct(xs: List<Long>, p: Int) = xs.sorted()[(xs.size * p / 100).coerceAtMost(xs.size - 1)]

    println("%-18s %12s %18s %12s %12s".format("", "msgs/s", "answers unchanged", "stale p50", "stale p99"))
    for (every in listOf(1_000L, 5_000L, 30_000L)) {
        val usefulPolls = HashSet<Pair<Int, Long>>()                          // polls that saw a change
        val stale = payments.indices.map { i ->
            val (t, m) = payments[i]
            val base = phase[m] % every
            val nextPoll = base + ((viewAt[i] - base + every - 1) / every) * every    // first poll after the change
            usefulPolls += m to nextPoll
            nextPoll + 40 - t
        }
        val polls = merchants.toLong() * seconds * 1_000 / every
        val changedPolls = usefulPolls.size
        println("%-18s %,12d %17.1f%% %9.2f s %9.2f s".format(
            "poll every ${every / 1000} s", polls / seconds, 100.0 * (polls - changedPolls) / polls,
            pct(stale, 50) / 1000.0, pct(stale, 99) / 1000.0))
    }
    val pushed = payments.indices.map { i -> viewAt[i] + 20 + random.nextLong(61) - payments[i].first }
    println("%-18s %,12d %17.1f%% %9.2f s %9.2f s".format(
        "push diffs", payments.size / seconds, 0.0, pct(pushed, 50) / 1000.0, pct(pushed, 99) / 1000.0))
}
