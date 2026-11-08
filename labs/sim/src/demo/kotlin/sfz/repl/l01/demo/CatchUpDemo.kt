package sfz.repl.l01.demo

/**
 * Lesson repl-01, section 3: a follower falls behind and catches up from its position.
 *
 * A payment every 10 ms; the link to f1 is cut from 200 to 500 ms. When it comes back, f1 sees a gap,
 * asks the leader for everything after its position, and applies it. Then the same again with a
 * leader that keeps only the last [keep] entries of its log, which is not enough.
 * Run: ./gradlew :sim:demo -Pmain=sfz.repl.l01.demo.CatchUpDemoKt
 * Optional: -Pargs='50' sets how many entries the leader keeps in the second run (default 20).
 */
fun main(args: Array<String>) {
    val keep = args.firstOrNull()?.toLong() ?: 20
    val sim = Sim()
    val cluster = Cluster(sim, Mode.Async, mapOf("f1" to 5L))
    val f1 = cluster.node("f1")
    cluster.writeEvery(10, from = 0, until = 990)
    sim.at(200) { cluster.cut += "f1" }
    sim.at(500) { cluster.cut -= "f1" }
    for (t in listOf(100L, 199L, 300L, 499L, 516L, 526L, 1_000L)) {
        sim.at(t) { println("%5d ms  leader at %3d, f1 at %3d%s".format(t, cluster.leader.position, f1.position, note(t))) }
    }
    sim.runUntil(1_100)

    println()
    println("Again, but the leader keeps only its last $keep log entries when f1 comes back:")
    val leader = Node("leader")
    val follower = Node("f1")
    val entries = (1L..100L).map { LogEntry(it, it, "pay-$it") }
    leader.apply(entries)
    follower.apply(entries.take(20))
    leader.truncateLogThrough(leader.position - keep)
    try {
        val got = follower.apply(leader.entriesAfter(follower.position))
        println("  f1 asks for entries after 20: applied $got, now at ${follower.position}")
    } catch (e: LogGoneException) {
        println("  f1 asks for entries after 20: ${e.message}")
        follower.restore(leader.snapshot())
        println("  f1 restored from a snapshot at position ${follower.position}; rows match the leader: ${follower.rows == leader.rows}")
    }
}

private fun note(t: Long) = when (t) {
    199L -> "   (the link to f1 is cut at 200 ms)"
    499L -> "   (the link comes back at 500 ms)"
    516L -> "   (entry 52 arrived at 515: f1 sees a gap after 20 and asks for everything after 20)"
    526L -> "   (entries 21 to 53 arrived at 525)"
    else -> ""
}
