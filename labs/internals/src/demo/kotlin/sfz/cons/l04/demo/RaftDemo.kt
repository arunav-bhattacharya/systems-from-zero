package sfz.cons.l04.demo

import sfz.cons.l04.Cluster
import sfz.cons.l04.Role
import sfz.cons.l04.Timing
import sfz.cons.l04.name

/**
 * Runs the cons-04 lab's Raft simulator (the reference solution) and prints a timeline. Five servers,
 * n1 to n5, on a simulated network: every message takes 1 to 10 ms, the clock is simulated, and the seed
 * fixes every random choice, so each run prints the same story.
 *
 *   election     the first election, with random timeouts of 150 to 300 ms (the default)
 *   split        every timeout exactly 150 ms and every message exactly 5 ms: votes split forever
 *   replicate    entries replicated with 10% message loss; followers crash until there is no majority
 *   partition    the leader is cut off, takes a write it can't commit, and loses it when it comes back
 *
 * Run from labs/: ./gradlew :internals:demo -Pmain=sfz.cons.l04.demo.RaftDemoKt -Pargs='election' -q
 * Add a seed to see another run: -Pargs='election 7'
 */
fun main(args: Array<String>) {
    val scenario = args.getOrNull(0) ?: "election"
    val seed = args.getOrNull(1)?.toLong()
    when (scenario) {
        "election" -> election(seed ?: 1)
        "split" -> split(seed ?: 1)
        "replicate" -> replicate(seed ?: 2)
        "partition" -> partition(seed ?: 4)
        else -> println("unknown scenario '$scenario': use election, split, replicate or partition")
    }
}

private fun election(seed: Long) {
    val c = Cluster(seed = seed)
    c.runUntil(5_000) { it.leader() != null }
    c.runFor(80)
    printEvents(c)
    printState(c)
}

private fun split(seed: Long) {
    val c = Cluster(seed = seed, minDelay = 5, maxDelay = 5, timing = Timing(electionTimeoutMin = 150, electionTimeoutMax = 150))
    c.runFor(10_000)
    // the first two rounds, with each round's 20 refusals summed up in one line
    for (e in c.events.filter { it.substring(2, 7).trim().toLong() < 400 }) {
        if ("refuses" !in e) println(e)
        else if ("refuses n1 " in e && e.contains("  n2  ")) {
            val t = e.substring(0, 7)
            val term = e.substringAfterLast("term ")
            val n = c.events.count { it.startsWith(t) && "refuses" in it }
            println("$t  all $n refusals: every server already voted for itself in term $term")
        }
    }
    println("...")
    val elections = c.events.count { "starts an election" in it }
    println("after %,d ms: %d elections started, highest term %d, leader: %s".format(
        c.now, elections, c.nodes.maxOf { it.currentTerm }, c.leader()?.let { name(it.id) } ?: "none"))
}

private fun replicate(seed: Long) {
    val c = Cluster(seed = seed, lossRate = 0.1)
    c.runUntil(5_000) { it.leader() != null }
    c.runFor(20)
    val leader = c.leader()!!
    for (i in 1..3) { c.propose("pay-$i"); c.runFor(5) }
    c.runFor(100)
    val followers = c.nodes.filter { it !== leader }.map { it.id }
    c.crash(followers[0]); c.crash(followers[1])
    c.propose("pay-4")
    c.runFor(150)
    c.crash(followers[2])
    c.propose("pay-5")
    c.runFor(300)
    c.restart(followers[0])
    c.runFor(300)
    printEvents(c)
    printState(c)
    println("messages sent: %,d, lost: %,d".format(c.messagesSent, c.messagesLost))
}

private fun partition(seed: Long) {
    val c = Cluster(seed = seed)
    c.runUntil(5_000) { it.leader() != null }
    c.runFor(20)
    c.propose("pay-1")
    c.runFor(100)
    val old = c.leader()!!
    c.isolate(old.id)
    c.proposeTo(old.id, "pay-2")                     // a client that still talks to the old leader
    c.runUntil(5_000) { it.leader() != null }
    c.runFor(20)
    c.propose("pay-3")
    c.runFor(100)
    printEvents(c)
    println("-- before the partition heals:")
    printState(c)
    val shown = c.events.size
    c.heal(old.id)
    c.runFor(300)
    c.events.drop(shown).forEach(::println)
    println("-- after:")
    printState(c)
}

private fun printEvents(c: Cluster) {
    // heartbeats and acknowledgements are not events; elections, votes, commits and refusals are
    c.events.forEach(::println)
}

private fun printState(c: Cluster) {
    for (n in c.nodes) {
        val role = if (!c.isUp(n.id)) "down" else n.role.name.lowercase()
        println("%-3s %-9s term %d  commit %d  log %s".format(name(n.id), role, n.currentTerm, n.commitIndex, n.log.joinToString(" ")))
    }
    require(c.violations.isEmpty()) { c.violations.joinToString("\n") }
    if (c.nodes.none { it.role == Role.LEADER && c.isUp(it.id) }) println("(no leader)")
}
