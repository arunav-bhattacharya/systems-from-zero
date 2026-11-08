package sfz.repl.l01.demo

/**
 * Lesson repl-01, section 4: a failover step by step, and the GitHub 2012 hazard of reused ids.
 *
 * The service writes a payment every 4 ms and, once the database says OK, caches id -> payment in a
 * separate store (Redis, say). The leader dies at 1,001 ms; the most up-to-date follower takes over
 * and the service writes four more payments.
 * Run: ./gradlew :sim:demo -Pmain=sfz.repl.l01.demo.FailoverDemoKt
 * Optional: -Pargs='sync' waits for one follower instead of replicating asynchronously.
 */
fun main(args: Array<String>) {
    val mode = if (args.firstOrNull() == "sync") Mode.Sync(1) else Mode.Async
    val sim = Sim()
    val cluster = Cluster(sim, mode, mapOf("f1" to 20L, "f2" to 50L))
    val cache = mutableMapOf<Long, String>()
    cluster.writeEvery(4, from = 0, until = 996)
    sim.at(1_001) { cluster.crash(cluster.leader) }
    sim.runUntil(1_001)
    cluster.acknowledged.forEach { cache[it.entry.id] = it.entry.payment }

    println("mode: ${if (mode == Mode.Async) "asynchronous" else "wait for 1 of 2 followers"}")
    println("1,001 ms  the leader dies at position ${cluster.leader.position}; clients have heard OK for ${cluster.acknowledged.size} payments")
    for (f in cluster.followers) println("          ${f.name} has applied up to position ${f.position}")

    val result = cluster.failover()
    println("          promote ${result.newLeader.name}, the most up to date; its next id is ${result.newLeader.nextId}")
    println("          acknowledged but not on ${result.newLeader.name}: ${result.lost.map { it.entry.payment }.ifEmpty { listOf("none") }}")

    val before = cluster.acknowledged.size
    for (n in 1..4) sim.at(1_100L + n) { cluster.write("refund-$n") }
    sim.runUntil(1_200)
    println()
    for (ack in cluster.acknowledged.drop(before)) {
        val cached = cache[ack.entry.id]
        val clash = if (cached != null && cached != ack.entry.payment) "  <- the cache says id ${ack.entry.id} is $cached" else ""
        println("%5d ms  the new leader stores %s as id %d%s".format(ack.ackedAt, ack.entry.payment, ack.entry.id, clash))
    }
}
