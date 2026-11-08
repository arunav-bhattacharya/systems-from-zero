package sfz.cache.l06.demo

import java.util.Random
import kotlin.math.ln

/**
 * A hot key on a simulated clock: about 10 reads a second, a recompute that takes 3 seconds, a TTL of 60.
 * How many recomputations does each refresh cost with a plain TTL, and with XFetch?
 */
private const val TTL = 60.0
private const val DELTA = 3.0
private const val RATE = 10.0
private const val HOURS = 10.0

private fun simulate(label: String, beta: Double) {
    val random = Random(42)                                   // same seed, same reads, in Java and Kotlin
    var expiry = TTL                                          // the value was computed at t = 0
    val finishing = mutableListOf<Double>()                   // recomputes in flight: when each one ends
    val perRefresh = mutableListOf<Int>()                     // recomputes started for each refresh
    var started = 0
    var misses = 0
    var recomputes = 0
    var earlySum = 0.0
    var t = 0.0
    while (t < HOURS * 3600) {
        for (i in finishing.indices.reversed()) {             // a finished recompute stores a fresh value
            if (finishing[i] <= t) {
                val newExpiry = finishing.removeAt(i) + TTL
                if (newExpiry > expiry) {
                    expiry = newExpiry
                    if (started > 0) perRefresh += started
                    started = 0
                }
            }
        }
        val recompute = when {
            t >= expiry -> { misses++; true }                 // nothing fresh to return: a miss
            beta > 0 -> {                                     // XFetch: now - delta * beta * ln(rand) >= expiry
                val u = 1 - random.nextDouble()               // uniform in (0, 1]
                (t - DELTA * beta * ln(u) >= expiry).also { if (it) earlySum += expiry - t }
            }
            else -> false
        }
        if (recompute) {
            started++
            recomputes++
            finishing += t + DELTA
        }
        t += -ln(1 - random.nextDouble()) / RATE
    }
    val early = recomputes - misses
    println("%-17s per refresh: %4.1f recomputes (max %2d)   reads that missed: %5d   recomputes per hour: %4.0f%s".format(
        label, perRefresh.average(), perRefresh.max(), misses, recomputes / HOURS,
        if (early > 0) "   started %.1f s early on average".format(earlySum / early) else ""))
}

fun main() {
    println("A hot key, %.0f hours: ~%.0f reads/s, %.0f s to recompute, TTL %.0f s".format(HOURS, RATE, DELTA, TTL))
    simulate("plain TTL", 0.0)
    simulate("XFetch, beta 1", 1.0)
    simulate("XFetch, beta 2", 2.0)
}
