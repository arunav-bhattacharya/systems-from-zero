package sfz.cache.l07

import redis.clients.jedis.RedisClient
import redis.clients.jedis.params.SetParams

/**
 * One pod's merchant cache in Redis, in front of a [MerchantTable]. Several instances can share one
 * Redis and one table: each instance plays a different pod.
 */
interface MerchantCache {
    /** The read path: the merchant's name from Redis, or from the table on a miss. Null if the table has no row. */
    fun get(id: String): String?

    /** The write path, called after the table's write has committed: make the cache forget the old row. */
    fun afterWrite(id: String)
}

/**
 * Plain cache-aside from lesson 6, with delete-on-write: GET; on a miss read the table and SET with a
 * TTL; after a write, DEL. It has the stale-set race this lesson is about. Done for you.
 *
 * @param beforeFill runs after the table read and before the SET. Real code would pass `{}`. The race
 *   harness passes a pause there, which is how a test makes a slow reader on purpose.
 */
class NaiveMerchantCache(
    private val redis: RedisClient,
    private val table: MerchantTable,
    private val prefix: String,
    private val beforeFill: Runnable,
) : MerchantCache {
    /** `<prefix>merchant:{<id>}`. The braces are a hash tag (lesson 10); here they only make the key easy to read. */
    fun key(id: String): String = "${prefix}merchant:{$id}"

    override fun get(id: String): String? {
        redis.get(key(id))?.let { return it }            // a hit
        val row = table.read(id) ?: return null          // a miss: query the table
        beforeFill.run()                                 // a slow reader is slow right here
        redis.set(key(id), row.name, SetParams.setParams().ex(TTL_SECONDS))
        return row.name
    }

    override fun afterWrite(id: String) {
        redis.del(key(id))
    }

    companion object {
        const val TTL_SECONDS = 3_600L
    }
}
