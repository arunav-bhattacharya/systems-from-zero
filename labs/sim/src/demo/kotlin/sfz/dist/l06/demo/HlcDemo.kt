package sfz.dist.l06.demo

/**
 * Lesson dist-06, section 3: how a hybrid logical clock behaves as the clocks disagree more. 20 histories of 500
 * events on 4 nodes; each node acts about every 10 ms and messages take 5 to 20 ms. For each skew: how often the
 * counter c is 0, 1 or more, its largest value, and how far l ran ahead of the node's own wall clock.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l06.demo.HlcDemoKt -q
 */
fun main() {
    println("max skew    c = 0    c = 1   c >= 2   max c   l - wall clock: max   mean")
    for (skew in listOf(1L, 3L, 9L, 30L, 100L)) {
        val counters = mutableListOf<Int>()
        val ahead = mutableListOf<Long>()
        for (seed in 1L..20L) {
            val h = Histories.generate(seed, nodes = 4, events = 500, maxSkewMs = skew, delayMs = 5L..20L, meanGapMs = 10)
            val hlc = hlcStamps(h)
            for ((i, e) in h.events.withIndex()) {
                counters += hlc[i].c
                ahead += hlc[i].l - e.physical
            }
        }
        fun pct(n: Int) = "%5.1f%%".format(100.0 * n / counters.size)
        println("%5d ms   %s   %s   %s   %5d   %16d ms   %4.1f ms".format(
            skew, pct(counters.count { it == 0 }), pct(counters.count { it == 1 }), pct(counters.count { it >= 2 }),
            counters.max(), ahead.max(), ahead.average()))
    }
}
