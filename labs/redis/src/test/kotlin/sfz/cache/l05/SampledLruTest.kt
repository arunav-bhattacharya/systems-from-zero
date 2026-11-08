package sfz.cache.l05

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

// a model: no Docker needed
class SampledLruTest {

    /**
     * 100 hot keys and a stream of one-time cold keys, the shape of a payment cache: each round
     * writes one new cold key, then reads one hot key, so every hot key comes back every 100 rounds.
     * Returns the hot keys' miss rate after a warm-up.
     */
    private fun hotMissRate(cache: SampledLru, rounds: Int = 30_000): Double {
        var hotReads = 0
        var hotMisses = 0
        for (r in 0 until rounds) {
            cache.access("cold:$r")
            val hit = cache.access("hot:${r % 100}")
            if (r >= 2_000) {                      // skip the warm-up while the cache fills
                hotReads++
                if (!hit) hotMisses++
            }
        }
        return hotMisses.toDouble() / hotReads
    }

    @Test
    fun `a miss inserts the key and a second access is a hit`() {
        val cache = SampledLru(10, 5, 1)

        assertThat(cache.access("payment:42")).isFalse()
        assertThat(cache.access("payment:42")).isTrue()

        assertThat(cache.size()).isEqualTo(1)
        assertThat(cache.contains("payment:42")).isTrue()
        assertThat(cache.evictions()).isZero()
    }

    @Test
    fun `every access stamps the key with the next clock tick`() {
        val cache = SampledLru(10, 5, 1)
        cache.access("a")
        cache.access("b")
        cache.access("a")

        assertThat(cache.lastUsed("a")).isEqualTo(3)
        assertThat(cache.lastUsed("b")).isEqualTo(2)
    }

    @Test
    fun `the cache never holds more than its capacity`() {
        val cache = SampledLru(100, 5, 7)
        for (i in 0 until 1_000) cache.access("card:$i")

        assertThat(cache.size()).isEqualTo(100)
        assertThat(cache.evictions()).isEqualTo(900)
    }

    @Test
    fun `with a sample as big as the cache it is exact LRU`() {
        val cache = SampledLru(3, 3, 1)
        cache.access("a")
        cache.access("b")
        cache.access("c")
        cache.access("a")                          // a is now the most recent, b the oldest

        assertThat(cache.chooseVictim()).isEqualTo("b")
        cache.access("d")                          // full: evicts b

        assertThat(cache.contains("b")).isFalse()
        assertThat(cache.contains("a")).isTrue()
        assertThat(cache.contains("c")).isTrue()
        assertThat(cache.contains("d")).isTrue()
    }

    @Test
    fun `the victim is the oldest of the keys it sampled`() {
        // 1,000 keys stamped 1..1000; with 5 samples the victim is old, but rarely the very oldest
        val cache = SampledLru(1_000, 5, 42)
        for (i in 1..1_000) cache.access("k$i")

        val stamps = (0 until 200).map { cache.lastUsed(cache.chooseVictim()) }

        // the oldest of 5 random keys sits around the 1/6 point on average
        assertThat(stamps.average()).isBetween(100.0, 270.0)
        assertThat(stamps.distinct().size).isGreaterThan(50)
    }

    @Test
    fun `five samples keep a hot set almost as well as exact LRU`() {
        val exact = hotMissRate(SampledLru(1_000, 1_000, 3))
        val sampled = hotMissRate(SampledLru(1_000, 5, 3))

        assertThat(exact).isZero()
        assertThat(sampled).isLessThan(0.01)
    }

    @Test
    fun `one sample is random eviction and loses hot keys`() {
        val random = hotMissRate(SampledLru(1_000, 1, 3))

        // a random victim is a hot key one time in ten, so about 1 hot read in 10 misses
        assertThat(random).isGreaterThan(0.05)
    }
}
