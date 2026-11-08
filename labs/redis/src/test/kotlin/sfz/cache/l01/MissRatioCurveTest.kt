package sfz.cache.l01

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test

// a model: no Docker needed, runs in a few seconds
class MissRatioCurveTest {

    private val n = 10_000
    private val trace by lazy { ZipfGenerator(n, 1.0, 2026).trace(300_000) }
    private val warmup = 50_000

    @Test
    fun `warm-up requests are not counted`() {
        val trace = intArrayOf(1, 2, 1, 2, 1, 2)

        assertThat(MissRatioCurve.missRatio(trace, 2)).isCloseTo(2.0 / 6, within(1e-12))
        assertThat(MissRatioCurve.missRatio(trace, 2, warmup = 2)).isZero()
    }

    @Test
    fun `a loop one key bigger than the cache misses every time`() {
        // keys 1..101 over and over: LRU always evicts exactly the key that comes back next
        val loop = IntArray(101 * 20) { it % 101 + 1 }

        assertThat(MissRatioCurve.missRatio(loop, 100, warmup = 101)).isEqualTo(1.0)
        assertThat(MissRatioCurve.missRatio(loop, 101, warmup = 101)).isEqualTo(0.0)
    }

    @Test
    fun `the miss ratio never rises as the cache grows`() {
        val curve = MissRatioCurve.measure(trace, listOf(1, 10, 50, 100, 500, 1_000, 2_000), warmup)

        assertThat(curve.map { it.size }).containsExactly(1, 10, 50, 100, 500, 1_000, 2_000)
        // LRU's bigger cache always holds everything its smaller cache holds, so it never misses more
        curve.zipWithNext { small, big -> assertThat(big.missRatio).isLessThanOrEqualTo(small.missRatio) }
    }

    @Test
    fun `LRU on Zipf traffic matches the expected curve`() {
        val p = Theory.zipf(n, 1.0)
        val curve = MissRatioCurve.measure(trace, listOf(10, 100, 1_000), warmup)

        for (point in curve) {
            assertThat(point.missRatio)
                .describedAs("miss ratio of an LRU cache of %d keys", point.size)
                .isCloseTo(Theory.cheLruMissRatio(p, point.size), within(0.02))
        }
        // the shape to remember: room for 1% of the keys still misses about 60% of the requests
        assertThat(curve[1].missRatio).isBetween(0.58, 0.64)
    }

    @Test
    fun `LRU never beats a cache of the most popular keys`() {
        val p = Theory.zipf(n, 1.0)
        for (size in listOf(10, 100, 1_000)) {
            val lru = MissRatioCurve.missRatio(trace, size, warmup)
            // LRU spends some of its slots on keys that came by once and won't come back soon
            assertThat(lru).isGreaterThan(Theory.bestStaticMissRatio(p, size))
        }
    }

    @Test
    fun `smallestSizeFor finds the first size that meets the target`() {
        val curve = listOf(CurvePoint(1_000, 0.08), CurvePoint(10, 0.6), CurvePoint(100, 0.3), CurvePoint(5_000, 0.04))

        assertThat(MissRatioCurve.smallestSizeFor(curve, 0.30)).isEqualTo(100)
        assertThat(MissRatioCurve.smallestSizeFor(curve, 0.05)).isEqualTo(5_000)
        assertThat(MissRatioCurve.smallestSizeFor(curve, 0.01)).isNull()
    }
}
