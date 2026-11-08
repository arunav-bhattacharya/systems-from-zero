package sfz.cache.l10

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.extension.ExtendWith
import sfz.redis.support.KeySpace
import sfz.redis.support.TestRedis
import sfz.redis.support.WithRedis
import java.util.concurrent.TimeUnit

// talks to the shared Redis 8.10 container (Docker); the slow log is server-wide, so each slow log test resets it
@ExtendWith(WithRedis::class)
@Timeout(30, unit = TimeUnit.SECONDS)
class DiagnosticsTest {
    private val redis = TestRedis.jedis
    private val diagnostics = Diagnostics(redis)

    /** Keeps the one command thread busy for about [millis] ms, like a big KEYS or HGETALL would. */
    private fun busy(millis: Int) {
        redis.eval("local stop = os.clock() + ARGV[1] / 1000 while os.clock() < stop do end return 1", 0, millis.toString())
    }

    /** `calls=` for one command in INFO commandstats (0 if it never ran). */
    private fun calls(command: String): Long =
        redis.info("commandstats").lineSequence()
            .firstOrNull { it.startsWith("cmdstat_$command:") }
            ?.let { Regex("calls=(\\d+)").find(it)!!.groupValues[1].toLong() } ?: 0

    @Test
    fun `slowest finds the slow script among fast commands`(keys: KeySpace) {
        redis.slowlogReset()
        busy(30)
        repeat(100) { redis.get(keys("payment:$it")) }            // microseconds each: under the 10 ms threshold

        val slow = diagnostics.slowest(10)

        assertThat(slow).hasSize(1)
        assertThat(slow[0].args()[0]).isEqualToIgnoringCase("EVAL")
        assertThat(slow[0].micros()).isGreaterThanOrEqualTo(25_000)
    }

    @Test
    fun `slowest puts the command that took longest first, not the newest`() {
        redis.slowlogReset()
        busy(60)
        busy(15)                                                   // newer, and SLOWLOG GET lists it first

        val slow = diagnostics.slowest(2)

        assertThat(slow).hasSize(2)
        assertThat(slow[0].args()).contains("60")
        assertThat(slow[1].args()).contains("15")
        assertThat(slow[0].micros()).isGreaterThan(slow[1].micros())
        assertThat(slow[0].id()).isLessThan(slow[1].id())          // ids grow with time: the slowest came first
    }

    @Test
    fun `slowest returns at most n entries`() {
        redis.slowlogReset()
        repeat(3) { busy(12) }

        assertThat(diagnostics.slowest(2)).hasSize(2)
        assertThat(diagnostics.slowest(10)).hasSize(3)
    }

    @Test
    fun `biggestKeys finds the hash that grew and the list behind it`(keys: KeySpace) {
        redis.hset(keys("merchant:7:payments"), (1..5_000).associate { "p-$it" to "1250" })
        redis.rpush(keys("settlement:queue"), *(1..2_000).map { "batch-$it" }.toTypedArray())
        (1..300).forEach { redis.set(keys("payment:$it"), "approved") }

        val big = diagnostics.biggestKeys(keys.prefix + "*", 2)

        assertThat(big.map { it.key() }).containsExactly(keys("merchant:7:payments"), keys("settlement:queue"))
        assertThat(big.map { it.type() }).containsExactly("hash", "list")
        assertThat(big[0].bytes()).isGreaterThan(50_000)
        assertThat(big[0].bytes()).isGreaterThan(big[1].bytes())
    }

    @Test
    fun `biggestKeys only looks at keys that match the pattern`(keys: KeySpace) {
        val other = KeySpace.fresh("other-team")
        try {
            redis.hset(other("huge"), (1..3_000).associate { "f-$it" to "x" })
            redis.set(keys("payment:1"), "approved")
            redis.set(keys("payment:2"), "declined")

            val big = diagnostics.biggestKeys(keys.prefix + "*", 10)

            assertThat(big.map { it.key() }).containsExactlyInAnyOrder(keys("payment:1"), keys("payment:2"))
        } finally {
            other.clear()
        }
    }

    @Test
    fun `biggestKeys walks the keyspace with SCAN and never sends KEYS`(keys: KeySpace) {
        (1..1_200).forEach { redis.set(keys("payment:$it"), "approved") }
        val keysBefore = calls("keys")
        val scansBefore = calls("scan")

        val big = diagnostics.biggestKeys(keys.prefix + "*", 5)

        assertThat(big).hasSize(5)
        assertThat(calls("keys")).isEqualTo(keysBefore)
        assertThat(calls("scan") - scansBefore).isGreaterThanOrEqualTo(2)   // many small steps, not one big one
    }
}
