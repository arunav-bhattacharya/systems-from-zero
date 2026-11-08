package sfz.dist.l06.demo

/**
 * Lesson dist-06, section 1: how often wall-clock timestamps put an effect before its cause, as the clocks drift
 * apart. 20 histories of 300 events on 4 nodes; messages take 1 to 20 ms. "Pairs" are all (a, b) where a happened
 * before b, found with vector clocks; "backwards" means b's wall-clock stamp is earlier than a's.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l06.demo.CausalityDemoKt -q
 */
fun main() {
    println("max skew   messages backwards   causal pairs backwards   Lamport backwards   HLC backwards")
    for (skew in listOf(0L, 2L, 5L, 10L, 20L, 50L)) {
        var messages = 0; var messagesBack = 0
        var pairs = 0L; var pairsBack = 0L; var lamportBack = 0L; var hlcBack = 0L
        for (seed in 1L..20L) {
            val h = Histories.generate(seed, nodes = 4, events = 300, maxSkewMs = skew, delayMs = 1L..20L)
            val vc = vectorStamps(h)
            val lamport = lamportStamps(h)
            val hlc = hlcStamps(h)
            val sendOf = h.events.filter { it.kind == Kind.SEND }.associateBy { it.msg }
            for (r in h.events.filter { it.kind == Kind.RECEIVE }) {
                messages++
                if (r.physical < sendOf.getValue(r.msg).physical) messagesBack++
            }
            for (a in h.events.indices) for (b in h.events.indices) if (vc[a] happenedBefore vc[b]) {
                pairs++
                if (h.events[b].physical < h.events[a].physical) pairsBack++
                if (lamport[b] < lamport[a]) lamportBack++
                if (hlc[b] < hlc[a]) hlcBack++
            }
        }
        println("%5d ms   %5d of %5d   %8d of %8d   %17d   %13d".format(skew, messagesBack, messages, pairsBack, pairs, lamportBack, hlcBack))
    }
}
