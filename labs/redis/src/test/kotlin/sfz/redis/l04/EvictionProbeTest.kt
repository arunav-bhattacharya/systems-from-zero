package sfz.redis.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import sfz.redis.support.EvictionRedis
import java.util.concurrent.TimeUnit

// talks to a separate Redis 8.10 container with maxmemory 4mb (Docker); each test empties it first
// the fills write 10,000 keys one round trip at a time: 5 to 20 s each, longer when the shared Docker VM is busy
@Timeout(60, unit = TimeUnit.SECONDS)
class EvictionProbeTest {
    private val redis = EvictionRedis.jedis
    private val probe = EvictionProbe(redis)

    companion object {
        @JvmStatic
        @BeforeAll
        fun startServer() {
            check(EvictionRedis.jedis.ping() == "PONG") { "the eviction test Redis did not answer PING" }
        }
    }

    @Test
    fun `stat reads numbers from INFO`() {
        EvictionRedis.reset("noeviction")

        assertThat(probe.stat("memory", "maxmemory")).isEqualTo(EvictionRedis.MAXMEMORY_BYTES)
        assertThat(probe.stat("memory", "used_memory")).isBetween(500_000L, EvictionRedis.MAXMEMORY_BYTES)
        assertThat(probe.stat("stats", "evicted_keys")).isGreaterThanOrEqualTo(0)
    }

    @Test
    fun `noeviction refuses writes once memory is full and still serves reads`() {
        EvictionRedis.reset("noeviction")
        val evictedBefore = probe.stat("stats", "evicted_keys")

        val fill = probe.fill("cache:", 10_000, 1_000)

        // about 2,000 values of 1 KB fit next to the 1.4 MB an empty server uses
        assertThat(fill.written).isBetween(1_000, 3_000)
        assertThat(fill.error).startsWith("OOM command not allowed")
        assertThat(probe.touch((0 until 100).map { "cache:$it" })).isEqualTo(100)   // reads still work
        assertThat(probe.stat("stats", "evicted_keys")).isEqualTo(evictedBefore)   // nothing was evicted
    }

    @Test
    fun `deleting keys makes room again under noeviction`() {
        EvictionRedis.reset("noeviction")
        val first = probe.fill("cache:", 10_000, 1_000)
        assertThat(first.error).isNotNull()

        redis.del(*(0 until 200).map { "cache:$it" }.toTypedArray())                  // DEL is allowed when full
        val second = probe.fill("more:", 100, 1_000)

        assertThat(second).isEqualTo(Fill(100, null))
    }

    @Test
    fun `allkeys-lru accepts every write and evicts older keys to make room`() {
        EvictionRedis.reset("allkeys-lru")
        val evictedBefore = probe.stat("stats", "evicted_keys")

        val fill = probe.fill("cache:", 10_000, 1_000)

        assertThat(fill).isEqualTo(Fill(10_000, null))
        assertThat(redis.dbSize()).isBetween(1_000L, 3_000L)
        assertThat(probe.stat("stats", "evicted_keys") - evictedBefore).isGreaterThan(7_000)
        // Redis evicts before it runs a write, so the write itself can leave it a few KB over the limit
        assertThat(probe.stat("memory", "used_memory")).isLessThan(EvictionRedis.MAXMEMORY_BYTES + 100_000)
    }

    @Test
    fun `allkeys-lru keeps the keys you keep reading`() {
        EvictionRedis.reset("allkeys-lru")
        val hot = (0 until 200).map { "hot:$it" }
        probe.fill("hot:", 200, 1_000)

        // Redis's LRU clock ticks once a second, so spread the cold writes over a few seconds:
        // read the hot keys, wait for the clock to move, write a batch of cold keys, repeat
        repeat(4) { round ->
            Thread.sleep(1_100)
            probe.touch(hot)
            assertThat(probe.fill("cold:$round:", 800, 1_000).error).isNull()
        }

        val hotLeft = hot.count { redis.exists(it) }
        val coldLeft = (0 until 800).count { redis.exists("cold:0:$it") }
        assertThat(hotLeft).isGreaterThanOrEqualTo(180)       // read every round: almost all survive
        assertThat(coldLeft).isLessThan(200)                  // the oldest cold batch: mostly evicted
    }

    @Test
    fun `volatile-lru only evicts keys that have a TTL`() {
        EvictionRedis.reset("volatile-lru")
        probe.fill("session:", 500, 1_000)                    // no TTL: never a candidate

        val cached = probe.fill("cache:", 5_000, 1_000, ttlSeconds = 3_600)
        val sessionsLeft = (0 until 500).count { redis.exists("session:$it") }
        val noTtl = probe.fill("more-sessions:", 5_000, 1_000)

        assertThat(cached).isEqualTo(Fill(5_000, null))       // keys with a TTL made room for each other
        assertThat(sessionsLeft).isEqualTo(500)
        assertThat(noTtl.error).startsWith("OOM")             // ...until they ran out: then it is noeviction
    }
}
