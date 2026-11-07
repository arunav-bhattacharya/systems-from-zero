package sfz.redis.l06

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.extension.ExtendWith
import sfz.redis.support.KeySpace
import sfz.redis.support.TestRedis
import sfz.redis.support.WithRedis
import java.util.Random
import java.util.concurrent.CompletableFuture
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

// talks to the shared Redis 8.10 container (Docker)
@ExtendWith(WithRedis::class)
// the fifty-thread test makes 2,000 transfers through an 8-connection pool: give it room on a busy Docker VM
@Timeout(60, unit = TimeUnit.SECONDS)
class WatchTransferTest {
    private val redis = TestRedis.jedis

    private fun balance(key: String): Long = redis.get(key)?.toLong() ?: 0

    @Test
    fun `a transfer moves the money in one attempt when nobody interferes`(keys: KeySpace) {
        redis.set(keys("acct:a"), "10000")
        redis.set(keys("acct:b"), "500")

        val result = WatchTransfer(redis).transfer(keys("acct:a"), keys("acct:b"), 3_000)

        assertThat(result).isEqualTo(WatchTransfer.Result(WatchTransfer.Outcome.DONE, 1))
        assertThat(balance(keys("acct:a"))).isEqualTo(7_000)
        assertThat(balance(keys("acct:b"))).isEqualTo(3_500)
    }

    @Test
    fun `an overdraft is refused and changes nothing`(keys: KeySpace) {
        redis.set(keys("acct:a"), "2000")

        val result = WatchTransfer(redis).transfer(keys("acct:a"), keys("acct:b"), 3_000)

        assertThat(result.outcome()).isEqualTo(WatchTransfer.Outcome.INSUFFICIENT_FUNDS)
        assertThat(balance(keys("acct:a"))).isEqualTo(2_000)
        assertThat(redis.exists(keys("acct:b"))).isFalse()
    }

    @Test
    fun `a change to the watched balance aborts EXEC and the transfer retries with the new balance`(keys: KeySpace) {
        redis.set(keys("acct:a"), "10000")
        val reads = AtomicInteger()
        TestRedis.newJedis().use { other ->
            // between our GET and our EXEC, another client takes 8,000 from the same account, once
            val interfere = Runnable { if (reads.incrementAndGet() == 1) other.decrBy(keys("acct:a"), 8_000) }

            val result = WatchTransfer(redis, interfere).transfer(keys("acct:a"), keys("acct:b"), 3_000)

            // attempt 1 read 10,000 and its EXEC was refused; attempt 2 read 2,000, which is not enough
            assertThat(result).isEqualTo(WatchTransfer.Result(WatchTransfer.Outcome.INSUFFICIENT_FUNDS, 2))
        }
        assertThat(balance(keys("acct:a"))).isEqualTo(2_000)
        assertThat(balance(keys("acct:b"))).isZero()
    }

    @Test
    fun `a retry that still has enough money completes`(keys: KeySpace) {
        redis.set(keys("acct:a"), "10000")
        val reads = AtomicInteger()
        TestRedis.newJedis().use { other ->
            val interfere = Runnable { if (reads.incrementAndGet() == 1) other.incrBy(keys("acct:a"), 500) }

            val result = WatchTransfer(redis, interfere).transfer(keys("acct:a"), keys("acct:b"), 3_000)

            assertThat(result).isEqualTo(WatchTransfer.Result(WatchTransfer.Outcome.DONE, 2))
        }
        assertThat(balance(keys("acct:a"))).isEqualTo(7_500)                // 10,000 + 500 - 3,000: nothing lost
        assertThat(balance(keys("acct:b"))).isEqualTo(3_000)
    }

    @Test
    fun `fifty threads moving money at random never create or destroy any`(keys: KeySpace) {
        val accounts = (0 until 4).map { keys("acct:$it") }
        accounts.forEach { redis.set(it, "25000") }
        val transfer = WatchTransfer(redis)
        val pool = Executors.newFixedThreadPool(50)
        val attempts = AtomicInteger()

        val jobs = (0 until 50).map { t ->
            CompletableFuture.runAsync({
                val random = Random(t.toLong())
                repeat(40) {
                    val from = accounts[random.nextInt(4)]
                    val to = accounts.filter { it != from }[random.nextInt(3)]
                    attempts.addAndGet(transfer.transfer(from, to, 1L + random.nextInt(5_000)).attempts())
                }
            }, pool)
        }
        jobs.forEach { it.get(50, TimeUnit.SECONDS) }
        pool.shutdown()

        val balances = accounts.map(::balance)
        assertThat(balances.sum()).isEqualTo(100_000)
        assertThat(balances).allSatisfy { assertThat(it).isGreaterThanOrEqualTo(0) }
        assertThat(attempts.get()).isGreaterThanOrEqualTo(2_000)              // 2,000 transfers, plus any retries
    }
}
