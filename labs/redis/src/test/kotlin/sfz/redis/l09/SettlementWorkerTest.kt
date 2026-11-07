package sfz.redis.l09

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.extension.ExtendWith
import redis.clients.jedis.StreamEntryID
import redis.clients.jedis.params.XAddParams
import sfz.redis.support.KeySpace
import sfz.redis.support.TestRedis
import sfz.redis.support.WithRedis
import java.time.Duration
import java.util.Collections
import java.util.concurrent.TimeUnit

// talks to the shared Redis 8.10 container (Docker)
@ExtendWith(WithRedis::class)
@Timeout(20, unit = TimeUnit.SECONDS)
class SettlementWorkerTest {
    private val redis = TestRedis.jedis

    private fun add(stream: String, payment: String, amount: Int = 1250): StreamEntryID =
        redis.xadd(stream, XAddParams.xAddParams(), mapOf("payment" to payment, "amount" to amount.toString()))

    /** A worker that records the payment ids it settled. */
    private class Recording(val failOn: (String) -> Boolean = { false }) {
        val settled: MutableList<String> = Collections.synchronizedList(mutableListOf())
        val handler = SettlementWorker.Handler { entry ->
            val payment = entry.fields["payment"]!!
            if (failOn(payment)) throw IllegalStateException("issuer timeout for $payment")
            settled += payment
        }
    }

    private fun pendingCount(stream: String): Long = redis.xpending(stream, "settlers").total

    @Test
    fun `a group created at the end of the stream sees only entries added after it`(keys: KeySpace) {
        val stream = keys("payments")
        add(stream, "p-1")
        add(stream, "p-2")
        val r = Recording()
        val worker = SettlementWorker(redis, stream, "settlers", "w1", r.handler)

        assertThat(worker.createGroup()).isTrue()
        assertThat(worker.createGroup()).isFalse()                          // every pod may call it on start
        add(stream, "p-3")
        add(stream, "p-4")

        assertThat(worker.processNew(10)).isEqualTo(2)
        assertThat(r.settled).containsExactly("p-3", "p-4")
    }

    @Test
    fun `processNew settles each entry once and acknowledges it`(keys: KeySpace) {
        val stream = keys("payments")
        val r = Recording()
        val worker = SettlementWorker(redis, stream, "settlers", "w1", r.handler).also { it.createGroup() }
        (1..5).forEach { add(stream, "p-$it") }

        assertThat(worker.processNew(10)).isEqualTo(5)
        assertThat(worker.processNew(10)).isEqualTo(0)

        assertThat(r.settled).containsExactly("p-1", "p-2", "p-3", "p-4", "p-5")
        assertThat(pendingCount(stream)).isZero()
        assertThat(redis.xlen(stream)).isEqualTo(5)                        // acked entries stay in the log
    }

    @Test
    fun `two workers in one group split the entries between them`(keys: KeySpace) {
        val stream = keys("payments")
        val r1 = Recording()
        val r2 = Recording()
        val w1 = SettlementWorker(redis, stream, "settlers", "w1", r1.handler).also { it.createGroup() }
        val w2 = SettlementWorker(redis, stream, "settlers", "w2", r2.handler)
        (1..10).forEach { add(stream, "p-$it") }

        w1.processNew(4)
        w2.processNew(10)

        assertThat(r1.settled).hasSize(4)
        assertThat(r2.settled).hasSize(6)
        assertThat(r1.settled + r2.settled).containsExactlyInAnyOrderElementsOf((1..10).map { "p-$it" })
    }

    @Test
    fun `an entry whose handler throws stays pending for that worker`(keys: KeySpace) {
        val stream = keys("payments")
        val r = Recording(failOn = { it == "p-3" })
        val worker = SettlementWorker(redis, stream, "settlers", "w1", r.handler).also { it.createGroup() }
        (1..5).forEach { add(stream, "p-$it") }

        assertThat(worker.processNew(10)).isEqualTo(4)

        val summary = redis.xpending(stream, "settlers")
        assertThat(summary.total).isEqualTo(1)
        assertThat(summary.consumerMessageCount).containsEntry("w1", 1L)
    }

    @Test
    fun `another worker recovers a crashed worker's entries once they have been idle long enough`(keys: KeySpace) {
        val stream = keys("payments")
        val crashed = Recording(failOn = { true })                          // reads, then dies before any XACK
        SettlementWorker(redis, stream, "settlers", "w1", crashed.handler).also { it.createGroup() }.let { w1 ->
            (1..3).forEach { add(stream, "p-$it") }
            assertThat(w1.processNew(10)).isZero()
        }
        val r2 = Recording()
        val w2 = SettlementWorker(redis, stream, "settlers", "w2", r2.handler)

        // just read: w1 might only be slow, so its entries are not up for grabs yet
        assertThat(w2.recoverAbandoned(Duration.ofSeconds(2), 100)).isZero()

        var recovered = 0
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(8)
        while (recovered < 3 && System.nanoTime() < deadline) {
            Thread.sleep(100)
            recovered += w2.recoverAbandoned(Duration.ofSeconds(2), 100)
        }

        assertThat(recovered).isEqualTo(3)
        assertThat(r2.settled).containsExactlyInAnyOrder("p-1", "p-2", "p-3")
        assertThat(pendingCount(stream)).isZero()
    }

    @Test
    fun `recovery walks the whole pending list, a page at a time`(keys: KeySpace) {
        val stream = keys("payments")
        val crashed = Recording(failOn = { true })
        val w1 = SettlementWorker(redis, stream, "settlers", "w1", crashed.handler).also { it.createGroup() }
        redis.pipelined().use { pipe ->
            (1..250).forEach { pipe.xadd(stream, XAddParams.xAddParams(), mapOf("payment" to "p-$it", "amount" to "1")) }
            pipe.sync()
        }
        assertThat(w1.processNew(250)).isZero()
        Thread.sleep(50)

        val r2 = Recording()
        val recovered = SettlementWorker(redis, stream, "settlers", "w2", r2.handler).recoverAbandoned(Duration.ofMillis(10), 100)

        assertThat(recovered).isEqualTo(250)                               // three pages of up to 100
        assertThat(pendingCount(stream)).isZero()
    }
}
