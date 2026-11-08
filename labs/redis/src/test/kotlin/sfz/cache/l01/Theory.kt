package sfz.cache.l01

import kotlin.math.exp
import kotlin.math.pow

/**
 * Expected values the tests check the lab against, computed from the formulas, not from your code.
 *
 * - [zipf]: the Zipf probabilities 1/k^alpha, normalized.
 * - [topShare]: the share of requests that go to the most popular keys.
 * - [bestStaticMissRatio]: a cache that always holds exactly the `size` most popular keys. When
 *   every request is drawn independently from the same distribution, no cache can beat it.
 * - [cheLruMissRatio]: Che's approximation of LRU. Find the time T in which `size` distinct keys
 *   are requested (sum over keys of 1 - e^(-p T) = size); a key is a hit if it came back within T.
 *   For traces like these it is usually within a point or two of a real LRU.
 */
object Theory {
    fun zipf(n: Int, alpha: Double): DoubleArray {
        val w = DoubleArray(n) { 1.0 / (it + 1.0).pow(alpha) }
        val total = w.sum()
        return DoubleArray(n) { w[it] / total }
    }

    fun topShare(p: DoubleArray, top: Int): Double = p.take(top).sum()

    fun bestStaticMissRatio(p: DoubleArray, size: Int): Double = 1.0 - topShare(p, size)

    fun cheLruMissRatio(p: DoubleArray, size: Int): Double {
        require(size < p.size)
        fun occupied(t: Double) = p.sumOf { 1.0 - exp(-it * t) }
        var lo = 0.0
        var hi = 1.0
        while (occupied(hi) < size) hi *= 2
        repeat(100) {                                   // bisection for T
            val mid = (lo + hi) / 2
            if (occupied(mid) < size) lo = mid else hi = mid
        }
        val t = (lo + hi) / 2
        return 1.0 - p.sumOf { it * (1.0 - exp(-it * t)) }
    }
}
