package sfz.cache.l01.demo

import java.util.Random
import kotlin.math.pow

/** LRU miss-ratio curves for Zipf traffic over 100,000 keys, and the loop that defeats LRU. */
fun main() {
    val n = 100_000
    val sizes = listOf(100, 1_000, 10_000, 50_000)      // 0.1%, 1%, 10% and 50% of the keys
    println("LRU miss ratio, 1,000,000 requests over 100,000 keys")
    println("alpha    100 keys  1,000 keys  10,000 keys  50,000 keys")
    for (alpha in listOf(0.8, 1.0, 1.2)) {
        val trace = zipfTrace(n, alpha, 1_000_000, 7)
        println("%5.1f".format(alpha) + sizes.joinToString("") { "  %10.1f%%".format(100 * lruMissRatio(trace, it, 200_000)) })
    }
    for (keys in listOf(1_001, 2_000)) {
        val loop = IntArray(keys * 50) { it % keys + 1 }   // keys 1..n, over and over
        println("loop over %,d keys: cache of 1,000 misses %.0f%%, cache of %,d misses %.0f%%".format(
            keys, 100 * lruMissRatio(loop, 1_000, keys), keys, 100 * lruMissRatio(loop, keys, keys)))
    }
}

/** Replays the trace through an LRU cache of [size] keys; the first [warmup] requests aren't counted. */
private fun lruMissRatio(trace: IntArray, size: Int, warmup: Int): Double {
    val lru = object : LinkedHashMap<Int, Boolean>(16, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<Int, Boolean>) = this.size > size   // evict the LRU key
    }
    var misses = 0L
    trace.forEachIndexed { i, key ->
        if (lru[key] == null) {                         // get() also marks the key as just used
            lru[key] = true
            if (i >= warmup) misses++
        }
    }
    return misses.toDouble() / (trace.size - warmup)
}

private fun zipfTrace(n: Int, alpha: Double, length: Int, seed: Long): IntArray {
    val total = (1..n).sumOf { it.toDouble().pow(-alpha) }
    var running = 0.0
    val cdf = DoubleArray(n) { running += (it + 1.0).pow(-alpha) / total; running }
    cdf[n - 1] = 1.0
    val random = Random(seed)
    return IntArray(length) {
        val k = cdf.binarySearch(random.nextDouble())
        (if (k >= 0) k else -k - 1) + 1
    }
}
