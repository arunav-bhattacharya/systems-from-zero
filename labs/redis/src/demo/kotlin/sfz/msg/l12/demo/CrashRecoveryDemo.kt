package sfz.msg.l12.demo

import redis.clients.jedis.RedisClient
import redis.clients.jedis.StreamEntryID
import redis.clients.jedis.params.XAddParams
import redis.clients.jedis.params.XAutoClaimParams
import redis.clients.jedis.params.XPendingParams
import redis.clients.jedis.params.XReadGroupParams
import redis.clients.jedis.resps.StreamEntry

/** Worker w1 reads three payments and dies before XACK. Worker w3 claims them once they have been idle for 1 s. */
private const val STREAM = "demo:l09:payments"
private const val GROUP = "settlers"

private fun RedisClient.readNew(consumer: String, count: Int): List<StreamEntry> =
    xreadGroup(GROUP, consumer, XReadGroupParams.xReadGroupParams().count(count),
        mapOf(STREAM to StreamEntryID.XREADGROUP_UNDELIVERED_ENTRY))?.firstOrNull()?.value.orEmpty()

private fun RedisClient.printPending() {
    val pending = xpending(STREAM, GROUP, XPendingParams.xPendingParams("-", "+", 10))
    println("  XPENDING: ${pending.size} pending")
    for (p in pending) {
        val payment = xrange(STREAM, p.id, p.id).single().fields["payment"]
        println("    $payment owner=${p.consumerName} idle=${p.idleTime} ms deliveries=${p.deliveredTimes}")
    }
}

fun main() {
    RedisClient.builder().hostAndPort("localhost", 6379).build().use { redis ->
        redis.del(STREAM)
        redis.xgroupCreate(STREAM, GROUP, StreamEntryID.XGROUP_LAST_ENTRY, true)    // XGROUP CREATE ... $ MKSTREAM
        (1..5).forEach { redis.xadd(STREAM, XAddParams.xAddParams(), mapOf("payment" to "p-$it", "amount" to "${1000 + it}")) }

        val w1 = redis.readNew("w1", 3)                            // w1 takes three... and its pod is killed
        val w2 = redis.readNew("w2", 10)                           // w2 takes the rest and settles them
        w2.forEach { redis.xack(STREAM, GROUP, it.id) }
        println("w1 read ${w1.size} and crashed; w2 read ${w2.size} and acknowledged them")
        redis.printPending()

        val early = redis.xautoclaim(STREAM, GROUP, "w3", 1_000, StreamEntryID(0, 0), XAutoClaimParams.xAutoClaimParams().count(100))
        println("w3 XAUTOCLAIM min-idle 1000 ms, right away: claimed ${early.value.size}")

        Thread.sleep(1_100)
        val claimed = redis.xautoclaim(STREAM, GROUP, "w3", 1_000, StreamEntryID(0, 0), XAutoClaimParams.xAutoClaimParams().count(100))
        println("w3 XAUTOCLAIM min-idle 1000 ms, 1.1 s later: claimed ${claimed.value.size}, next cursor ${claimed.key}")
        redis.printPending()
        claimed.value.forEach { redis.xack(STREAM, GROUP, it.id) }  // settle, then ack
        println("w3 acknowledged them. XPENDING total: ${redis.xpending(STREAM, GROUP).total}")
    }
}
