package sfz.redis.l07

import redis.clients.jedis.RedisClient
import java.time.Duration

/**
 * The idempotency-key record behind `POST /payments`: one string key per `Idempotency-Key` header, so that a retried
 * request never charges the card twice.
 *
 * The value of `prefix + key` is one of two states, written with `|` between the parts:
 *
 * - `P|<requestHash>|<token>` while the first request is running (PENDING). It expires after [pendingTtl], so a pod
 *   that crashes mid-request doesn't block the key forever. The token is random and says which attempt owns it.
 * - `D|<requestHash>|<response>` once it finished (DONE), kept for [doneTtl]. The response is stored exactly as it
 *   was sent, and may itself contain `|`.
 *
 * The request hash is a digest of the request body that the caller computes. It lets the store tell a real retry
 * (same key, same body) from a client bug (same key, different body).
 */
class IdempotencyStore(
    private val redis: RedisClient,
    private val prefix: String,
    private val pendingTtl: Duration = Duration.ofSeconds(30),
    private val doneTtl: Duration = Duration.ofHours(24),
) {
    /** What [begin] found. */
    sealed interface Begin {
        /** This request owns the key now: do the work, then call [complete] with this token. */
        data class Started(val token: String) : Begin

        /** Another request with this key and body is still running. Answer 409 Conflict and let the client retry. */
        data object InProgress : Begin

        /** This request ran before: send back [response] as it is, and do nothing else. */
        data class Replay(val response: String) : Begin

        /** The key was used before for a different body. Answer 422 Unprocessable Content. */
        data object Mismatch : Begin
    }

    /**
     * Claims [key] for a request whose body hashes to [requestHash], or reports what is already there, in ONE command:
     * `SET <prefix+key> P|<hash>|<token> NX GET PX <pendingTtl>`. In Jedis that is
     * `redis.setGet(k, value, SetParams.setParams().nx().px(...))`, with a fresh `UUID.randomUUID().toString()` as
     * the token.
     *
     * - It returns null when the key did not exist: Redis stored your PENDING value. Return [Begin.Started].
     * - Otherwise it returns the value that is there and writes nothing. Split it with `split("|", limit = 3)`:
     *   a different hash is a [Begin.Mismatch]; with the same hash, `D` is a [Begin.Replay] of the third part and
     *   `P` is [Begin.InProgress].
     */
    fun begin(key: String, requestHash: String): Begin {
        TODO("lesson 7 lab: SET NX GET PX, then read what was there")
    }

    /**
     * Turns this attempt's PENDING value into DONE with [response], kept for [doneTtl], but only if the key still
     * holds exactly `P|<requestHash>|<token>`. If the pending entry expired and another attempt took the key over,
     * write nothing and return false.
     *
     * One command on Redis 8.4+: `SET <k> D|<hash>|<response> IFEQ P|<hash>|<token> PX <doneTtl>`, which is
     * `redis.set(k, done, SetParams.setParams().condition(CompareCondition.valueEq(pending)).px(...))` in Jedis. It
     * returns "OK" when it wrote and null when the value didn't match. (Before 8.4 the same check-and-set is a Lua
     * script: GET, compare, SET.)
     */
    fun complete(key: String, requestHash: String, token: String, response: String): Boolean {
        TODO("lesson 7 lab: SET ... IFEQ the pending value")
    }
}
