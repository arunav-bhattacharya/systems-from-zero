package sfz.redis.l04.demo

import redis.clients.jedis.RedisClient

/**
 * Creates 500,000 idempotency keys that all expire 3 seconds later, then watches how Redis reclaims them:
 * a GET says the key is gone at once, while DBSIZE and used_memory fall only as the active expiry cycle works.
 */
private val CREATE = """
    for i = 1, tonumber(ARGV[1]) do
        redis.call('SET', 'idem:' .. i, 'done', 'PX', ARGV[2])
    end
    return redis.call('DBSIZE')
""".trimIndent()

fun main() {
    RedisClient.builder().hostAndPort("localhost", 6379).build().use { redis ->
        val expiredBefore = redis.stat("expired_keys")
        val start = System.nanoTime()
        fun elapsed() = (System.nanoTime() - start) / 1_000_000
        // one script, so every key gets the same deadline: the script's start time plus 3,000 ms
        redis.eval(CREATE, 0, "500000", "3000")
        println("created 500,000 keys in ${elapsed()} ms, used_memory ${redis.stat("used_memory") / 1_000_000} MB")
        Thread.sleep(2_700 - elapsed())
        repeat(12) {
            val ms = elapsed()
            val get: String? = redis.get("idem:250000")                // a lazy check on one key
            println("t=%5d ms  GET idem:250000 -> %-6s DBSIZE %,7d  expired %,7d  used_memory %3d MB".format(
                ms, get, redis.dbSize(), redis.stat("expired_keys") - expiredBefore, redis.stat("used_memory") / 1_000_000))
            Thread.sleep(150)
        }
    }
}

private fun RedisClient.stat(field: String): Long {
    val section = if (field.startsWith("used_memory")) "memory" else "stats"
    return info(section).lineSequence().map { it.trim() }.first { it.startsWith("$field:") }.substringAfter(':').toLong()
}
