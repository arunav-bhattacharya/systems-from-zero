package sfz.cache.l07

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.extension.ExtendWith
import sfz.redis.support.KeySpace
import sfz.redis.support.TestRedis
import sfz.redis.support.WithRedis
import java.time.Duration
import java.util.concurrent.TimeUnit

// talks to the shared Redis 8.10 container (Docker)
@ExtendWith(WithRedis::class)
@Timeout(10, unit = TimeUnit.SECONDS)
class StaleSetRaceTest {
    private val redis = TestRedis.jedis

    private fun tableWith(id: String) = MerchantTable().apply { write(id, "Fietsen Utrecht") }

    @Test
    fun `naive cache-aside ends with the old name in Redis after the writer's delete`(keys: KeySpace) {
        val table = tableWith("m-17")

        val outcome = StaleSetRace.run(table, "m-17", "Velo Utrecht") { pause ->
            NaiveMerchantCache(redis, table, keys.prefix, pause)
        }

        assertThat(outcome.database).isEqualTo("Velo Utrecht")
        assertThat(outcome.readerA).isEqualTo("Fietsen Utrecht")          // fine: A read before the commit
        assertThat(outcome.readerB).isEqualTo("Fietsen Utrecht")          // stale: B read long after it
        val key = NaiveMerchantCache(redis, table, keys.prefix) {}.key("m-17")
        assertThat(redis.get(key)).isEqualTo("Fietsen Utrecht")
        assertThat(redis.ttl(key)).isGreaterThan(3_500L)                   // and it stays wrong for an hour
    }

    @Test
    fun `the interleaving is decided by latches, so twenty runs give twenty stale caches`(keys: KeySpace) {
        val stale = (1..20).count { i ->
            val table = tableWith("m-$i")
            val outcome = StaleSetRace.run(table, "m-$i", "Velo $i") { pause ->
                NaiveMerchantCache(redis, table, keys.prefix, pause)
            }
            outcome.readerB != outcome.database
        }
        assertThat(stale).isEqualTo(20)
    }

    @Test
    fun `the same timeline against the lease cache ends with the new name`(keys: KeySpace) {
        val table = tableWith("m-17")
        val reference = LeasedMerchantCache(redis, table, keys.prefix, Duration.ofSeconds(10), Duration.ofSeconds(1)) {}

        val outcome = StaleSetRace.run(table, "m-17", "Velo Utrecht") { pause ->
            LeasedMerchantCache(redis, table, keys.prefix, Duration.ofSeconds(10), Duration.ofSeconds(1), pause)
        }

        assertThat(outcome.readerA).isEqualTo("Fietsen Utrecht")
        assertThat(outcome.readerB).isEqualTo("Velo Utrecht")
        assertThat(redis.get(reference.valueKey("m-17"))).isEqualTo("Velo Utrecht")
    }
}
