package sfz.dist.l08.demo

/**
 * Lesson dist-08, section 3: deterministic simulation testing of a primary-backup register.
 *
 * Searches seeds for the first run where the naive protocol loses an acknowledged write, prints the
 * seed and the events before the violation, replays the seed to show the run is identical, then
 * runs the fixed protocol (epochs) on the same 10,000 seeds.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l08.demo.DstDemoKt
 * Optional: -Pargs='seed 4' prints the whole trace of one naive run (heartbeats left out).
 * Section 4: -Pargs='history' compares the god's-eye check with a check of the client's history alone.
 */
fun main(args: Array<String>) {
    when (args.firstOrNull()) {
        "seed" -> return printSeed(args[1].toLong())
        "history" -> return history()
    }
    val seeds = 0L until 10_000L
    println("Searching seeds 0 to 9,999 for a run where the naive protocol loses an acknowledged write...")
    val failure = Dst.search(seeds, Protocol.NAIVE)!!
    println("seed ${failure.seed} fails after ${failure.events} events. Fault: ${failure.fault}")
    println("  ${failure.violation}")
    println()
    println("The last events before it (heartbeats left out):")
    failure.trace.filterNot { "Heartbeat" in it }.takeLast(12).forEach { println("  $it") }
    println()
    val replay = Dst.replay(failure)
    println("Replaying seed ${failure.seed}: ${replay.trace.size} trace lines, identical to the first run: ${replay == failure}")
    println()
    val started = System.nanoTime()
    var failures = 0
    var simulatedMs = 0L
    for (seed in seeds) {
        val run = Simulation(seed, Protocol.FIXED).run()
        if (run.violation != null) failures++
        simulatedMs += 1_500
    }
    val wallMs = (System.nanoTime() - started) / 1_000_000
    println("The fixed protocol (epochs) on the same 10,000 seeds: $failures failures.")
    println("That was %,d simulated seconds in %,d ms of real time.".format(simulatedMs / 1_000, wallMs))
}

private fun printSeed(seed: Long) {
    val run = Simulation(seed, Protocol.NAIVE).run()
    run.trace.filterNot { "Heartbeat" in it }.forEach(::println)
}

/** Section 4: what a black-box checker sees, against what the simulator knows. */
private fun history() {
    var lost = 0
    var seen = 0
    var example: Run? = null
    for (seed in 0L until 10_000L) {
        val run = Simulation(seed, Protocol.NAIVE, stopAtViolation = false).run()
        if (run.violation != null) lost++
        if (run.violation != null && staleReads(run.history).isNotEmpty()) {
            seen++
            if (example == null) example = run
        }
    }
    println("Naive protocol, 10,000 seeds:")
    println("  runs that lost an acknowledged write (god's-eye check after every event): %,d".format(lost))
    println("  of those, runs where the client's own history shows it (a stale read):    %,d".format(seen))
    println()
    val run = example!!
    val stale = staleReads(run.history)
    println("Seed ${run.seed} (${run.fault}), the client's history around the first stale read:")
    println("   op  kind  value  invoked  completed  attempts")
    val firstBad = stale.first().substringAfter("read ").substringBefore(" ").toInt()
    run.history.filter { it.op in (firstBad - 7)..(firstBad + 1) }.forEach {
        println("  %3d  %-5s %5s  %4d ms    %4d ms  %8d".format(it.op, it.kind, it.value, it.invokedAt, it.doneAt, it.attempts))
    }
    println("  checker: ${stale.first()}")
}
