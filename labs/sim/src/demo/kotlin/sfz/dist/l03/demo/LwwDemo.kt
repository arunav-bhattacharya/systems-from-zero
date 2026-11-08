package sfz.dist.l03.demo

import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

/**
 * Lesson dist-03, section 3: last write wins with one slow clock.
 *
 * Two pods update one payment's status in a causal chain: each reads the current status, then writes
 * the next one. pod-b's clock is behind. First a trace of four rounds with pod-b 15 ms behind, then
 * the share of acknowledged writes lost for skews from 0 to 1 s, with 0 to 50 ms of think time
 * between rounds.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l03.demo.LwwDemoKt
 * Optional: -Pargs='40' sets pod-b's skew in ms for the trace.
 */
fun main(args: Array<String>) {
    val behind = args.firstOrNull()?.toLong() ?: 15
    val fmt = DateTimeFormatter.ofPattern("HH:mm:ss.SSS").withZone(ZoneOffset.UTC)
    fun t(ms: Long) = fmt.format(Instant.ofEpochMilli(ms))

    println("pod-b's clock is $behind ms behind. Each write follows a read of the one before it.")
    println("%-6s %-7s %-11s %-14s %-14s %s".format("round", "writer", "value", "true time", "stamp", "after the OK, a read returns"))
    val sim = Sim()
    val store = Store(sim)
    val pods = listOf(Writer("pod-a", DriftingClock(sim), sim, store), Writer("pod-b", DriftingClock(sim, offsetMs = -behind), sim, store))
    val statuses = listOf("captured", "refunded", "settled", "chargeback")
    fun round(i: Int) {
        if (i == statuses.size) return
        val w = pods[i % 2]
        store.read { _ ->
            val trueTime = sim.now
            val stamp = w.clock.millis()
            w.write(statuses[i]) {
                store.read { seen ->
                    println("%-6d %-7s %-11s %-14s %-14s %s".format(i + 1, w.name, statuses[i], t(trueTime), t(stamp),
                        if (seen?.value == statuses[i]) seen.value else "${seen?.value}   <- lost"))
                    round(i + 1)
                }
            }
        }
    }
    sim.at(sim.now) { round(0) }
    sim.run()

    println()
    println("1,000 writes alternating between the pods, 0 to 50 ms of think time between them")
    println("%-14s %12s %8s".format("pod-b behind", "acknowledged", "lost"))
    for (skew in listOf(0L, 5L, 10L, 20L, 50L, 100L, 1_000L)) {
        val s = Sim(7)
        val st = Store(s)
        val ws = listOf(Writer("pod-a", DriftingClock(s), s, st), Writer("pod-b", DriftingClock(s, offsetMs = -skew), s, st))
        val r = causalChain(s, st, ws, rounds = 1_000, commitWait = false, maxThinkMs = 50)
        println("%-14s %12d %7.1f%%".format("$skew ms", r.acknowledged, 100.0 * r.lost.size / r.acknowledged))
    }
}
