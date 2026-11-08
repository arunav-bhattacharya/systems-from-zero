package sfz.dist.l02.demo

/**
 * Lesson dist-02, sections 1 and 2: fixed timeouts against phi accrual on two links.
 *
 * A heartbeat every second for 300 s, then the node dies. The detector is asked every 10 ms whether
 * it suspects the node. "False alarms" counts the times it started suspecting a node that was alive;
 * "detection" is how long after the crash it first suspected it.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l02.demo.DetectorDemoKt
 * Optional: -Pargs='pause' freezes the node for 4 s at 199 s (a long GC pause) on both links.
 */
fun main(args: Array<String>) {
    val pause = args.firstOrNull() == "pause"
    val pauses = if (pause) listOf(199_001L until 203_001L) else emptyList()
    val detectors = listOf<Pair<String, () -> FailureDetector>>(
        "fixed 1,500 ms" to { FixedTimeoutDetector(1_500) },
        "fixed 3,000 ms" to { FixedTimeoutDetector(3_000) },
        "fixed 6,000 ms" to { FixedTimeoutDetector(6_000) },
        "phi > 8" to { PhiAccrualDetector(threshold = 8.0) },
        "phi > 12" to { PhiAccrualDetector(threshold = 12.0) },
    )
    println(if (pause) "The node freezes for 4 s at 199 s, then dies at 300 s" else "The node dies at 300 s")
    for (link in listOf(CALM, JITTERY)) {
        println()
        println("${link.name}: each heartbeat takes ${link.baseMs} to ${link.baseMs + link.jitterMs} ms")
        println("%-16s %13s %22s %11s".format("detector", "false alarms", "suspected while alive", "detection"))
        for ((name, make) in detectors) {
            val s = score(make(), Scenario(link, pauses = pauses))
            println("%-16s %13d %19d ms %8s ms".format(name, s.falseAlarms, s.suspectedWhileAliveMs, s.detectionMs ?: "never"))
        }
    }
}
