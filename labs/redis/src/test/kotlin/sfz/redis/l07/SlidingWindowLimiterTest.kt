package sfz.redis.l07

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.extension.ExtendWith
import sfz.redis.support.KeySpace
import sfz.redis.support.TestRedis
import sfz.redis.support.WithRedis
import java.util.concurrent.CompletableFuture
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

// talks to the shared Redis 8.10 container (Docker); the clock is the nowMillis argument, so nothing here sleeps
@ExtendWith(WithRedis::class)
@Timeout(20, unit = TimeUnit.SECONDS)
class SlidingWindowLimiterTest {
    private val redis = TestRedis.jedis
    private val minute = 60_000L

    private fun limiter(keys: KeySpace, limit: Int = 5) = SlidingWindowLimiter(redis, keys("rl:"), limit, minute)

    @Test
    fun `admits up to the limit inside one window and refuses the next request`(keys: KeySpace) {
        val limiter = limiter(keys)

        val first5 = (0 until 5).map { limiter.tryAcquire("card:7", it * 1_000L) }

        assertThat(first5).containsOnly(true)
        assertThat(limiter.tryAcquire("card:7", 5_000)).isFalse()
        assertThat(redis.zcard(limiter.key("card:7"))).isEqualTo(5)       // the refusal was not recorded
    }

    @Test
    fun `a slot opens exactly when the oldest request leaves the window`(keys: KeySpace) {
        val limiter = limiter(keys)
        (0 until 5).forEach { limiter.tryAcquire("card:7", it * 1_000L) }    // at 0, 1000, 2000, 3000, 4000 ms
        limiter.tryAcquire("card:7", 5_000)                                   // refused, and not recorded

        assertThat(limiter.tryAcquire("card:7", 59_999)).isFalse()           // the request at 0 is still inside
        assertThat(limiter.tryAcquire("card:7", 60_000)).isTrue()            // now it is 60 s old: gone
        assertThat(limiter.tryAcquire("card:7", 60_500)).isFalse()           // 1000..4000 and 60000: full again
        assertThat(limiter.tryAcquire("card:7", 61_000)).isTrue()
    }

    @Test
    fun `there is no burst at a minute boundary`(keys: KeySpace) {
        val limiter = limiter(keys)
        (0 until 5).forEach { assertThat(limiter.tryAcquire("card:7", 59_000L + it * 100)).isTrue() }

        // a fixed window keyed by minute would start counting from zero here and admit five more
        assertThat(limiter.tryAcquire("card:7", 60_100)).isFalse()
        assertThat(limiter.tryAcquire("card:7", 118_999)).isFalse()
        assertThat(limiter.tryAcquire("card:7", 119_000)).isTrue()
    }

    @Test
    fun `two requests in the same millisecond both count`(keys: KeySpace) {
        val limiter = limiter(keys, limit = 2)

        assertThat(limiter.tryAcquire("card:7", 1_000)).isTrue()
        assertThat(limiter.tryAcquire("card:7", 1_000)).isTrue()
        assertThat(limiter.tryAcquire("card:7", 1_000)).isFalse()            // members must be unique, not the time
    }

    @Test
    fun `subjects have separate windows`(keys: KeySpace) {
        val limiter = limiter(keys, limit = 1)

        assertThat(limiter.tryAcquire("card:7", 1_000)).isTrue()
        assertThat(limiter.tryAcquire("card:7", 1_001)).isFalse()
        assertThat(limiter.tryAcquire("card:8", 1_002)).isTrue()
    }

    @Test
    fun `an idle subject's key expires after one window`(keys: KeySpace) {
        val limiter = limiter(keys)
        limiter.tryAcquire("card:7", 1_000)

        assertThat(redis.pttl(limiter.key("card:7"))).isBetween(1L, minute)
    }

    @Test
    fun `thirty-two callers at the same instant are admitted exactly five times`(keys: KeySpace) {
        val limiter = limiter(keys)
        val pool = Executors.newFixedThreadPool(32)
        val start = CountDownLatch(1)

        val calls = (0 until 32).map {
            CompletableFuture.supplyAsync({ start.await(); limiter.tryAcquire("card:7", 10_000) }, pool)
        }
        start.countDown()
        val admitted = calls.map { it.get(10, TimeUnit.SECONDS) }.count { it }
        pool.shutdown()

        // ZCARD then ZADD from the client admits more than five here; one script can't
        assertThat(admitted).isEqualTo(5)
        assertThat(redis.zcard(limiter.key("card:7"))).isEqualTo(5)
    }
}
