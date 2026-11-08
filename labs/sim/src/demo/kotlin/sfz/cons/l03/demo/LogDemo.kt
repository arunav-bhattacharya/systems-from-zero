package sfz.cons.l03.demo

/**
 * Lesson cons-03: a compare-and-set register on a total order broadcast.
 *   ./gradlew :sim:demo -Pmain=sfz.cons.l03.demo.LogDemoKt -q
 *   ./gradlew :sim:demo -Pmain=sfz.cons.l03.demo.LogDemoKt -Pargs=7 -q     another seed for the race
 *
 * Six booking services race to claim seat 12A with cas(null -> their name). Then 200 seeded runs of
 * three clients mixing CAS and reads, with reads through the log or straight from the home replica.
 */
fun main(args: Array<String>) {
    val seed = args.firstOrNull()?.toLong() ?: 3
    val sim = Sim(seed)
    val reg = LogRegister(Network(sim, minMs = 1, maxMs = 20))
    for (i in 1..6) {
        sim.after(sim.random.nextLong(0, 10)) {
            val sent = sim.now
            reg.cas("c$i", null, "c$i") { ok -> println("  %3d ms  c$i sent at %d ms: %s".format(sim.now, sent, if (ok) "got the seat" else "seat taken")) }
        }
    }
    println("seed $seed: six clients race for seat 12A")
    sim.run()
    for (r in reg.replicas) println("  ${r.name} applied ${r.applied.joinToString(" ") { it.client }}  ->  seat 12A belongs to ${r.value}")
    println()

    for (local in listOf(false, true)) {
        val bad = (1L..200L).count { !linearizable(history(it, local)) }
        println("reads ${if (local) "from the home replica, skipping the log" else "through the log"}: $bad of 200 histories not linearizable")
    }
}

private fun history(seed: Long, localReads: Boolean): List<Op> {
    val sim = Sim(seed)
    val reg = LogRegister(Network(sim, maxMs = 30))
    val ops = mutableListOf<Op>()
    var next = 1
    for (c in 1..3) {
        val client = "c$c"
        var left = 8
        var seen: String? = null
        fun go() {
            if (left-- == 0) return
            sim.after(sim.random.nextLong(0, 10)) {
                val start = sim.now
                if (sim.random.nextInt(3) == 0) {
                    val v = "v${next++}"
                    val expected = seen
                    reg.cas(client, expected, v) { ok ->
                        ops += Op(start, sim.now, cas = true, expected = expected, value = v, ok = ok)
                        if (ok) seen = v
                        go()
                    }
                } else {
                    val read: (String?) -> Unit = { v -> ops += Op(start, sim.now, cas = false, value = v); seen = v; go() }
                    if (localReads) reg.localRead(client, read) else reg.read(client, read)
                }
            }
        }
        go()
    }
    sim.run()
    return ops
}
