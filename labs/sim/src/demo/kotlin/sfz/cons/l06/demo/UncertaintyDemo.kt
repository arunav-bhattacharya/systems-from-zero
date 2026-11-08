package sfz.cons.l06.demo

/**
 * The cons-06 lab's two-range transaction on servers whose clocks disagree (a copy of the reference
 * solution, in Model.kt). The settlement job's clock is epsilon ahead; audit-0's is epsilon behind.
 *
 *   trust [epsilon]        one batch, then one audit 1 ms after the client was told: trusting the clocks
 *   commitwait [epsilon]   the same with Spanner-style commit wait
 *   restart [epsilon]      the same with CockroachDB-style uncertainty restarts
 *   sweep                  ten seconds of traffic per policy and clock bound: what each one costs
 *
 * Run from labs/: ./gradlew :sim:demo -Pmain=sfz.cons.l06.demo.UncertaintyDemoKt -Pargs='trust' -q
 */
fun main(args: Array<String>) {
    val scenario = args.getOrNull(0) ?: "trust"
    val epsilon = args.getOrNull(1)?.toLong() ?: 10
    when (scenario) {
        "trust" -> one(Policy.TRUST_CLOCK, epsilon)
        "commitwait" -> one(Policy.COMMIT_WAIT, epsilon)
        "restart" -> one(Policy.RESTART, epsilon)
        "sweep" -> sweep()
        else -> println("unknown scenario '$scenario': use trust, commitwait, restart or sweep")
    }
}

private fun one(policy: Policy, epsilon: Long) {
    val c = Cluster(policy, epsilon)
    c.trace = { println(it) }
    println("$policy, clocks within $epsilon ms of true time: settle runs $epsilon ms ahead, audit-0 $epsilon ms behind")
    c.sim.launch {
        c.settle(1)
        c.sim.sleep(1)                                     // the audit begins 1 ms after the client heard "paid"
        val a = c.audit(c.readers[0])
        println(if (a.payout < 1) "STALE: batch 1 was acknowledged before this audit began, and the audit missed it"
                else "fresh: the audit sees batch 1 (${a.restarts} restart(s), waited ${a.waitedMs} ms)")
    }
    c.sim.runUntil(1_000)
}

private fun sweep() {
    println("10 s of traffic: one settlement job, 4 auditors. Per policy and clock bound (epsilon, ms):")
    println("policy        eps   stale/1000   restarts/1000   write ms   audit ms")
    for (policy in Policy.entries) {
        for (eps in listOf(0L, 1L, 5L, 10L, 25L, 50L, 100L, 250L)) {
            val s = Cluster(policy, eps).run(10_000)
            println("%-12s %4d   %10.1f   %13.1f   %8.1f   %8.1f".format(
                policy, eps, 1000.0 * s.staleReads / s.audits, 1000.0 * s.restarts / s.audits, s.meanWriteMs, s.meanReadMs))
        }
    }
}
