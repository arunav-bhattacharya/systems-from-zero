package sfz.found.l02

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.data.Offset
import org.assertj.core.data.Percentage
import org.junit.jupiter.api.Test
import kotlin.math.ceil
import kotlin.math.exp
import kotlin.random.Random

class LogHistogramTest {
    /** The exact nearest-rank quantile of a list, for checking the histogram against. */
    private fun exact(values: List<Long>, q: Double): Long {
        val sorted = values.sorted()
        return sorted[maxOf(1, ceil(q * sorted.size).toInt()) - 1]
    }

    /** Skewed, latency-like data: mostly around 20 ms, with a long tail. */
    private fun latencies(seed: Long, n: Int): List<Long> {
        val rnd = Random(seed)
        return List(n) { (exp(rnd.nextDouble() * rnd.nextDouble() * 6.0) * 2_000).toLong() + 500 }
    }

    @Test
    fun `it counts every value and keeps the exact max and mean`() {
        val h = LogHistogram()
        listOf(1_000L, 2_000L, 3_000L, 250_000L).forEach(h::record)
        assertThat(h.count).isEqualTo(4)
        assertThat(h.max).isEqualTo(250_000)
        assertThat(h.mean()).isEqualTo(64_000.0)
    }

    @Test
    fun `an empty histogram reports 0`() {
        assertThat(LogHistogram().quantile(0.99)).isEqualTo(0)
    }

    @Test
    fun `quantiles of a small example follow the nearest-rank rule`() {
        val h = LogHistogram()
        // ten response times in microseconds: nine fast ones and one slow one
        listOf(12_000L, 13_000, 13_000, 14_000, 15_000, 15_000, 16_000, 18_000, 22_000, 940_000).forEach(h::record)
        assertThat(h.quantile(0.5)).isCloseTo(15_000, Percentage.withPercentage(1.0))
        assertThat(h.quantile(0.9)).isCloseTo(22_000, Percentage.withPercentage(1.0))
        assertThat(h.quantile(0.99)).isCloseTo(940_000, Percentage.withPercentage(1.0))
        assertThat(h.quantile(0.0)).isCloseTo(12_000, Percentage.withPercentage(1.0))
    }

    @Property(tries = 30)
    fun `every quantile is within 1 percent of the exact one`(@ForAll seed: Long) {
        val values = latencies(seed, 5_000)
        val h = LogHistogram()
        values.forEach(h::record)
        for (q in listOf(0.5, 0.9, 0.99, 0.999, 1.0)) {
            assertThat(h.quantile(q)).`as`("q=$q").isCloseTo(exact(values, q), Offset.offset((exact(values, q) * 0.01).toLong() + 1))
        }
    }

    @Test
    fun `a million values fit in about a thousand buckets`() {
        val h = LogHistogram()
        val rnd = Random(5)
        repeat(1_000_000) { h.record(rnd.nextLong(1, 3_600_000_000L)) }
        assertThat(h.count).isEqualTo(1_000_000)
        assertThat(h.nonEmptyBuckets()).isLessThan(1_200)
    }

    @Test
    fun `merging two histograms is the same as recording everything in one`() {
        val a = latencies(1, 20_000)
        val b = latencies(2, 3_000).map { it * 10 }
        val ha = LogHistogram().apply { a.forEach(::record) }
        val hb = LogHistogram().apply { b.forEach(::record) }
        val both = LogHistogram().apply { (a + b).forEach(::record) }
        ha.merge(hb)
        assertThat(ha.count).isEqualTo(both.count)
        assertThat(ha.max).isEqualTo(both.max)
        for (q in listOf(0.5, 0.9, 0.99, 0.999)) assertThat(ha.quantile(q)).isEqualTo(both.quantile(q))
    }

    @Test
    fun `the average of two pods' p99s is not the p99 of the service`() {
        val rnd = Random(9)
        // pod A: 9,000 requests, all 15 to 25 ms. Pod B: 1,000 requests, 1 in 20 of them take 800 ms.
        val podA = List(9_000) { rnd.nextLong(15_000, 25_000) }
        val podB = List(1_000) { if (rnd.nextInt(20) == 0) 800_000L else rnd.nextLong(15_000, 25_000) }
        val ha = LogHistogram().apply { podA.forEach(::record) }
        val hb = LogHistogram().apply { podB.forEach(::record) }
        val averaged = (ha.quantile(0.99) + hb.quantile(0.99)) / 2
        ha.merge(hb)
        val merged = ha.quantile(0.99)
        assertThat(merged).isCloseTo(exact(podA + podB, 0.99), Percentage.withPercentage(1.0))
        assertThat(averaged).isGreaterThan(merged * 10)                     // averaging says about 412 ms
    }
}
