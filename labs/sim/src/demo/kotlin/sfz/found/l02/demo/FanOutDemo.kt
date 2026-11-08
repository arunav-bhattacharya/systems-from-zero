package sfz.found.l02.demo

import kotlin.math.ceil
import kotlin.math.pow
import kotlin.random.Random

/**
 * A request fans out to N leaves and waits for all of them. Each leaf answers in 5 to 15 ms, but
 * 1 time in 100 it takes a full second. Then the same with hedged requests.
 */
private const val SLOW = 1_000_000L   // µs

private fun run(leaves: Int, requests: Int, hedgeAfter: Long?, correlated: Boolean = false): Triple<LongArray, Double, Double> {
    val rnd = Random(1)
    fun leaf() = if (rnd.nextInt(100) == 0) SLOW else rnd.nextLong(5_000, 15_001)
    var hedges = 0L
    val roots = LongArray(requests) {
        var slowest = 0L
        repeat(leaves) {
            val first = leaf()
            val second = if (correlated && first == SLOW) SLOW else leaf()
            val latency = if (hedgeAfter == null || first <= hedgeAfter) first else { hedges++; minOf(first, hedgeAfter + second) }
            slowest = maxOf(slowest, latency)
        }
        slowest
    }
    roots.sort()
    return Triple(roots, roots.count { it >= SLOW }.toDouble() / requests, hedges.toDouble() / (requests.toLong() * leaves))
}

private fun q(s: LongArray, p: Double) = s[maxOf(1, ceil(p * s.size).toInt()) - 1] / 1000.0

fun main() {
    println("leaves   slow requests   formula 1 - 0.99^N")
    for (n in listOf(1, 10, 100, 1_000)) {
        val (_, slow, _) = run(n, 20_000, null)
        println("%6d   %12.1f%%   %17.1f%%".format(n, slow * 100, (1 - 0.99.pow(n)) * 100))
    }
    println()
    println("100 leaves                     p50       p99     p99.9   extra requests")
    for ((name, hedge, corr) in listOf(Triple("no hedging", null, false), Triple("hedge after 15 ms", 15_000L, false),
                                      Triple("hedge, slowness shared", 15_000L, true))) {
        val (s, _, extra) = run(100, 20_000, hedge, corr)
        println("%-24s %7.0f ms %7.0f ms %7.0f ms %10.1f%%".format(name, q(s, 0.5), q(s, 0.99), q(s, 0.999), extra * 100))
    }
}
