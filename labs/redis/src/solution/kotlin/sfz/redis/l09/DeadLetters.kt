package sfz.redis.l09

import redis.clients.jedis.RedisClient
import redis.clients.jedis.StreamEntryID
import redis.clients.jedis.params.XAddParams
import redis.clients.jedis.params.XPendingParams

class DeadLetters(
    private val redis: RedisClient,
    private val stream: String,
    private val group: String,
    private val deadStream: String,
    private val maxDeliveries: Long,
) {
    fun sweep(): List<StreamEntryID> {
        val moved = mutableListOf<StreamEntryID>()
        // the extended form lists each pending entry with its owner, idle time and delivery count
        for (p in redis.xpending(stream, group, XPendingParams.xPendingParams("-", "+", 100))) {
            if (p.deliveredTimes <= maxDeliveries) continue
            val fields = redis.xrange(stream, p.id, p.id).firstOrNull()?.fields.orEmpty()   // empty if trimmed
            val copy = fields + mapOf(
                "original-id" to p.id.toString(),
                "group" to group,
                "deliveries" to p.deliveredTimes.toString(),
            )
            // copy and ack together: both happen or neither does (lesson 6)
            redis.multi().use { tx ->
                tx.xadd(deadStream, XAddParams.xAddParams(), copy)
                tx.xack(stream, group, p.id)
                tx.exec()
            }
            moved += p.id
        }
        return moved
    }
}
