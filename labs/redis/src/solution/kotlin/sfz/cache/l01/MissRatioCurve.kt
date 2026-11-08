package sfz.cache.l01

/** One point of a miss-ratio curve: a cache of [size] keys missed this share of requests. */
data class CurvePoint(val size: Int, val missRatio: Double)

object MissRatioCurve {

    @JvmStatic
    fun missRatio(trace: IntArray, size: Int, warmup: Int = 0): Double {
        require(warmup in 0 until trace.size) { "warmup must leave at least one request to count" }
        val cache = LruCache<Int>(size)                 // a fresh, empty cache for every size
        for (i in 0 until warmup) cache.access(trace[i])
        cache.resetStats()                              // the warm-up filled the cache; don't count it
        for (i in warmup until trace.size) cache.access(trace[i])
        return cache.missRatio()
    }

    @JvmStatic
    fun measure(trace: IntArray, sizes: List<Int>, warmup: Int = 0): List<CurvePoint> =
        sizes.map { CurvePoint(it, missRatio(trace, it, warmup)) }

    @JvmStatic
    fun smallestSizeFor(curve: List<CurvePoint>, target: Double): Int? =
        curve.sortedBy { it.size }.firstOrNull { it.missRatio <= target }?.size
}
