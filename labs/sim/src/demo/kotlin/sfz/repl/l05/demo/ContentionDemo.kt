package sfz.repl.l05.demo

import java.util.PriorityQueue
import kotlin.math.ln
import kotlin.random.Random

/**
 * Two regions, eu and us, each a leader. Clients add holds to merchant M-0042 by read-modify-write,
 * and every write is copied to the other region 20 to 80 ms later. Same seed, same run.
 *
 * For each write rate, it counts acknowledged holds that are missing at the end under last write
 * wins, and with conflict detection (keep concurrent versions as siblings, merge on read).
 * Pass a different seed with -Pargs='7'.
 */
private class W(val id: String, val region: String, val holds: Set<String>, val ts: Long, val seen: Set<String>)

private class Leader(val name: String, val detect: Boolean) {
    var versions = listOf<W>()
    val known = HashSet<String>()
    var n = 0
    fun read() = versions.flatMap { it.holds }.toSet()
    fun apply(w: W) {
        known += w.id; known += w.seen
        versions = if (!detect) {
            val cur = versions.singleOrNull()
            listOf(if (cur == null || compareValuesBy(w, cur, W::ts, W::region) > 0) w else cur)
        } else if (versions.any { it.id == w.id || w.id in it.seen }) versions // old news
        else versions.filter { it.id !in w.seen } + w // replace what it saw, keep the rest as siblings
    }
}

private fun lost(detect: Boolean, meanGapMs: Double, seed: Long, writesPerRegion: Int = 300): Int {
    val random = Random(seed)
    val leaders = listOf("eu", "us").associateWith { Leader(it, detect) }
    data class E(val at: Long, val seq: Int, val f: () -> Unit)
    val q = PriorityQueue<E>(compareBy({ it.at }, { it.seq }))
    var seq = 0
    val ids = mutableListOf<String>()
    for (r in leaders.keys) {
        var t = 0.0
        repeat(writesPerRegion) {
            t += -ln(1 - random.nextDouble()) * meanGapMs
            val at = t.toLong()
            q += E(at, seq++) {
                val l = leaders.getValue(r)
                val id = "$r:${++l.n}"
                val w = W(id, r, l.read() + id, at, l.known.toSet())
                ids += id
                l.apply(w)
                val other = leaders.getValue(if (r == "eu") "us" else "eu")
                q += E(at + random.nextLong(20, 81), seq++) { other.apply(w) }
            }
        }
    }
    while (q.isNotEmpty()) q.poll().f()
    val final = leaders.getValue("eu").read()
    check(final == leaders.getValue("us").read()) { "regions disagree" }
    return ids.count { it !in final }
}

fun main(args: Array<String>) {
    val seed = args.firstOrNull()?.toLong() ?: 42
    println("600 acknowledged writes (300 per region), lag 20 to 80 ms, seed $seed")
    println("mean gap between writes   last write wins lost   detector lost")
    for (gap in listOf(5_000.0, 1_000.0, 300.0, 100.0, 50.0, 10.0)) {
        val l = lost(false, gap, seed)
        val d = lost(true, gap, seed)
        println("%,10.0f ms per region  %6d  (%4.1f%%)        %6d".format(gap, l, 100.0 * l / 600, d))
    }
}
