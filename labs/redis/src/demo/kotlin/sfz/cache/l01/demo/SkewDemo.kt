package sfz.cache.l01.demo

import java.util.Random
import kotlin.math.pow

/** How much of the traffic the most popular keys get under Zipf popularity, for four values of alpha. */
fun main() {
    val n = 1_000_000                                   // a million merchants
    println("alpha  top 0.1%  top 1%  top 10%   distinct keys in 1M requests  seen once")
    for (alpha in listOf(0.6, 0.8, 1.0, 1.2)) {
        val cdf = cdf(n, alpha)
        // draw a million requests and count how many different keys they touched
        val random = Random(42)
        val seen = IntArray(n)
        repeat(1_000_000) {
            val k = cdf.binarySearch(random.nextDouble())
            seen[if (k >= 0) k else -k - 1]++           // first cdf entry above the draw
        }
        val distinct = seen.count { it > 0 }
        val once = seen.count { it == 1 }
        println("%5.1f  %7.1f%%  %5.1f%%  %6.1f%%   %,28d  %8.0f%%".format(alpha,
            100 * cdf[n / 1000 - 1], 100 * cdf[n / 100 - 1], 100 * cdf[n / 10 - 1],
            distinct, 100.0 * once / distinct))
    }
}

/** cdf[k - 1] = share of requests for keys 1..k, with key k weighted 1 / k^alpha. */
private fun cdf(n: Int, alpha: Double): DoubleArray {
    val total = (1..n).sumOf { it.toDouble().pow(-alpha) }
    var running = 0.0
    val cdf = DoubleArray(n) { running += (it + 1.0).pow(-alpha) / total; running }
    cdf[n - 1] = 1.0
    return cdf
}
