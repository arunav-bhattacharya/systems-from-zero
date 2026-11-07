package sfz.redis.l05

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.extension.ExtendWith
import sfz.redis.support.KeySpace
import sfz.redis.support.TestRedis
import sfz.redis.support.WithRedis
import java.util.Random
import java.util.concurrent.CompletableFuture
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

// talks to the shared Redis 8.10 container (Docker)
@ExtendWith(WithRedis::class)
@Timeout(10, unit = TimeUnit.SECONDS)
class MerchantCacheTest {
    private val redis = TestRedis.jedis
    private val fietsen = Merchant("m-17", "Fietsen Utrecht", "NL", 5940)

    private fun cacheFor(keys: KeySpace, repo: MerchantRepository) =
        MerchantCache(redis, keys.prefix, repo, 3_600, 0.1, 60, 42)

    @Test
    fun `a miss loads from the repository and stores the merchant with a TTL near the base`(keys: KeySpace) {
        val repo = FakeMerchantRepository().apply { add(fietsen) }
        val cache = cacheFor(keys, repo)

        assertThat(cache.get("m-17")).isEqualTo(fietsen)

        assertThat(repo.calls).isEqualTo(1)
        assertThat(redis.get(cache.key("m-17"))).isEqualTo("m-17|Fietsen Utrecht|NL|5940")
        assertThat(redis.ttl(cache.key("m-17"))).isBetween(3_240L, 3_960L)
    }

    @Test
    fun `a hit never touches the repository`(keys: KeySpace) {
        val repo = FakeMerchantRepository().apply { add(fietsen) }
        val cache = cacheFor(keys, repo)

        repeat(5) { assertThat(cache.get("m-17")).isEqualTo(fietsen) }

        assertThat(repo.calls).isEqualTo(1)
    }

    @Test
    fun `merchants loaded together get spread-out TTLs`(keys: KeySpace) {
        val repo = FakeMerchantRepository(delayMillis = 0)
        repeat(200) { repo.add(Merchant("m-$it", "Shop $it", "NL", 5411)) }
        val cache = cacheFor(keys, repo)

        repeat(200) { cache.get("m-$it") }

        val ttls = (0 until 200).map { redis.ttl(cache.key("m-$it")) }
        assertThat(ttls).allSatisfy { assertThat(it).isBetween(3_240L, 3_960L) }
        assertThat(ttls.max() - ttls.min()).isGreaterThan(500)        // not one cliff, a 720-second slope
        assertThat(ttls.distinct().size).isGreaterThan(100)
    }

    @Test
    fun `an unknown merchant is cached as missing for a short time`(keys: KeySpace) {
        val repo = FakeMerchantRepository()
        val cache = cacheFor(keys, repo)

        assertThat(cache.get("m-404")).isNull()
        assertThat(cache.get("m-404")).isNull()

        assertThat(repo.calls).isEqualTo(1)                              // the second miss stopped at Redis
        assertThat(redis.get(cache.key("m-404"))).isEqualTo(MerchantCache.MISSING)
        assertThat(redis.ttl(cache.key("m-404"))).isBetween(1L, 60L)
    }

    @Test
    fun `invalidate drops the entry so the next read loads the new row`(keys: KeySpace) {
        val repo = FakeMerchantRepository().apply { add(fietsen) }
        val cache = cacheFor(keys, repo)
        cache.get("m-17")

        val renamed = Merchant("m-17", "Fietsen Utrecht Centrum", "NL", 5940)
        repo.add(renamed)                                                 // the database changed...
        assertThat(cache.get("m-17")).isEqualTo(fietsen)                  // ...and the cache is stale
        cache.invalidate("m-17")

        assertThat(redis.exists(cache.key("m-17"))).isFalse()
        assertThat(cache.get("m-17")).isEqualTo(renamed)
        assertThat(repo.calls).isEqualTo(2)
    }

    @Test
    fun `a hundred concurrent misses for one merchant reach the repository once`(keys: KeySpace) {
        val repo = FakeMerchantRepository(delayMillis = 300).apply { add(fietsen) }
        val cache = cacheFor(keys, repo)
        val pool = Executors.newFixedThreadPool(100)
        val start = CountDownLatch(1)

        val results = (0 until 100).map {
            CompletableFuture.supplyAsync({ start.await(); cache.get("m-17") }, pool)
        }
        start.countDown()
        val merchants = results.map { it.get(5, TimeUnit.SECONDS) }
        pool.shutdown()

        assertThat(repo.calls).isEqualTo(1)
        assertThat(merchants).hasSize(100).containsOnly(fietsen)
    }

    @Test
    fun `misses for different merchants load in parallel`(keys: KeySpace) {
        val repo = FakeMerchantRepository(delayMillis = 300)
        repeat(10) { repo.add(Merchant("m-$it", "Shop $it", "NL", 5411)) }
        val cache = cacheFor(keys, repo)
        val pool = Executors.newFixedThreadPool(10)

        val t0 = System.nanoTime()
        (0 until 10).map { id -> CompletableFuture.supplyAsync({ cache.get("m-$id") }, pool) }
            .forEach { it.get(5, TimeUnit.SECONDS) }
        val millis = (System.nanoTime() - t0) / 1_000_000
        pool.shutdown()

        assertThat(repo.calls).isEqualTo(10)
        assertThat(millis).isLessThan(2_000)                              // one after another would take 3,000 ms
        assertThat(redis.exists(cache.key("m-3"))).isTrue()
    }
}

// no Docker: pure arithmetic
class JitteredTtlTest {

    @Test
    fun `jittered TTLs stay inside the band and fill it`() {
        val random = Random(7)

        val ttls = (0 until 10_000).map { MerchantCache.jitteredTtl(3_600, 0.1, random) }

        assertThat(ttls.min()).isGreaterThanOrEqualTo(3_240)
        assertThat(ttls.max()).isLessThanOrEqualTo(3_960)
        assertThat(ttls.average()).isBetween(3_570.0, 3_630.0)           // centred on the base
        assertThat(ttls.count { it < 3_300 }).isGreaterThan(500)          // both edges are used
        assertThat(ttls.count { it > 3_900 }).isGreaterThan(500)
    }

    @Test
    fun `no jitter gives the base TTL, and a TTL is never below one second`() {
        val random = Random(7)

        assertThat(MerchantCache.jitteredTtl(3_600, 0.0, random)).isEqualTo(3_600)
        assertThat(MerchantCache.jitteredTtl(1, 0.9, random)).isGreaterThanOrEqualTo(1)
    }
}
