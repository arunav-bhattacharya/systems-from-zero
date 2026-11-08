package sfz.found.l02.demo

import kotlin.math.ln
import kotlin.random.Random

/**
 * One worker, requests arriving at random (Poisson), each needing a random amount of work with a
 * mean of 10 ms (exponential). Raise the arrival rate and watch the response time.
 * Also checks Little's law: requests in the system = arrival rate x time in the system.
 */
private const val MEAN_SERVICE_MS = 10.0

private fun exp(rnd: Random, mean: Double) = -mean * ln(1 - rnd.nextDouble())

private class Run(val meanMs: Double, val p99Ms: Double, val inSystem: Double)

private fun simulate(utilization: Double, constantService: Boolean, n: Int = 1_000_000, seed: Long = 1): Run {
    val rnd = Random(seed)
    val meanGap = MEAN_SERVICE_MS / utilization          // utilization = arrival rate x service time
    val arrive = DoubleArray(n)
    val depart = DoubleArray(n)
    var t = 0.0
    var freeAt = 0.0
    for (i in 0 until n) {
        t += exp(rnd, meanGap)
        val service = if (constantService) MEAN_SERVICE_MS else exp(rnd, MEAN_SERVICE_MS)
        val start = maxOf(t, freeAt)                     // wait in line if the worker is busy
        freeAt = start + service
        arrive[i] = t
        depart[i] = freeAt
    }
    val response = DoubleArray(n) { depart[it] - arrive[it] }
    val sorted = response.sortedArray()
    // count the requests in the system at 10,000 random moments: arrived but not yet departed
    var total = 0L
    repeat(10_000) {
        val at = rnd.nextDouble() * arrive[n - 1]
        val arrived = arrive.binarySearch(at).let { if (it < 0) -it - 1 else it + 1 }
        val departed = depart.binarySearch(at).let { if (it < 0) -it - 1 else it + 1 }
        total += arrived - departed
    }
    return Run(response.average(), sorted[(0.99 * n).toInt() - 1], total / 10_000.0)
}

fun main() {
    println("one worker, mean service time 10 ms, 1,000,000 requests per row")
    println("busy   formula S/(1-p)   measured mean   measured p99   in system   rate x mean")
    for (u in listOf(0.5, 0.8, 0.9, 0.95, 0.99)) {
        val r = simulate(u, constantService = false)
        val rate = u / MEAN_SERVICE_MS                   // requests per ms
        println("%3.0f%%   %10.0f ms   %10.0f ms   %10.0f ms   %9.1f   %11.1f".format(
            u * 100, MEAN_SERVICE_MS / (1 - u), r.meanMs, r.p99Ms, r.inSystem, rate * r.meanMs))
    }
    val c = simulate(0.9, constantService = true)
    println("90%% busy, every request exactly 10 ms: mean %.0f ms, p99 %.0f ms".format(c.meanMs, c.p99Ms))
}
