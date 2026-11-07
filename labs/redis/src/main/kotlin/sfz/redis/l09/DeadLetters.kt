package sfz.redis.l09

import redis.clients.jedis.RedisClient
import redis.clients.jedis.StreamEntryID

/**
 * Takes poison messages out of the way. An entry whose handler fails every time is claimed and retried forever, and
 * each claim adds one to its delivery count. Once an entry has been delivered more than [maxDeliveries] times, this
 * sweeper copies it to [deadStream] for a person to look at, and acknowledges it in [stream] so nobody claims it again.
 */
class DeadLetters(
    private val redis: RedisClient,
    private val stream: String,
    private val group: String,
    private val deadStream: String,
    private val maxDeliveries: Long,
) {
    /**
     * Moves every entry pending in [group] that was delivered more than [maxDeliveries] times, and returns their IDs.
     *
     * 1. `XPENDING <stream> <group> - + 100`, in Jedis
     *    `redis.xpending(stream, group, XPendingParams.xPendingParams("-", "+", 100))`. Each item has `id`,
     *    `consumerName`, `idleTime` and `deliveredTimes`.
     * 2. For each item with `deliveredTimes > maxDeliveries`, read its fields with `redis.xrange(stream, id, id)`.
     *    The list is empty if the entry was trimmed away; then copy no fields.
     * 3. Copy it and acknowledge it in ONE transaction, so a crash can't leave it in both places or in neither:
     *    `redis.multi().use { tx -> tx.xadd(deadStream, XAddParams.xAddParams(), fields); tx.xack(stream, group, id);
     *    tx.exec() }`. Add three fields to the copy: `original-id`, `group` and `deliveries`.
     */
    fun sweep(): List<StreamEntryID> {
        TODO("lesson 9 lab: XPENDING, then XADD to the dead-letter stream and XACK in one MULTI")
    }
}
