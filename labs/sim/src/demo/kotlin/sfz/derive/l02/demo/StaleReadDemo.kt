package sfz.derive.l02.demo

import java.util.PriorityQueue
import kotlin.random.Random

/**
 * Try it, derive-02 section 4: read your own write from a derived view.
 *
 * The lab's experiment, with its reference answers built in. 1,000 users each send a transfer at
 * a random moment in one minute; the response reaches the phone 5 ms later, and 0 to 60 ms after
 * that the app reads the user's own balance from the derived view. The view's processor polls the
 * log every P ms (plus or minus 10 ms). First the read is answered from the view as it is
 * ("now"), then it waits until the view has applied the user's own offset ("after my offset").
 *
 * Pass poll intervals in ms to try others: -Pargs="10 50 200"
 */
fun main(args: Array<String>) {
    val intervals = args.map { it.toLong() }.ifEmpty { listOf(10L, 50L, 200L) }
    println("%-8s %-24s %-28s".format("poll", "read now", "read after my offset"))
    for (p in intervals) {
        val now = experiment(2026, p, waitForOffset = false)
        val waited = experiment(2026, p, waitForOffset = true)
        val w = waited.map { it.second }.sorted()
        println("%-8s %-24s %-28s".format(
            "$p ms",
            "${now.count { it.first }} of 1,000 stale",
            "${waited.count { it.first }} stale, p50 ${w[499]} ms, p99 ${w[989]} ms"))
    }
}

/** Returns, per read, (was it stale, how long it waited). */
private fun experiment(seed: Long, pollMs: Long, waitForOffset: Boolean): List<Pair<Boolean, Long>> {
    val random = Random(seed)
    val queue = PriorityQueue(compareBy<Triple<Long, Long, () -> Unit>>({ it.first }, { it.second }))
    var seq = 0L
    var clock = 0L
    fun at(t: Long, f: () -> Unit) { queue += Triple(t, seq++, f) }

    var logEnd = -1L                                            // offset of the last write
    var applied = -1L                                           // offset the view has applied
    val parked = ArrayList<Triple<Long, Long, (Long) -> Unit>>() // (offset, asked at, reply)
    val reads = ArrayList<Pair<Boolean, Long>>()

    repeat(1_000) {
        val t = random.nextLong(60_000)
        random.nextInt(50); random.nextInt(49); random.nextLong(9_900)   // from, to, cents: unused here
        val think = random.nextLong(61)
        at(t) {
            val offset = ++logEnd                               // the write path: append, get an offset
            at(clock + 5 + think) {
                val asked = clock
                if (!waitForOffset || applied >= offset) reads += (applied < offset) to 0L
                else parked += Triple(offset, asked) { answeredAt -> reads += false to (answeredAt - asked) }
            }
        }
    }
    fun poll() {
        applied = logEnd                                        // apply everything new
        val ready = parked.filter { it.first <= applied }
        parked.removeAll(ready)
        ready.forEach { it.third(clock) }
        at(clock + pollMs - 10 + random.nextLong(21)) { poll() }
    }
    at(pollMs) { poll() }
    while (queue.isNotEmpty() && queue.peek().first <= 61_000) {
        val (t, _, f) = queue.poll()
        clock = t
        f()
    }
    return reads
}
