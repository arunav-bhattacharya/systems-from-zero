package sfz.nosql.l12

import java.time.Duration
import java.time.Instant

/** One measurement: for example the latency of one card authorization. */
data class Point(val at: Instant, val value: Double)

/**
 * The summary of every point in one time bucket. It keeps the sum and the count rather than the
 * average, because sums and counts can be added up again later and averages can't.
 */
data class Bucket(val start: Instant, val count: Int, val min: Double, val max: Double, val sum: Double) {
    val avg: Double get() = sum / count
}

/**
 * Time bucketing and downsampling, the core of a time-series store: raw points are cut into fixed
 * windows and summarised, and the summaries are summarised again into wider windows.
 *
 * Your job: [downsample] and [rollup]. [bucketStart] and [retain] are given.
 */
object TimeSeries {
    /**
     * Given: the start of the [width] bucket that holds [at], counting buckets from the Unix epoch, like
     * TimescaleDB's `time_bucket`. With a 5-minute width, 09:43:07 falls in the bucket that starts at 09:40.
     */
    fun bucketStart(at: Instant, width: Duration): Instant {
        val w = width.toMillis()
        return Instant.ofEpochMilli(Math.floorDiv(at.toEpochMilli(), w) * w)
    }

    /**
     * Groups [points] by [bucketStart] and returns one [Bucket] per bucket that has at least one point
     * (count, min, max, sum of the values), sorted by start.
     */
    fun downsample(points: List<Point>, width: Duration): List<Bucket> = TODO("group by bucketStart, one Bucket(count, min, max, sum) per bucket, sorted by start")

    /**
     * Merges narrow buckets into wider ones of [width] (which must be a multiple of theirs), WITHOUT the
     * raw points: counts and sums add up, min of the mins, max of the maxes. Sorted by start.
     * This is what a continuous aggregate on top of another one does.
     */
    fun rollup(buckets: List<Bucket>, width: Duration): List<Bucket> = TODO("group buckets by bucketStart(start, width); add counts and sums, min of mins, max of maxes")

    /** Given: retention. Keeps only the points at or after [cutoff], as a retention policy drops old chunks. */
    fun retain(points: List<Point>, cutoff: Instant): List<Point> = points.filter { !it.at.isBefore(cutoff) }
}
