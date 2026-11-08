package sfz.dist.l03.demo

/**
 * Lesson dist-03, section 2: drift, syncs and the error bound.
 *
 * Two servers: one oscillator runs 150 ppm fast, the other 120 ppm slow. First their offsets after
 * a day with different sync intervals; then the error bound a node believes (1 ms at each sync,
 * plus an assumed worst drift of 200 ppm) over two minutes with a 30-second poll, Spanner's setting.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l03.demo.DriftDemoKt
 */
fun main() {
    println("%-22s %16s %16s %18s".format("sync", "fast clock, max", "slow clock, max", "max skew between"))
    val day = 86_400_000L
    for ((label, every) in listOf("never" to 0L, "every hour" to 3_600_000L, "every 64 s" to 64_000L, "every 30 s" to 30_000L)) {
        val sim = Sim()
        val fast = DriftingClock(sim, driftPpm = 150)
        val slow = DriftingClock(sim, driftPpm = -120)
        val start = sim.now
        if (every > 0) for (t in every..day step every) sim.at(start + t) { fast.sync(0); slow.sync(0) }
        var maxFast = 0L; var maxSlow = 0L; var maxSkew = 0L
        for (t in 0L..day step 1_000L) sim.at(start + t) {
            val f = fast.millis() - sim.now; val s = slow.millis() - sim.now
            maxFast = maxOf(maxFast, f); maxSlow = minOf(maxSlow, s); maxSkew = maxOf(maxSkew, f - s)
        }
        sim.run()
        println("%-22s %13d ms %13d ms %15d ms".format(label, maxFast, maxSlow, maxSkew))
    }

    println()
    println("The error bound with a 30 s poll: 1 ms at each sync + 200 ppm of assumed drift since")
    val sim = Sim()
    val clock = DriftingClock(sim, driftPpm = 150, maxDriftPpm = 200, boundMs = 1)
    val start = sim.now
    for (t in 30_000L..120_000L step 30_000L) sim.at(start + t) { clock.sync(residualMs = 0, boundMs = 1) }
    val cells = mutableListOf<String>()
    for (t in 0L until 120_000L step 5_000L) sim.at(start + t) { cells += "%3d s: %d ms".format(t / 1_000, clock.errorBoundMs()) }
    sim.at(start + 119_999) { cells += "119.999 s: ${clock.errorBoundMs()} ms" }
    sim.run()
    cells.chunked(6).forEach { row -> println(row.joinToString("   ")) }
}
