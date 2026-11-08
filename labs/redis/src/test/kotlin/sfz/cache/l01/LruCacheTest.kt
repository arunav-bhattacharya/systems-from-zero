package sfz.cache.l01

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test

// a model: no Docker needed
class LruCacheTest {

    @Test
    fun `a miss inserts the key and the next access is a hit`() {
        val cache = LruCache<String>(10)

        assertThat(cache.access("merchant:m-17")).isFalse()
        assertThat(cache.access("merchant:m-17")).isTrue()

        assertThat(cache.size()).isEqualTo(1)
        assertThat(cache.hits()).isEqualTo(1)
        assertThat(cache.misses()).isEqualTo(1)
        assertThat(cache.missRatio()).isCloseTo(0.5, within(1e-12))
    }

    @Test
    fun `a full cache evicts the least recently used key`() {
        val cache = LruCache<String>(3)
        cache.access("a")
        cache.access("b")
        cache.access("c")
        cache.access("a")                       // a is now the newest; b is the oldest

        cache.access("d")                       // full: b goes

        assertThat(cache.contains("b")).isFalse()
        assertThat(cache.keysOldestFirst()).containsExactly("c", "a", "d")
        assertThat(cache.evictions()).isEqualTo(1)
    }

    @Test
    fun `a hit moves the key to the newest end`() {
        val cache = LruCache<Int>(4)
        listOf(1, 2, 3, 4).forEach { cache.access(it) }

        cache.access(2)
        cache.access(1)

        assertThat(cache.keysOldestFirst()).containsExactly(3, 4, 2, 1)
    }

    @Test
    fun `the cache never holds more than its capacity`() {
        val cache = LruCache<Int>(100)
        for (i in 0 until 1_000) cache.access(i)

        assertThat(cache.size()).isEqualTo(100)
        assertThat(cache.evictions()).isEqualTo(900)
        assertThat(cache.keysOldestFirst()).containsExactlyElementsOf(900 until 1_000)
    }

    @Test
    fun `contains does not count as a use`() {
        val cache = LruCache<String>(2)
        cache.access("a")
        cache.access("b")

        assertThat(cache.contains("a")).isTrue()    // a peek, not a use: a stays the oldest
        cache.access("c")

        assertThat(cache.contains("a")).isFalse()
        assertThat(cache.hits()).isZero()
    }
}
