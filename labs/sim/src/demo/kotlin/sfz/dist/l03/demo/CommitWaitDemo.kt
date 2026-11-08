package sfz.dist.l03.demo

/**
 * Lesson dist-03, section 4: commit wait with clocks that report their error.
 *
 * The same causal chain as LwwDemo: 1,000 writes alternating between two pods, 0 to 50 ms of think
 * time. pod-b's clock is behind by the full amount of its error bound, the worst an honest bound
 * allows. Both pods sync every second, so each bound stays at its value plus about 1 ms of assumed
 * drift. Each pod stamps a write with the latest time its clock allows and waits until the earliest
 * time has passed the stamp. The last row lies: pod-b is 20 ms behind but claims a 5 ms bound.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l03.demo.CommitWaitDemoKt
 */
fun main() {
    println("%-34s %8s %18s %18s".format("pod-b's clock", "lost", "pod-a waits (avg)", "pod-b waits (avg)"))
    val rows = listOf(
        "1 ms behind, bound 1 ms" to (-1L to 1L),
        "4 ms behind, bound 4 ms" to (-4L to 4L),
        "7 ms behind, bound 7 ms" to (-7L to 7L),
        "20 ms behind, bound 20 ms" to (-20L to 20L),
        "250 ms behind, bound 250 ms" to (-250L to 250L),
        "20 ms behind, bound claims 5 ms" to (-20L to 5L),
    )
    for ((label, cfg) in rows) {
        val (offset, bound) = cfg
        val sim = Sim(7)
        val store = Store(sim)
        // pod-a is exactly right but doesn't know it: it also carries a bound, 1 ms
        val a = Writer("pod-a", DriftingClock(sim, offsetMs = 0, boundMs = 1), sim, store)
        val b = Writer("pod-b", DriftingClock(sim, offsetMs = offset, boundMs = bound), sim, store)
        for (t in 1_000L..1_000_000L step 1_000L) sim.at(sim.now + t) {
            a.clock.sync(residualMs = 0, boundMs = 1)
            b.clock.sync(residualMs = offset, boundMs = bound)       // the same offset, the same belief
        }
        val r = causalChain(sim, store, listOf(a, b), rounds = 1_000, commitWait = true, maxThinkMs = 50)
        val aw = r.waitsMs.filterIndexed { i, _ -> i % 2 == 0 }.average()
        val bw = r.waitsMs.filterIndexed { i, _ -> i % 2 == 1 }.average()
        println("%-34s %8d %15.1f ms %15.1f ms".format(label, r.lost.size, aw, bw))
    }
}
