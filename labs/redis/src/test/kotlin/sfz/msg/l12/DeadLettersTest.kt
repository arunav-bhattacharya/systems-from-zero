package sfz.msg.l12

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.extension.ExtendWith
import redis.clients.jedis.StreamEntryID
import redis.clients.jedis.params.XAddParams
import redis.clients.jedis.params.XClaimParams
import redis.clients.jedis.params.XReadGroupParams
import sfz.redis.support.KeySpace
import sfz.redis.support.TestRedis
import sfz.redis.support.WithRedis
import java.util.concurrent.TimeUnit

// talks to the shared Redis 8.10 container (Docker)
@ExtendWith(WithRedis::class)
@Timeout(20, unit = TimeUnit.SECONDS)
class DeadLettersTest {
    private val redis = TestRedis.jedis

    /** Adds one payment, delivers it to w1, then has it claimed (min idle 0) until it was delivered [times] times. */
    private fun deliveredTimes(stream: String, payment: String, times: Int): StreamEntryID {
        val id = redis.xadd(stream, XAddParams.xAddParams(), mapOf("payment" to payment, "amount" to "1250"))
        redis.xreadGroup("settlers", "w1", XReadGroupParams.xReadGroupParams().count(1),
            mapOf(stream to StreamEntryID.XREADGROUP_UNDELIVERED_ENTRY))
        repeat(times - 1) { redis.xclaim(stream, "settlers", "w2", 0, XClaimParams.xClaimParams(), id) }
        return id
    }

    private fun setUp(keys: KeySpace): String =
        keys("payments").also { redis.xgroupCreate(it, "settlers", StreamEntryID.XGROUP_LAST_ENTRY, true) }

    @Test
    fun `an entry delivered more times than the limit moves to the dead-letter stream`(keys: KeySpace) {
        val stream = setUp(keys)
        val poison = deliveredTimes(stream, "p-13", times = 6)

        val moved = DeadLetters(redis, stream, "settlers", keys("payments:dead"), maxDeliveries = 5).sweep()

        assertThat(moved).containsExactly(poison)
        assertThat(redis.xpending(stream, "settlers").total).isZero()       // acknowledged: nobody claims it again
        assertThat(redis.xlen(keys("payments:dead"))).isEqualTo(1)
    }

    @Test
    fun `entries at or under the limit stay pending`(keys: KeySpace) {
        val stream = setUp(keys)
        deliveredTimes(stream, "p-1", times = 1)
        deliveredTimes(stream, "p-2", times = 5)
        val poison = deliveredTimes(stream, "p-3", times = 7)

        val moved = DeadLetters(redis, stream, "settlers", keys("payments:dead"), maxDeliveries = 5).sweep()

        assertThat(moved).containsExactly(poison)
        assertThat(redis.xpending(stream, "settlers").total).isEqualTo(2)
    }

    @Test
    fun `the dead-letter copy keeps the fields and says where it came from`(keys: KeySpace) {
        val stream = setUp(keys)
        val poison = deliveredTimes(stream, "p-13", times = 6)

        DeadLetters(redis, stream, "settlers", keys("payments:dead"), maxDeliveries = 5).sweep()

        val copy = redis.xrange(keys("payments:dead"), "-", "+").single().fields
        assertThat(copy).containsEntry("payment", "p-13")
            .containsEntry("amount", "1250")
            .containsEntry("original-id", poison.toString())
            .containsEntry("group", "settlers")
            .containsEntry("deliveries", "6")
    }

    @Test
    fun `a sweep with nothing over the limit moves nothing`(keys: KeySpace) {
        val stream = setUp(keys)
        deliveredTimes(stream, "p-1", times = 2)

        assertThat(DeadLetters(redis, stream, "settlers", keys("payments:dead"), maxDeliveries = 5).sweep()).isEmpty()
        assertThat(redis.exists(keys("payments:dead"))).isFalse()
    }
}
