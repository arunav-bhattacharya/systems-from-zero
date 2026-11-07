package sfz.redis.l04.demo

import redis.clients.jedis.RedisClient
import redis.clients.jedis.exceptions.JedisDataException

/**
 * Fills the tiny lab server (port 6380, maxmemory 4mb) under one eviction policy and reports what survived.
 * 200 hot keys are read before every batch; four batches of 800 cold keys are written once and never read.
 * It empties that server first, so never point it at a Redis you care about.
 */
fun main(args: Array<String>) {
    val policy = args.firstOrNull() ?: "allkeys-lru"
    val value = "x".repeat(1_000)
    RedisClient.builder().hostAndPort("localhost", 6380).build().use { redis ->
        redis.flushAll()
        redis.configSet("maxmemory-policy", policy)
        val evictedBefore = redis.stat("stats", "evicted_keys")
        println("policy $policy, maxmemory ${redis.stat("memory", "maxmemory")} bytes")

        val hot = (0 until 200).map { "hot:$it" }
        hot.forEach { redis.set(it, value) }
        for (round in 0 until 4) {
            Thread.sleep(1_100)                                   // let the once-a-second LRU clock move
            hot.forEach { redis.get(it) }                         // read the hot keys: they are young again
            var written = 0
            var error: String? = null
            for (i in 0 until 800) {
                try {
                    redis.set("cold:$round:$i", value)
                    written++
                } catch (e: JedisDataException) {
                    error = e.message
                    break
                }
            }
            println("batch ${round + 1}: wrote $written cold keys" + (error?.let { ", then: $it" } ?: ""))
            if (error != null) break
        }

        val hotLeft = hot.count { redis.exists(it) }
        val cold = (0 until 4).map { round -> (0 until 800).count { redis.exists("cold:$round:$it") } }
        println("hot keys left: $hotLeft of 200")
        println("cold keys left per batch: ${cold.joinToString(", ")}")
        println("evicted_keys: ${redis.stat("stats", "evicted_keys") - evictedBefore}, used_memory: ${redis.stat("memory", "used_memory")}")
    }
}

private fun RedisClient.stat(section: String, field: String): Long =
    info(section).lineSequence().map { it.trim() }.first { it.startsWith("$field:") }.substringAfter(':').toLong()
