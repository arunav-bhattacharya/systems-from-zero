package sfz.cache.l08

import redis.clients.jedis.RedisClient
import redis.clients.jedis.params.SetParams
import redis.clients.jedis.util.CompareCondition
import java.time.Duration
import java.util.UUID

class IdempotencyStore(
    private val redis: RedisClient,
    private val prefix: String,
    private val pendingTtl: Duration = Duration.ofSeconds(30),
    private val doneTtl: Duration = Duration.ofHours(24),
) {
    sealed interface Begin {
        data class Started(val token: String) : Begin
        data object InProgress : Begin
        data class Replay(val response: String) : Begin
        data object Mismatch : Begin
    }

    fun begin(key: String, requestHash: String): Begin {
        val token = UUID.randomUUID().toString()
        // claim and look in one command (NX and GET together need Redis 7.0+): no gap between "is it there?" and "mine"
        val previous = redis.setGet(prefix + key, "P|$requestHash|$token",
            SetParams.setParams().nx().px(pendingTtl.toMillis()))
            ?: return Begin.Started(token)                       // nil: the key was free, and now it holds our PENDING
        val (state, hash, rest) = previous.split("|", limit = 3)
        return when {
            hash != requestHash -> Begin.Mismatch                // same key, different body: a client bug, not a retry
            state == "D" -> Begin.Replay(rest)                   // finished before: replay the stored response
            else -> Begin.InProgress                             // still running somewhere: 409, retry later
        }
    }

    fun complete(key: String, requestHash: String, token: String, response: String): Boolean {
        val pending = "P|$requestHash|$token"
        // Redis 8.4+: write DONE only if the key still holds OUR pending value; a stale attempt changes nothing
        val reply = redis.set(prefix + key, "D|$requestHash|$response",
            SetParams.setParams().condition(CompareCondition.valueEq(pending)).px(doneTtl.toMillis()))
        return reply != null
    }
}
