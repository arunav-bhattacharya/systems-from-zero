package sfz.shard.l04

import java.util.Random

/** How long a scatter-gather takes when every shard is usually fast and now and then slow. */
object FanOut {
    /** One shard's reply: 2 to 3 ms, except 1 reply in 100 takes 50 ms (a GC pause, a compaction). Given. */
    fun shardMillis(rnd: Random): Double = if (rnd.nextInt(100) == 0) 50.0 else 2.0 + rnd.nextDouble()

    /** A scatter-gather to [shards] shards waits for all of them, so it takes as long as the slowest reply. */
    fun scatterMillis(shards: Int, rnd: Random): Double {
        require(shards >= 1)
        return (1..shards).maxOf { shardMillis(rnd) } // the last reply decides when the query is done
    }

    /** The [p]th percentile (0 < p <= 100) by nearest rank: sort, then take the value at index ceil(p / 100 * n) - 1. Given. */
    fun percentile(values: List<Double>, p: Double): Double {
        val sorted = values.sorted()
        return sorted[maxOf(0, Math.ceil(p / 100.0 * sorted.size).toInt() - 1)]
    }

    /** The share of [values] above [millis]. Given. */
    fun slowerThan(values: List<Double>, millis: Double): Double = values.count { it > millis }.toDouble() / values.size
}
