package sfz.dist.l07.demo

/**
 * Lesson dist-07, sections 1 and 2: check one election under each node model, in every order.
 *
 * Two candidates (the first and last node) each vote for themselves and ask everyone else. The
 * explorer tries every order of delivery and every moment for a crash, and checks "at most one
 * node ever wins the term" in every state it reaches.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l07.demo.ExploreDemoKt
 * Optional: -Pargs='5 1' checks 5 nodes with up to 1 crash (defaults 3 and 1).
 * Lesson dist-08, section 2: -Pargs='grow' counts the states of the fixed election as the model grows.
 */
fun main(args: Array<String>) {
    if (args.firstOrNull() == "grow") return grow()
    val size = args.getOrNull(0)?.toInt() ?: 3
    val crashes = args.getOrNull(1)?.toInt() ?: 1
    println("$size nodes, candidates n1 and n$size, at most $crashes crash(es). Rule: at most one node ever wins the term.")
    println()
    println("%-15s %-17s %10s %7s  %s".format("model", "vote stored", "states", "stuck", "one leader?"))
    val runs = listOf(
        Triple("no crashes", NodeModel.CRASH_STOP, Persist.NEVER) to 0,
        Triple("crash-stop", NodeModel.CRASH_STOP, Persist.NEVER) to crashes,
        Triple("crash-recovery", NodeModel.CRASH_RECOVERY, Persist.NEVER) to crashes,
        Triple("crash-recovery", NodeModel.CRASH_RECOVERY, Persist.AFTER_REPLY) to crashes,
        Triple("crash-recovery", NodeModel.CRASH_RECOVERY, Persist.BEFORE_REPLY) to crashes,
    )
    var firstBroken: Pair<String, Exploration<World>>? = null
    for ((run, maxCrashes) in runs) {
        val (label, model, persist) = run
        val result = Election(size, model, persist, maxCrashes).check()
        val verdict = result.violation?.let { "NO: broken after ${it.size} steps" } ?: "yes"
        val states = if (result.violation == null) "%,d".format(result.states) else "-"
        val stuck = if (result.violation == null) "%,d".format(result.stuck) else "-"
        println("%-15s %-17s %10s %7s  %s".format(label, persist.label(), states, stuck, verdict))
        if (result.violation != null && firstBroken == null) firstBroken = "$label, ${persist.label()}" to result
    }
    val (where, result) = firstBroken ?: return
    println()
    println("The shortest way to break it ($where):")
    result.violation!!.forEachIndexed { i, step -> println("  %2d. %s".format(i + 1, step)) }
    println("  winners of the term: ${result.badState!!.elected.sorted().joinToString(" and ")}")
}

/** Full explorations of the fixed election (votes on disk before replying) at growing sizes. */
private fun grow() {
    println("The fixed election (votes on disk before replying), crash-recovery, explored in full:")
    println()
    println("%5s %8s %10s %9s".format("nodes", "crashes", "states", "time"))
    for (size in listOf(3, 5)) {
        for (crashes in 0..2) {
            val started = System.nanoTime()
            val result = Election(size, NodeModel.CRASH_RECOVERY, Persist.BEFORE_REPLY, crashes).check()
            val ms = (System.nanoTime() - started) / 1_000_000
            println("%5d %8d %,10d %6d ms".format(size, crashes, result.states, ms))
        }
    }
}

private fun Persist.label() = when (this) {
    Persist.NEVER -> "memory only"
    Persist.AFTER_REPLY -> "disk, after reply"
    Persist.BEFORE_REPLY -> "disk, before reply"
}
