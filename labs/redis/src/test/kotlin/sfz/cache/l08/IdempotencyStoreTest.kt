package sfz.cache.l08

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.extension.ExtendWith
import sfz.cache.l08.IdempotencyStore.Begin
import sfz.redis.support.KeySpace
import sfz.redis.support.TestRedis
import sfz.redis.support.WithRedis
import java.time.Duration
import java.util.concurrent.CompletableFuture
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

// talks to the shared Redis 8.10 container (Docker)
@ExtendWith(WithRedis::class)
@Timeout(20, unit = TimeUnit.SECONDS)
class IdempotencyStoreTest {
    private val redis = TestRedis.jedis
    private val body = "h-4f1c"                       // stands in for a digest of the request body
    private val response = """{"payment":"p-981","status":"approved","amount":1250,"note":"a|b ✓"}"""

    @Test
    fun `the first request starts and a duplicate that arrives while it runs is told to wait`(keys: KeySpace) {
        val store = IdempotencyStore(redis, keys("idem:"))

        assertThat(store.begin("k-1", body)).isInstanceOf(Begin.Started::class.java)
        assertThat(store.begin("k-1", body)).isEqualTo(Begin.InProgress)
        assertThat(redis.get(keys("idem:k-1"))).startsWith("P|$body|")
    }

    @Test
    fun `a retry after completion replays the stored response byte for byte`(keys: KeySpace) {
        val store = IdempotencyStore(redis, keys("idem:"))
        val started = store.begin("k-1", body) as Begin.Started

        assertThat(store.complete("k-1", body, started.token, response)).isTrue()

        assertThat(store.begin("k-1", body)).isEqualTo(Begin.Replay(response))
        assertThat(store.begin("k-1", body)).isEqualTo(Begin.Replay(response))
    }

    @Test
    fun `the same key with a different body is a mismatch, while running and after`(keys: KeySpace) {
        val store = IdempotencyStore(redis, keys("idem:"))
        val started = store.begin("k-1", body) as Begin.Started

        assertThat(store.begin("k-1", "h-other")).isEqualTo(Begin.Mismatch)
        store.complete("k-1", body, started.token, response)
        assertThat(store.begin("k-1", "h-other")).isEqualTo(Begin.Mismatch)
        assertThat(store.begin("k-1", body)).isEqualTo(Begin.Replay(response))  // the mismatch changed nothing
    }

    @Test
    fun `twenty identical requests at once start exactly one charge`(keys: KeySpace) {
        val store = IdempotencyStore(redis, keys("idem:"))
        val pool = Executors.newFixedThreadPool(20)
        val start = CountDownLatch(1)

        val calls = (0 until 20).map { CompletableFuture.supplyAsync({ start.await(); store.begin("k-1", body) }, pool) }
        start.countDown()
        val results = calls.map { it.get(10, TimeUnit.SECONDS) }
        pool.shutdown()

        assertThat(results.filterIsInstance<Begin.Started>()).hasSize(1)
        assertThat(results.filter { it == Begin.InProgress }).hasSize(19)
    }

    @Test
    fun `a pending key expires so a retry after a crash can start again`(keys: KeySpace) {
        val store = IdempotencyStore(redis, keys("idem:"), pendingTtl = Duration.ofSeconds(1))
        store.begin("k-1", body)                                       // this pod dies before complete()

        assertThat(store.begin("k-1", body)).isEqualTo(Begin.InProgress)
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5)
        while (redis.exists(keys("idem:k-1")) && System.nanoTime() < deadline) Thread.sleep(50)

        assertThat(store.begin("k-1", body)).isInstanceOf(Begin.Started::class.java)
    }

    @Test
    fun `a stale attempt cannot complete a key that another attempt took over`(keys: KeySpace) {
        val store = IdempotencyStore(redis, keys("idem:"))
        val slow = store.begin("k-1", body) as Begin.Started
        redis.del(keys("idem:k-1"))                                    // its pending entry expired...
        val retry = store.begin("k-1", body) as Begin.Started          // ...and the client's retry took the key

        assertThat(store.complete("k-1", body, slow.token, """{"status":"stale"}""")).isFalse()
        assertThat(redis.get(keys("idem:k-1"))).isEqualTo("P|$body|${retry.token}")
        assertThat(store.complete("k-1", body, retry.token, response)).isTrue()
        assertThat(store.begin("k-1", body)).isEqualTo(Begin.Replay(response))
    }

    @Test
    fun `pending lives for seconds and done lives for a day`(keys: KeySpace) {
        val store = IdempotencyStore(redis, keys("idem:"))
        val started = store.begin("k-1", body) as Begin.Started

        assertThat(redis.pttl(keys("idem:k-1"))).isBetween(1L, 30_000L)
        store.complete("k-1", body, started.token, response)
        assertThat(redis.ttl(keys("idem:k-1"))).isBetween(86_000L, 86_400L)
    }
}
