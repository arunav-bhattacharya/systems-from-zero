package sfz.redis.l04

import redis.clients.jedis.RedisClient

/** How many writes [EvictionProbe.fill] got through, and the OOM error that stopped it (null if none did). */
data class Fill(val written: Int, val error: String?)

/**
 * Fills a Redis server that has a `maxmemory` limit and reports what the server did about it.
 *
 * The tests point it at a separate server with `maxmemory 4mb`, set the eviction policy, and then
 * check what survived. Your code never changes the policy.
 */
class EvictionProbe(private val redis: RedisClient) {

    /**
     * SETs the keys `"$prefix$i"` for `i` in `0 until count`. Each value is [valueBytes] bytes long
     * (`"x".repeat(valueBytes)` is fine). If [ttlSeconds] is not null, give each key that TTL
     * (`SetParams().ex(ttlSeconds)`).
     *
     * When the server refuses a write because it is out of memory, Jedis throws a
     * `JedisDataException` whose message starts with `OOM`. Stop at the first one and return how many
     * writes succeeded before it, with its message. Let any other exception escape. If every write
     * succeeds, return `Fill(count, null)`.
     */
    fun fill(prefix: String, count: Int, valueBytes: Int, ttlSeconds: Long? = null): Fill {
        TODO("lesson 4 lab: SET in a loop, stop at the first OOM error")
    }

    /**
     * Reads every key in [keys] with GET and returns how many still exist. Use GET, not EXISTS:
     * a read refreshes the key's last-access time, which is what keeps a hot key alive under LRU.
     */
    fun touch(keys: List<String>): Int {
        TODO("lesson 4 lab: GET each key, count the ones that are not null")
    }

    /**
     * One number from INFO. `stat("stats", "evicted_keys")` reads the line `evicted_keys:1234` from
     * `redis.info("stats")` and returns 1234. Lines end with `\r\n`, so trim them.
     */
    fun stat(section: String, field: String): Long {
        TODO("lesson 4 lab: find the line that starts with \"field:\" and parse the number after the colon")
    }
}
