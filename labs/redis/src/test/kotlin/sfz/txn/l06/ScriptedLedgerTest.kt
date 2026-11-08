package sfz.txn.l06

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

// talks to the shared Redis 8.10 container (Docker)
@ExtendWith(WithRedis::class)
@Timeout(20, unit = TimeUnit.SECONDS)
class ScriptedLedgerTest {
    private val redis = TestRedis.jedis

    private fun balance(key: String): Long = redis.get(key)?.toLong() ?: 0

    @Test
    fun `the script moves the money and says so`(keys: KeySpace) {
        redis.set(keys("acct:a"), "10000")
        val ledger = ScriptedLedger(redis)

        assertThat(ledger.transfer(keys("acct:a"), keys("acct:b"), 3_000)).isTrue()

        assertThat(balance(keys("acct:a"))).isEqualTo(7_000)
        assertThat(balance(keys("acct:b"))).isEqualTo(3_000)
    }

    @Test
    fun `the script refuses an overdraft and writes nothing`(keys: KeySpace) {
        redis.set(keys("acct:a"), "2000")
        val ledger = ScriptedLedger(redis)

        assertThat(ledger.transfer(keys("acct:a"), keys("acct:b"), 3_000)).isFalse()
        assertThat(ledger.transfer(keys("acct:none"), keys("acct:b"), 1)).isFalse()   // a missing account holds 0

        assertThat(balance(keys("acct:a"))).isEqualTo(2_000)
        assertThat(redis.exists(keys("acct:b"))).isFalse()
    }

    @Test
    fun `transfers keep working after the script cache is flushed`(keys: KeySpace) {
        redis.set(keys("acct:a"), "10000")
        val ledger = ScriptedLedger(redis)
        ledger.transfer(keys("acct:a"), keys("acct:b"), 1_000)

        redis.scriptFlush()                                    // what a restart or a failover does to the cache

        assertThat(ledger.transfer(keys("acct:a"), keys("acct:b"), 1_000)).isTrue()
        assertThat(balance(keys("acct:a"))).isEqualTo(8_000)
    }

    @Test
    fun `fifty threads moving money at random never create or destroy any`(keys: KeySpace) {
        val accounts = (0 until 4).map { keys("acct:$it") }
        accounts.forEach { redis.set(it, "25000") }
        val ledger = ScriptedLedger(redis)
        val pool = Executors.newFixedThreadPool(50)

        val jobs = (0 until 50).map { t ->
            CompletableFuture.runAsync({
                val random = Random(t.toLong())
                repeat(40) {
                    val from = accounts[random.nextInt(4)]
                    val to = accounts.filter { it != from }[random.nextInt(3)]
                    ledger.transfer(from, to, 1L + random.nextInt(5_000))
                }
            }, pool)
        }
        jobs.forEach { it.get(15, TimeUnit.SECONDS) }
        pool.shutdown()

        val balances = accounts.map(::balance)
        assertThat(balances.sum()).isEqualTo(100_000)
        assertThat(balances).allSatisfy { assertThat(it).isGreaterThanOrEqualTo(0) }
    }

    @Test
    fun `openAccounts sets every balance`(keys: KeySpace) {
        val balances = (0 until 500).associate { keys("acct:$it") to it * 100L }

        ScriptedLedger(redis).openAccounts(balances)

        assertThat(balances).allSatisfy { k, v -> assertThat(redis.get(k)).isEqualTo(v.toString()) }
    }

    @Test
    fun `a pipeline opens 2,000 accounts far faster than one round trip each`(keys: KeySpace) {
        val ledger = ScriptedLedger(redis)
        val warm = (0 until 200).associate { keys("warm:$it") to 1L }
        ledger.openAccounts(warm)                                  // warm up the JIT and the connection pool
        warm.keys.forEach { redis.set(it, "1") }

        val oneByOne = (0 until 2_000).associate { keys("seq:$it") to 100L }
        val t0 = System.nanoTime()
        oneByOne.forEach { (k, v) -> redis.set(k, v.toString()) }
        val sequentialNanos = System.nanoTime() - t0

        val pipelined = (0 until 2_000).associate { keys("pipe:$it") to 100L }
        val t1 = System.nanoTime()
        ledger.openAccounts(pipelined)
        val pipelineNanos = System.nanoTime() - t1

        // usually 10 to 50 times faster; 3 times leaves room for a busy laptop
        assertThat(pipelineNanos * 3).isLessThan(sequentialNanos)
        assertThat(redis.get(keys("pipe:1999"))).isEqualTo("100")
    }
}
