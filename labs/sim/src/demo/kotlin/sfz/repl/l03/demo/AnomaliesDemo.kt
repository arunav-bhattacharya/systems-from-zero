package sfz.repl.l03.demo

/**
 * Lesson repl-03: each replication-lag anomaly as a timeline, then the same reads with the fix.
 * Run one part at a time:
 *   ./gradlew :sim:demo -Pmain=sfz.repl.l03.demo.AnomaliesDemoKt -Pargs='lag'
 *   ./gradlew :sim:demo -Pmain=sfz.repl.l03.demo.AnomaliesDemoKt -Pargs='monotonic'
 *   ./gradlew :sim:demo -Pmain=sfz.repl.l03.demo.AnomaliesDemoKt -Pargs='prefix'
 * A second argument changes the lag in ms: of r2 for 'lag' and 'monotonic', of shard 0's follower for 'prefix'.
 */
fun main(args: Array<String>) {
    val lag = args.getOrNull(1)?.toLong()
    when (args.firstOrNull() ?: "lag") {
        "lag" -> lag(lag ?: 900)
        "monotonic" -> monotonic(lag ?: 900)
        "prefix" -> prefix(lag ?: 400)
        else -> println("say lag, monotonic or prefix")
    }
}

/** Positions over time: a follower's lag in log positions and what a read there returns. */
private fun lag(r2Lag: Long) {
    val leader = Leader()
    val r1 = Replica("r1", 20, leader)
    val r2 = Replica("r2", r2Lag, leader)
    for (n in 1..20) leader.write(n * 100L, "pay-$n", "captured")
    println("a payment captured every 100 ms; r1 is 20 ms behind, r2 is $r2Lag ms behind")
    println("%8s %8s %10s %10s %24s".format("time", "leader", "r1", "r2", "pay-15 on r2"))
    for (t in listOf(500L, 1_000L, 1_500L, 2_000L, 2_500L, 3_000L)) {
        val p2 = r2.position(t)
        println("%5d ms %8d %10d %10d %24s".format(t, leader.position(t), r1.position(t), p2, r2.valueAt("pay-15", p2) ?: "not there"))
    }
    println("once the writes stop at 2,000 ms, both followers converge: that is all \"eventually consistent\" promises")
}

private fun monotonic(r2Lag: Long) {
    val leader = Leader()
    val r1 = Replica("r1", 20, leader)
    val r2 = Replica("r2", r2Lag, leader)
    val replicas = listOf(r1, r2)
    val client = Client(leader)
    client.write(Session("payments-service"), 0, "pay-9", "authorized")
    client.write(Session("payments-service"), 1_000, "pay-9", "captured")
    for (fixed in listOf(false, true)) {
        val ops = Session("ops")
        println(if (fixed) "with a session token (never below the highest position seen):" else "round robin, no token:")
        var previous = 0L
        var backwards = 0
        for (i in 0 until 6) {
            val now = 1_100L + 50 * i
            val route = if (fixed) monotonicReads(ops, replicas, leader, now) else Route(replicas[i % 2])
            val read = client.read(ops, now, "pay-9", route)
            val back = read.position < previous
            if (back) backwards++
            println("  %5d ms  %-6s at position %d: pay-9 is %-10s%s".format(now, read.node, read.position, read.value, if (back) " <- went back" else ""))
            previous = read.position
        }
        println("  went back $backwards times")
    }
}

private fun prefix(slowLag: Long) {
    for ((label, shardOf) in listOf<Pair<String, (PaymentEvent, Int) -> Int>>("a shard per event type" to ::shardByType, "a shard per payment" to ::shardFor)) {
        val leaders = listOf(Leader(), Leader())
        val followers = listOf(Replica("shard0", slowLag, leaders[0]), Replica("shard1", 20, leaders[1]))
        for (n in 1..20) {
            for ((type, at) in listOf("authorized" to n * 50L, "captured" to n * 50L + 30)) {
                val e = PaymentEvent("pay-$n", type)
                leaders[shardOf(e, 2)].write(at, e.paymentId, e.type)
            }
        }
        var anomalies = 0
        var first: String? = null
        for (now in 0L..2_000L step 10) {
            val seen = followers.flatMap { f -> f.entriesUpTo(f.position(now)) }
            val authorized = seen.filter { it.value == "authorized" }.map { it.key }.toSet()
            val bad = seen.filter { it.value == "captured" && it.key !in authorized }
            anomalies += bad.size
            if (first == null && bad.isNotEmpty()) first = "at $now ms the dashboard shows ${bad.first().key} captured, with no authorization"
        }
        println("$label (shard 0's follower $slowLag ms behind, shard 1's 20 ms):")
        println("  ${first ?: "no capture ever appears before its authorization"}")
        println("  captures without an authorization, summed over 201 refreshes: $anomalies")
    }
}
