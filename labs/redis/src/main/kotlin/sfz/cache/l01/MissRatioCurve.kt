package sfz.cache.l01

/** One point of a miss-ratio curve: a cache of [size] keys missed this share of requests. */
data class CurvePoint(val size: Int, val missRatio: Double)

/**
 * A miss-ratio curve: replay the same requests through LRU caches of different sizes and record
 * the share of requests each one missed. It answers the sizing question "how big must the cache be
 * to miss at most X% of requests?" by measurement instead of by guessing.
 */
object MissRatioCurve {

    /**
     * Replays [trace] through a fresh, empty [LruCache] of [size] keys and returns its miss ratio.
     *
     * The first [warmup] requests fill the cache and are not counted: run them, then call
     * `resetStats()`, then run the rest. Without a warm-up, every cache pays for filling itself
     * from empty, and small traces make every cache look worse than it is in steady state.
     */
    @JvmStatic
    fun missRatio(trace: IntArray, size: Int, warmup: Int = 0): Double {
        TODO("lesson 1 lab: warm up a fresh LruCache, reset its stats, replay the rest, return missRatio()")
    }

    /** One [CurvePoint] per entry of [sizes], in the same order, all from the same [trace]. */
    @JvmStatic
    fun measure(trace: IntArray, sizes: List<Int>, warmup: Int = 0): List<CurvePoint> {
        TODO("lesson 1 lab: one missRatio call per size")
    }

    /**
     * The smallest size in [curve] whose miss ratio is at most [target], or null if none is.
     * The points may come in any order.
     */
    @JvmStatic
    fun smallestSizeFor(curve: List<CurvePoint>, target: Double): Int? {
        TODO("lesson 1 lab: sort by size, take the first point at or under the target")
    }
}
