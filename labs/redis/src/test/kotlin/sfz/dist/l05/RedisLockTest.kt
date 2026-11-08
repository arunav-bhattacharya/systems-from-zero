package sfz.dist.l05

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.extension.ExtendWith
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
class RedisLockTest {
    private val redis = TestRedis.jedis
    private val thirtySeconds = Duration.ofSeconds(30)

    /** Waits (up to 5 s) until Redis has expired the key: what a lease running out during a GC pause looks like. */
    private fun waitUntilGone(key: String) {
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5)
        while (redis.exists(key) && System.nanoTime() < deadline) Thread.sleep(20)
        assertThat(redis.exists(key)).describedAs("the lease should have expired").isFalse()
    }

    @Test
    fun `the first client gets the lock and a second is refused while the lease lasts`(keys: KeySpace) {
        val lock = RedisLock(redis, keys(""))

        val a = lock.tryAcquire("settle", thirtySeconds)
        val b = lock.tryAcquire("settle", thirtySeconds)

        assertThat(a).isPresent
        assertThat(b).isEmpty
        assertThat(redis.get(lock.lockKey("settle"))).isEqualTo(a.get().token())
        assertThat(redis.pttl(lock.lockKey("settle"))).isBetween(1L, 30_000L)
    }

    @Test
    fun `every acquisition gets a larger fencing token`(keys: KeySpace) {
        val lock = RedisLock(redis, keys(""))

        val fences = (1..3).map {
            val lease = lock.tryAcquire("settle", thirtySeconds).orElseThrow()
            lock.release(lease)
            lease.fence()
        }

        assertThat(fences).containsExactly(1L, 2L, 3L)
        assertThat(redis.ttl(lock.fenceKey("settle"))).isEqualTo(-1L)       // the counter must never expire
    }

    @Test
    fun `a failed attempt does not use up a fencing token`(keys: KeySpace) {
        val lock = RedisLock(redis, keys(""))
        lock.tryAcquire("settle", thirtySeconds).orElseThrow()

        repeat(5) { lock.tryAcquire("settle", thirtySeconds) }

        assertThat(redis.get(lock.fenceKey("settle"))).isEqualTo("1")
    }

    @Test
    fun `release frees the lock for the next client`(keys: KeySpace) {
        val lock = RedisLock(redis, keys(""))
        val a = lock.tryAcquire("settle", thirtySeconds).orElseThrow()

        assertThat(lock.release(a)).isTrue()
        assertThat(lock.tryAcquire("settle", thirtySeconds)).isPresent
    }

    @Test
    fun `the lease ends on its own when the holder never releases`(keys: KeySpace) {
        val lock = RedisLock(redis, keys(""))
        lock.tryAcquire("settle", Duration.ofMillis(200)).orElseThrow()       // and then the pod dies

        waitUntilGone(lock.lockKey("settle"))

        assertThat(lock.tryAcquire("settle", thirtySeconds)).isPresent
    }

    @Test
    fun `a late release does not delete the next holder's lock`(keys: KeySpace) {
        val lock = RedisLock(redis, keys(""))
        val a = lock.tryAcquire("settle", Duration.ofMillis(200)).orElseThrow()
        waitUntilGone(lock.lockKey("settle"))                                 // A is paused; its lease runs out
        val b = lock.tryAcquire("settle", thirtySeconds).orElseThrow()        // B gets the lock and starts working

        val aDeleted = lock.release(a)                                        // A wakes up and "releases"

        assertThat(aDeleted).isFalse()
        assertThat(redis.get(lock.lockKey("settle"))).isEqualTo(b.token())
        assertThat(lock.tryAcquire("settle", thirtySeconds)).describedAs("C must not get in while B works").isEmpty
    }

    @Test
    fun `extend pushes out the holder's deadline and refuses anyone else's`(keys: KeySpace) {
        val lock = RedisLock(redis, keys(""))
        val a = lock.tryAcquire("settle", Duration.ofSeconds(5)).orElseThrow()

        assertThat(lock.extend(a, thirtySeconds)).isTrue()
        assertThat(redis.pttl(lock.lockKey("settle"))).isGreaterThan(20_000L)

        redis.del(lock.lockKey("settle"))                                     // A's lease is gone...
        val b = lock.tryAcquire("settle", Duration.ofMillis(5_000)).orElseThrow()   // ...and B holds the lock
        assertThat(lock.extend(a, thirtySeconds)).isFalse()
        assertThat(redis.get(lock.lockKey("settle"))).isEqualTo(b.token())
        assertThat(redis.pttl(lock.lockKey("settle"))).isLessThanOrEqualTo(5_000L)
    }

    @Test
    fun `twenty pods racing for one lock, exactly one wins`(keys: KeySpace) {
        val lock = RedisLock(redis, keys(""))
        val pool = Executors.newFixedThreadPool(20)
        val start = CountDownLatch(1)

        val tries = (0 until 20).map {
            CompletableFuture.supplyAsync({ start.await(); lock.tryAcquire("settle", thirtySeconds) }, pool)
        }
        start.countDown()
        val winners = tries.map { it.get(10, TimeUnit.SECONDS) }.filter { it.isPresent }
        pool.shutdown()

        assertThat(winners).hasSize(1)
        assertThat(winners.single().get().fence()).isEqualTo(1L)
    }

    @Test
    fun `with fencing, a holder that paused past its lease cannot overwrite the next holder's file`(keys: KeySpace) {
        val lock = RedisLock(redis, keys(""))
        val ledger = PayoutLedger()
        val a = lock.tryAcquire("settle", Duration.ofMillis(200)).orElseThrow()
        waitUntilGone(lock.lockKey("settle"))                                 // A stops for a long GC pause
        val b = lock.tryAcquire("settle", thirtySeconds).orElseThrow()

        assertThat(ledger.write("batch-118", b.fence(), "B: 4,210 payouts")).isTrue()
        assertThat(ledger.write("batch-118", a.fence(), "A: 4,198 payouts (stale)")).isFalse()   // A wakes and writes

        assertThat(ledger.read("batch-118")).isEqualTo(PayoutLedger.PayoutFile(b.fence(), "B: 4,210 payouts"))
    }
}
