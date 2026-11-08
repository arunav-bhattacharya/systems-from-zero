package sfz.cache.l07

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.extension.ExtendWith
import sfz.redis.support.KeySpace
import sfz.redis.support.TestRedis
import sfz.redis.support.WithRedis
import java.time.Duration
import java.util.concurrent.CompletableFuture
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.TimeUnit.SECONDS

// talks to the shared Redis 8.10 container (Docker)
@ExtendWith(WithRedis::class)
@Timeout(10, unit = TimeUnit.SECONDS)
class LeasedMerchantCacheTest {
    private val redis = TestRedis.jedis
    private val noPause = Runnable {}

    private fun cache(
        keys: KeySpace,
        table: MerchantTable,
        beforeFill: Runnable = noPause,
        lease: Duration = Duration.ofSeconds(10),
        patience: Duration = Duration.ofSeconds(2),
    ) = LeasedMerchantCache(redis, table, keys.prefix, lease, patience, beforeFill)

    /** A pause for one reader's fill: [atFill] opens when it gets there, and it waits for [release]. */
    private class Gate : Runnable {
        val atFill = CountDownLatch(1)
        val release = CountDownLatch(1)
        override fun run() {
            atFill.countDown()
            release.await(5, SECONDS)
        }
    }

    @Test
    fun `a miss takes the lease, fills the value with a TTL and gives the lease back`(keys: KeySpace) {
        val table = MerchantTable().apply { write("m-17", "Fietsen Utrecht") }
        val c = cache(keys, table)

        assertThat(c.get("m-17")).isEqualTo("Fietsen Utrecht")

        assertThat(redis.get(c.valueKey("m-17"))).isEqualTo("Fietsen Utrecht")
        assertThat(redis.ttl(c.valueKey("m-17"))).isBetween(3_500L, 3_600L)
        assertThat(redis.exists(c.leaseKey("m-17"))).isFalse()
        assertThat(table.reads).isEqualTo(1)
    }

    @Test
    fun `a hit never touches the table`(keys: KeySpace) {
        val table = MerchantTable().apply { write("m-17", "Fietsen Utrecht") }
        val c = cache(keys, table)

        repeat(5) { assertThat(c.get("m-17")).isEqualTo("Fietsen Utrecht") }

        assertThat(table.reads).isEqualTo(1)
    }

    @Test
    fun `a fill whose lease was deleted by a write is refused`(keys: KeySpace) {
        val table = MerchantTable().apply { write("m-17", "Fietsen Utrecht") }
        val gate = Gate()
        val podA = cache(keys, table, gate)
        val podB = cache(keys, table)

        val readerA = CompletableFuture.supplyAsync { podA.get("m-17") }
        assertThat(gate.atFill.await(5, SECONDS)).isTrue()               // A has read version 1
        table.write("m-17", "Velo Utrecht")                              // the writer commits version 2
        podB.afterWrite("m-17")                                          // and revokes A's lease
        gate.release.countDown()

        assertThat(readerA.get(5, SECONDS)).isEqualTo("Fietsen Utrecht")
        assertThat(redis.get(podA.valueKey("m-17"))).isNull()             // A's late fill changed nothing
        assertThat(podB.get("m-17")).isEqualTo("Velo Utrecht")           // the next miss loads version 2
        assertThat(redis.get(podA.valueKey("m-17"))).isEqualTo("Velo Utrecht")
        assertThat(table.reads).isEqualTo(2)
    }

    @Test
    fun `a reader that misses while another holds the lease waits for that value instead of reading the table`(keys: KeySpace) {
        val table = MerchantTable().apply { write("m-17", "Fietsen Utrecht") }
        val gate = Gate()
        val podA = cache(keys, table, gate)
        val podB = cache(keys, table)

        val readerA = CompletableFuture.supplyAsync { podA.get("m-17") }
        assertThat(gate.atFill.await(5, SECONDS)).isTrue()               // A holds the lease
        val readerB = CompletableFuture.supplyAsync { podB.get("m-17") }
        Thread.sleep(150)                                                // B misses, finds the lease taken, polls
        assertThat(readerB.isDone).isFalse()
        gate.release.countDown()                                         // A fills

        assertThat(readerA.get(5, SECONDS)).isEqualTo("Fietsen Utrecht")
        assertThat(readerB.get(5, SECONDS)).isEqualTo("Fietsen Utrecht")
        assertThat(table.reads).isEqualTo(1)                             // two misses, one query
    }

    @Test
    fun `a reader out of patience answers from the table and does not fill`(keys: KeySpace) {
        val table = MerchantTable().apply { write("m-17", "Fietsen Utrecht") }
        val gate = Gate()
        val podA = cache(keys, table, gate)
        val impatient = cache(keys, table, patience = Duration.ofMillis(200))

        val readerA = CompletableFuture.supplyAsync { podA.get("m-17") }
        assertThat(gate.atFill.await(5, SECONDS)).isTrue()
        val t0 = System.nanoTime()
        assertThat(impatient.get("m-17")).isEqualTo("Fietsen Utrecht")
        val waitedMillis = (System.nanoTime() - t0) / 1_000_000

        assertThat(waitedMillis).isGreaterThanOrEqualTo(190L)
        assertThat(redis.get(podA.valueKey("m-17"))).isNull()             // only the lease holder fills
        assertThat(table.reads).isEqualTo(2)
        gate.release.countDown()
        readerA.get(5, SECONDS)
    }

    @Test
    fun `the lease of a reader that crashed before its fill expires, and the next miss fills`(keys: KeySpace) {
        val table = MerchantTable().apply { write("m-17", "Fietsen Utrecht") }
        val crashing = cache(keys, table, beforeFill = { throw IllegalStateException("pod OOM-killed") },
            lease = Duration.ofMillis(300))

        assertThatThrownBy { crashing.get("m-17") }.hasMessageContaining("OOM-killed")
        assertThat(redis.pttl(crashing.leaseKey("m-17"))).isBetween(1L, 300L)   // left behind, with a deadline

        Thread.sleep(400)
        val next = cache(keys, table, patience = Duration.ofMillis(50))
        assertThat(next.get("m-17")).isEqualTo("Fietsen Utrecht")
        assertThat(redis.get(next.valueKey("m-17"))).isEqualTo("Fietsen Utrecht")
    }

    @Test
    fun `afterWrite deletes the value and the lease`(keys: KeySpace) {
        val table = MerchantTable().apply { write("m-17", "Fietsen Utrecht") }
        val c = cache(keys, table)
        c.get("m-17")
        redis.set(c.leaseKey("m-17"), "another-readers-token")

        c.afterWrite("m-17")

        assertThat(redis.exists(c.valueKey("m-17"))).isFalse()
        assertThat(redis.exists(c.leaseKey("m-17"))).isFalse()
    }

    @Test
    fun `an unknown merchant returns null and leaves neither a value nor a lease behind`(keys: KeySpace) {
        val c = cache(keys, MerchantTable())

        assertThat(c.get("m-404")).isNull()

        assertThat(redis.exists(c.valueKey("m-404"))).isFalse()
        assertThat(redis.exists(c.leaseKey("m-404"))).isFalse()
    }
}
