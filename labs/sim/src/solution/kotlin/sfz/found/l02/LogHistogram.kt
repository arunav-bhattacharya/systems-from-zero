package sfz.found.l02

import kotlin.math.ceil
import kotlin.math.ln
import kotlin.math.pow
import kotlin.math.roundToLong

/**
 * A latency histogram with logarithmic buckets. Values are microseconds.
 *
 * Bucket i holds the values v with gamma^(i-1) < v <= gamma^i, where gamma = (1 + e) / (1 - e) and e
 * is [relativeError]. Each bucket is about 2e wider than the one before it, so small values get
 * narrow buckets and large values wide ones, and every value the histogram reports is within e
 * (1% by default) of a value that was really recorded. About 1,100 buckets cover 1 µs to 1 hour.
 *
 * Two histograms with the same [relativeError] merge by adding their bucket counts. That is the
 * whole reason to keep histograms instead of percentiles: counts add up, percentiles don't.
 */
class LogHistogram(val relativeError: Double = 0.01) {
    private val gamma = (1 + relativeError) / (1 - relativeError)
    private val lnGamma = ln(gamma)
    private val counts = LongArray(bucketIndex(MAX_VALUE) + 1)

    /** How many values were recorded. */
    var count: Long = 0
        private set

    /** The largest value recorded, exactly. */
    var max: Long = 0
        private set

    private var sum: Long = 0

    /** The exact mean of everything recorded (0 if empty). */
    fun mean(): Double = if (count == 0L) 0.0 else sum.toDouble() / count

    /** The bucket a value falls in. Values below 1 µs count as 1 µs; values above an hour as an hour. */
    fun bucketIndex(micros: Long): Int {
        val v = micros.coerceIn(1, MAX_VALUE)
        return ceil(ln(v.toDouble()) / lnGamma).toInt()
    }

    /** The value the histogram reports for bucket [i]: within [relativeError] of anything in it. */
    fun bucketValue(i: Int): Long = (2 * gamma.pow(i) / (gamma + 1)).roundToLong()

    /** Counts one value: one increment in its bucket. Also keep count, sum and max up to date. */
    fun record(micros: Long) {
        counts[bucketIndex(micros)]++
        count++
        sum += micros
        if (micros > max) max = micros
    }

    /**
     * The q-quantile (q = 0.99 for p99) by the nearest-rank rule: the smallest recorded value such
     * that at least q of all values are at or below it. Walk the buckets from the smallest, adding
     * up counts, and stop at the bucket where the running total reaches ceil(q * count).
     * Returns 0 for an empty histogram.
     */
    fun quantile(q: Double): Long {
        require(q in 0.0..1.0) { "q must be between 0 and 1" }
        if (count == 0L) return 0
        val rank = maxOf(1L, ceil(q * count).toLong())   // the rank-th smallest value, counting from 1
        var seen = 0L
        for (i in counts.indices) {
            seen += counts[i]
            if (seen >= rank) return minOf(bucketValue(i), max)   // never report more than the true max
        }
        return max
    }

    /** Adds every count in [other] to this histogram. Both must use the same [relativeError]. */
    fun merge(other: LogHistogram) {
        require(other.relativeError == relativeError) { "histograms with different buckets don't add" }
        for (i in counts.indices) counts[i] += other.counts[i]
        count += other.count
        sum += other.sum
        max = maxOf(max, other.max)
    }

    /** How many buckets hold at least one value: the histogram's real size. */
    fun nonEmptyBuckets(): Int = counts.count { it > 0 }

    companion object {
        const val MAX_VALUE: Long = 3_600_000_000L   // one hour in microseconds
    }
}
