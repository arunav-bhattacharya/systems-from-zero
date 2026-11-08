package sfz.found.l05

import kotlin.math.sqrt

// Reference answers for Scaling.kt.

fun amdahl(workers: Int, serial: Double): Double = 1.0 / (serial + (1.0 - serial) / workers)

fun usl(workers: Int, alpha: Double, beta: Double): Double {
    val n = workers.toDouble()
    // contention grows with the other N - 1 workers; coherency with all N (N - 1) pairs
    return n / (1.0 + alpha * (n - 1.0) + beta * n * (n - 1.0))
}

fun uslPeak(alpha: Double, beta: Double): Double =
    if (beta <= 0.0) Double.POSITIVE_INFINITY else sqrt((1.0 - alpha) / beta)

data class UslFit(val alpha: Double, val beta: Double, val single: Double) {
    fun throughput(workers: Int): Double = single * usl(workers, alpha, beta)
}

fun fitUsl(measured: Map<Int, Double>): UslFit {
    val single = requireNotNull(measured[1]) { "the measurements must include one worker" }
    // rearranged USL: z = (alpha + beta) + beta x, a straight line
    val points = measured.filterKeys { it > 1 }.map { (n, x) ->
        val c = x / single                                  // relative capacity
        (n - 1.0) to (n / c - 1.0) / (n - 1.0)
    }
    require(points.size >= 2) { "need at least two worker counts besides 1" }
    val meanX = points.map { it.first }.average()
    val meanZ = points.map { it.second }.average()
    val slope = points.sumOf { (x, z) -> (x - meanX) * (z - meanZ) } / points.sumOf { (x, _) -> (x - meanX) * (x - meanX) }
    val intercept = meanZ - slope * meanX
    return UslFit(alpha = intercept - slope, beta = slope, single = single)
}

fun cost(singleThreadSeconds: Double, clusterSeconds: (workers: Int) -> Double, maxWorkers: Int): Int? =
    (1..maxWorkers).firstOrNull { clusterSeconds(it) < singleThreadSeconds }
