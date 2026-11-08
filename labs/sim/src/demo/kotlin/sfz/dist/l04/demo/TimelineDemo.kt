package sfz.dist.l04.demo

/**
 * Lesson dist-04, section 1: one 3-second pause of holder A, and what the ledger receives. Network delay is fixed at
 * 5 ms so the times are easy to follow. A checks its lease at 1,500 ms, starts 60 ms of work, and stops at 1,520 ms.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l04.demo.TimelineDemoKt -q
 * Options: -Pargs='careful' uses the careful holder (200 ms margin). A second number moves the pause:
 * -Pargs='careful 1562' stops A at 1,562 ms, after its last check, while the write is being sent.
 */
fun main(args: Array<String>) {
    val policy: HolderPolicy = if (args.firstOrNull() == "careful") Careful(200) else Naive
    val pauseAt = args.getOrNull(1)?.toLong() ?: 1_520L
    val scenario = Scenario(
        durationMs = 6_000,
        latencyMs = 5L..5L,
        pauses = mapOf("A" to listOf(Pause(pauseAt, 3_000))),
        log = true,
    )
    val run = simulate(scenario, policy)
    println("holder: ${if (policy == Naive) "naive" else "careful, 200 ms margin"}; A stops at %,d ms for 3,000 ms".format(pauseAt))
    val window = run.log.filter { line ->
        line.substringBefore(" ms").replace(",", "").trim().toLong() in 1_400..4_600 && "B renewed" !in line
    }
    printCondensed(window)
    println("stale writes: ${staleWrites(run).size}; landed after a newer holder's write: ${clobbers(run).size}")
}

/** Prints the log, folding B's run of routine updates into one line. */
private fun printCondensed(lines: List<String>) {
    val routine = "ledger applies B's update under lease 2, inside its lease"
    var i = 0
    while (i < lines.size) {
        if (routine !in lines[i]) {
            println(lines[i++])
            continue
        }
        var j = i
        while (j + 1 < lines.size && routine in lines[j + 1]) j++
        val from = lines[i].substringBefore(" ms").trim()
        val to = lines[j].substringBefore(" ms").trim()
        if (i == j) println(lines[i])
        else println("%7s ms  ledger applies B's updates under lease 2, every 100 ms until %s ms (%d of them)".format(from, to, j - i + 1))
        i = j + 1
    }
}
