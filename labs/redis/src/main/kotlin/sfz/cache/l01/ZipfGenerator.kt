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

    /**
     * Fills [cdf], the running total of the probabilities.
     *
     * 1. Add up the weights `1 / k^alpha` for k = 1..n (`Math.pow`). Call the sum `total`.
     * 2. Walk k = 1..n again, adding `1 / k^alpha / total` to a running sum, and store the running
     *    sum in `cdf[k - 1]`.
     * 3. Set `cdf[n - 1] = 1.0`, so rounding can never leave a gap at the end.
     */
    private fun buildCdf() {
        TODO("lesson 1 lab: fill cdf with the running total of 1 / k^alpha, normalized")
    }

    /** The probability that one request asks for key [rank]. Hint: the difference of two [cdf] entries. */
    fun probability(rank: Int): Double {
        TODO("lesson 1 lab: probability of one rank, from cdf")
    }

    /** The share of all requests that go to the [top] most popular keys. Done for you. */
    fun shareOfTop(top: Int): Double = if (top <= 0) 0.0 else cdf[minOf(top, n) - 1]

    /**
     * One request: the rank of the key it asks for.
     *
     * Draw `u = random.nextDouble()`, uniform in [0, 1). The answer is the smallest rank k with
     * `cdf[k - 1] > u`. Find it with a binary search over [cdf], not a loop from the start: a
     * million keys would cost a million steps per request.
     */
    fun next(): Int {
        TODO("lesson 1 lab: draw u, binary-search cdf for the first entry above it")
    }

    /** [length] requests in a row. Done for you. */
    fun trace(length: Int): IntArray = IntArray(length) { next() }
}
