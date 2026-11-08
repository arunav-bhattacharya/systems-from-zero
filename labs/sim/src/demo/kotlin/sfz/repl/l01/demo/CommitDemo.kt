package sfz.repl.l01.demo

/**
 * Lesson repl-01, section 2: what each replication mode costs per commit, and what a failover loses.
 *
 * One leader and two followers, a payment every 4 ms for one second, the leader dies at 1,001 ms
 * and the most up-to-date follower is promoted. Virtual time: the whole run takes milliseconds.
 * Run: ./gradlew :sim:demo -Pmain=sfz.repl.l01.demo.CommitDemoKt
 * Optional: -Pargs='2 70' sets the one-way delays (ms) to f1 and f2 (defaults 20 and 50).
 */
fun main(args: Array<String>) {
    val d1 = args.getOrNull(0)?.toLong() ?: 20
    val d2 = args.getOrNull(1)?.toLong() ?: 50
    println("leader -> f1 $d1 ms, leader -> f2 $d2 ms (one way); a payment every 4 ms; the leader dies at 1,001 ms")
    println()
    println("%-27s %10s %10s %8s %11s %5s".format("mode", "commit p50", "commit max", "said OK", "new leader", "lost"))
    val modes = listOf(
        "async" to Mode.Async,
        "sync, 1 of 2 followers" to Mode.Sync(1),
        "sync, both followers" to Mode.Sync(2),
        "semi-sync, timeout 500 ms" to Mode.SemiSync(500),
    )
    for ((label, mode) in modes) row(label, mode, mapOf("f1" to d1, "f2" to d2))
    println()
    println("The same semi-sync leader, with both followers stalled (600 and 700 ms away):")
    row("semi-sync, timeout 500 ms", Mode.SemiSync(500), mapOf("f1" to 600L, "f2" to 700L))
}

private fun row(label: String, mode: Mode, delays: Map<String, Long>) {
    val sim = Sim()
    val cluster = Cluster(sim, mode, delays)
    cluster.writeEvery(4, from = 0, until = 996)
    var switchedOff: Long? = null
    for (t in 0L..1_000L) sim.at(t) { if (switchedOff == null && !cluster.semiSyncOn) switchedOff = t }
    sim.at(1_001) { cluster.crash(cluster.leader) }
    sim.runUntil(1_001)
    val latencies = cluster.acknowledged.map { it.latencyMs }.sorted()
    val p50 = latencies.getOrNull(latencies.size / 2)?.let { "$it ms" } ?: "never"
    val max = latencies.lastOrNull()?.let { "$it ms" } ?: "never"
    val result = cluster.failover()
    println("%-27s %10s %10s %8d %11s %5d".format(label, p50, max, cluster.acknowledged.size,
        "${result.newLeader.name} at ${result.newLeader.position}", result.lost.size))
    switchedOff?.let { println("  semi-sync switched itself off at $it ms and stayed off: every later commit returned at once") }
}
