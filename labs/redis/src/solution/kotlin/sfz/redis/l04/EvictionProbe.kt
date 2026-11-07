package sfz.redis.l04

import redis.clients.jedis.RedisClient
import redis.clients.jedis.exceptions.JedisDataException
import redis.clients.jedis.params.SetParams

data class Fill(val written: Int, val error: String?)

class EvictionProbe(private val redis: RedisClient) {

    fun fill(prefix: String, count: Int, valueBytes: Int, ttlSeconds: Long? = null): Fill {
        val value = "x".repeat(valueBytes)
        val params = ttlSeconds?.let { SetParams().ex(it) }
        for (i in 0 until count) {
            try {
                if (params == null) redis.set("$prefix$i", value) else redis.set("$prefix$i", value, params)
            } catch (e: JedisDataException) {
                // under noeviction (or with nothing evictable) Redis refuses the write and keeps going
                if (e.message?.startsWith("OOM") == true) return Fill(i, e.message)
                throw e
            }
        }
        return Fill(count, null)
    }

    // GET (not EXISTS) on purpose: a read refreshes the key's LRU stamp, which is what keeps it hot
    fun touch(keys: List<String>): Int = keys.count { redis.get(it) != null }

    fun stat(section: String, field: String): Long =
        redis.info(section).lineSequence()
            .map { it.trim() }
            .first { it.startsWith("$field:") }
            .substringAfter(':')
            .toLong()
}
