package sfz.redis.l05.demo

import redis.clients.jedis.RedisClient
import redis.clients.jedis.params.SetParams

/** Cache-aside in front of a "database" that takes 120 ms: one miss, then hits. */
private var dbCalls = 0

// the system of record: in production an Oracle query behind a connection pool
private fun loadFromDatabase(id: String): String {
    dbCalls++
    Thread.sleep(120)
    return "$id|Fietsen Utrecht|NL|5940"
}

private fun RedisClient.getMerchant(id: String): String {
    val key = "merchant:$id"
    get(key)?.let { return it }                                       // 1. ask Redis first
    val row = loadFromDatabase(id)                                    // 2. a miss: go to the database
    set(key, row, SetParams.setParams().ex(3_600))                    // 3. keep it for an hour
    return row
}

fun main() {
    RedisClient.builder().hostAndPort("localhost", 6379).build().use { redis ->
        redis.del("merchant:m-17")
        redis.get("warm-up")                                          // open a pooled connection first
        for (i in 1..4) {
            val t0 = System.nanoTime()
            val row = redis.getMerchant("m-17")
            println("read %d: %-30s %7.2f ms  (database calls so far: %d)".format(i, row, (System.nanoTime() - t0) / 1e6, dbCalls))
        }
        println("TTL merchant:m-17 = ${redis.ttl("merchant:m-17")} s")
    }
}
