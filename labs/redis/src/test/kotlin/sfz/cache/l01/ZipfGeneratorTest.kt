package sfz.cache.l01

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test

// a model: no Docker needed, runs in about a second
class ZipfGeneratorTest {

    @Test
    fun `key k is asked for in proportion to 1 over k to the alpha`() {
        val zipf = ZipfGenerator(1_000, 1.0, 1)

        // with alpha = 1, key 1 is twice as popular as key 2 and ten times as popular as key 10
        assertThat(zipf.probability(1) / zipf.probability(2)).isCloseTo(2.0, within(1e-9))
        assertThat(zipf.probability(1) / zipf.probability(10)).isCloseTo(10.0, within(1e-9))
        // the normalizer is 1 + 1/2 + ... + 1/1000 = 7.4855, so key 1 gets 13.36% of requests
        assertThat(zipf.probability(1)).isCloseTo(0.13359, within(1e-5))
        assertThat((1..1_000).sumOf { zipf.probability(it) }).isCloseTo(1.0, within(1e-9))
    }

    @Test
    fun `alpha 0 is uniform`() {
        val zipf = ZipfGenerator(100, 0.0, 1)

        assertThat(zipf.probability(1)).isCloseTo(0.01, within(1e-12))
        assertThat(zipf.probability(100)).isCloseTo(0.01, within(1e-12))
        assertThat(zipf.shareOfTop(10)).isCloseTo(0.10, within(1e-9))
    }

    @Test
    fun `the same seed gives the same requests, another seed different ones`() {
        val a = ZipfGenerator(10_000, 1.0, 42).trace(1_000)
        val b = ZipfGenerator(10_000, 1.0, 42).trace(1_000)
        val c = ZipfGenerator(10_000, 1.0, 43).trace(1_000)

        assertThat(a).isEqualTo(b)
        assertThat(a).isNotEqualTo(c)
    }

    @Test
    fun `draws land on keys 1 to n at the expected rates`() {
        val n = 10_000
        val trace = ZipfGenerator(n, 1.0, 7).trace(500_000)
        val p = Theory.zipf(n, 1.0)

        assertThat(trace.min()).isGreaterThanOrEqualTo(1)
        assertThat(trace.max()).isLessThanOrEqualTo(n)
        // key 1 should get p[0] = 10.2% of draws; 500,000 draws pin that to about +-0.1%
        assertThat(trace.count { it == 1 } / 500_000.0).isCloseTo(p[0], within(0.003))
        // the top 1% of keys (100 of 10,000) get 53% of the requests
        assertThat(trace.count { it <= 100 } / 500_000.0).isCloseTo(Theory.topShare(p, 100), within(0.005))
        assertThat(Theory.topShare(p, 100)).isCloseTo(0.530, within(0.001))
    }

    @Test
    fun `a bigger alpha puts more of the traffic on the top keys`() {
        val shares = listOf(0.8, 1.0, 1.2).map { ZipfGenerator(100_000, it, 1).shareOfTop(1_000) }

        // the top 1% of 100,000 keys: about 34%, 62% and 85% of all requests
        assertThat(shares[0]).isCloseTo(Theory.topShare(Theory.zipf(100_000, 0.8), 1_000), within(1e-9))
        assertThat(shares[1]).isCloseTo(Theory.topShare(Theory.zipf(100_000, 1.0), 1_000), within(1e-9))
        assertThat(shares[2]).isCloseTo(Theory.topShare(Theory.zipf(100_000, 1.2), 1_000), within(1e-9))
        assertThat(shares).isSorted()
    }
}
