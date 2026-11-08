package sfz.cons.l03.demo

/**
 * Lesson cons-03: Paxos on a simulated network, 500 or 1,000 seeded runs per line.
 *   ./gradlew :sim:demo -Pmain=sfz.cons.l03.demo.PaxosDemoKt -q              safety, and the rule that gives it
 *   ./gradlew :sim:demo -Pmain=sfz.cons.l03.demo.PaxosDemoKt -Pargs=timing -q  liveness needs timeouts longer than round trips
 *   ./gradlew :sim:demo -Pmain=sfz.cons.l03.demo.PaxosDemoKt -Pargs=cost -q    messages and time per decision
 */
fun main(args: Array<String>) {
    when (args.firstOrNull() ?: "safety") {
        "safety" -> safety()
        "timing" -> timing()
        "cost" -> cost()
        else -> println("say safety, timing or cost")
    }
}

private val seeds = 1L..1_000L

private fun safety() {
    val hostile = { seed: Long ->
        PaxosConfig(
            seed = seed, values = listOf("capture", "void", "refund"), acceptors = 5,
            dropRate = 0.2, duplicateRate = 0.1, maxDown = 2, proposersCrash = true,
        )
    }
    println("3 proposers (capture, void, refund), 5 acceptors, 20% of messages lost, 10% duplicated,")
    println("up to 2 acceptors down at a time, all but one proposer crash early")
    println()
    val few = 1L..500L
    report("Paxos as written", few.map { runPaxos(hostile(it)) })
    report("proposers ignore the promises and push their own value", few.map { runPaxos(hostile(it)) { own, _ -> own } })
    report("acceptors forget their promises when they restart", few.map { runPaxos(hostile(it).copy(acceptorsForget = true)) })
}

private fun report(title: String, outs: List<PaxosOutcome>) {
    val decided = outs.count { it.decisions.isNotEmpty() }
    val split = outs.count { it.chosen.size > 1 }
    println(title)
    println("  runs where someone learned a decision: %,d of %,d".format(decided, outs.size))
    println("  runs where two different values were chosen: %,d".format(split))
    println("  rounds per run: mean %.1f, max %d".format(outs.map { it.rounds }.average(), outs.maxOf { it.rounds }))
    println()
}

private fun timing() {
    println("2 proposers, 5 acceptors, no loss, one-way delay 1 to 30 ms (a round trip up to 60 ms), give up at 2 s")
    println("%-10s %-15s %22s %14s %13s".format("timeout", "retry", "runs that decided", "mean rounds", "two values"))
    for (timeout in listOf(20L, 40L, 60L, 120L)) for (backoff in listOf(false, true)) {
        val outs = seeds.map {
            runPaxos(PaxosConfig(seed = it, maxDelayMs = 30, timeoutMs = timeout, randomBackoff = backoff, giveUpAtMs = 2_000))
        }
        println("%-10s %-15s %16d of %,d %14.1f %13d".format(
            "$timeout ms", if (backoff) "random backoff" else "at once",
            outs.count { it.decisions.isNotEmpty() }, outs.size, outs.map { it.rounds }.average(), outs.count { it.chosen.size > 1 },
        ))
    }
}

private fun cost() {
    println("one proposer, no loss, one-way delay 1 to 10 ms, 1,000 runs per line")
    println("%-10s %15s %15s %20s %20s".format("acceptors", "messages", "phase 2 only", "ms, whole round", "ms, phase 2 only"))
    for (n in listOf(3, 5, 7)) {
        val outs = seeds.map { runPaxos(PaxosConfig(seed = it, acceptors = n, values = listOf("capture"))) }
        println("%-10d %15.1f %15d %20.1f %20.1f".format(
            n, outs.map { it.messages }.average(), 2 * n, outs.map { it.roundMs.first() }.average(), outs.map { it.phase2Ms.first() }.average(),
        ))
    }
}
