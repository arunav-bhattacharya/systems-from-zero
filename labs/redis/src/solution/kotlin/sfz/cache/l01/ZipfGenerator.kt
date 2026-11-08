package sfz.cache.l01

import java.util.Random

/**
 * Draws keys 1..[n] the way real cache traffic arrives: a few keys are asked for all the time and
 * most keys almost never. Key `k` (its popularity rank, 1 = most popular) is asked for with a
 * probability proportional to `1 / k^alpha`. That is a Zipf distribution, and [alpha] says how
 * skewed it is: 0 is uniform, 1 is the classic Zipf, bigger is more skewed.
 *
 * The same [seed] always gives the same requests, so a test or a demo can be repeated exactly.
 */
class ZipfGenerator(val n: Int, val alpha: Double, seed: Long) {
    private val random = Random(seed)

    /** `cdf[k - 1]` is the chance that one request asks for one of keys 1..k. The last entry is 1. */
    private val cdf = DoubleArray(n)

    init {
        require(n >= 1) { "n must be at least 1" }
        require(alpha >= 0.0) { "alpha must not be negative" }
        buildCdf()
    }

    private fun buildCdf() {
        var total = 0.0
        for (k in 1..n) total += 1.0 / Math.pow(k.toDouble(), alpha)   // the normalizer, H(n, alpha)
        var running = 0.0
        for (k in 1..n) {
            running += 1.0 / Math.pow(k.toDouble(), alpha) / total
            cdf[k - 1] = running                                        // running sum of probabilities
        }
        cdf[n - 1] = 1.0                       // rounding can leave 0.9999999; no draw may fall past the end
    }

    /** The probability that one request asks for key [rank]. */
    fun probability(rank: Int): Double {
        require(rank in 1..n) { "rank must be in 1..$n" }
        return if (rank == 1) cdf[0] else cdf[rank - 1] - cdf[rank - 2]
    }

    /** The share of all requests that go to the [top] most popular keys. */
    fun shareOfTop(top: Int): Double = if (top <= 0) 0.0 else cdf[minOf(top, n) - 1]

    /** One request: the rank of the key it asks for. */
    fun next(): Int {
        val u = random.nextDouble()            // uniform in [0, 1)
        var lo = 0
        var hi = n - 1
        while (lo < hi) {                      // binary search: the first entry with cdf > u
            val mid = (lo + hi) ushr 1
            if (cdf[mid] > u) hi = mid else lo = mid + 1
        }
        return lo + 1                          // index 0 is rank 1
    }

    /** [length] requests in a row. Done for you. */
    fun trace(length: Int): IntArray = IntArray(length) { next() }
}
