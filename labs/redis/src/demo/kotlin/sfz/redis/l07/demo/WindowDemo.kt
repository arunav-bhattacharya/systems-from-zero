package sfz.redis.l07.demo

import redis.clients.jedis.RedisClient
import redis.clients.jedis.params.IncrexParams
import java.util.UUID
import java.util.concurrent.CompletableFuture
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors

/** Limit: 5 requests per card per minute. A fixed window, a sliding window, and a sliding window done without a script. */
private const val LIMIT = 5
private const val MINUTE = 60_000L
private const val BASE = 1_762_500_000_000L                      // a time that starts a new minute (it divides by 60,000)

private val SLIDING = """
    local now, window, limit = tonumber(ARGV[1]), tonumber(ARGV[2]), tonumber(ARGV[3])
    redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
    if redis.call('ZCARD', KEYS[1]) >= limit then return 0 end
    redis.call('ZADD', KEYS[1], now, ARGV[4])
    redis.call('PEXPIRE', KEYS[1], window)
    return 1
""".trimIndent()

private fun fixed(redis: RedisClient, card: String, now: Long): Boolean {
    val key = "demo:l07:fixed:$card:${now / MINUTE}"                 // one counter per card per minute
    // Redis 8.8: +1 unless that passes 5, and a 60 s TTL set by the same command (ENX: only when there is none)
    val (_, applied) = redis.increx(key, 1, IncrexParams.increxParams().ubound(LIMIT.toLong()).ex(60).enx())
    return applied == 1L                                             // [new value, applied increment]
}

private fun sliding(redis: RedisClient, card: String, now: Long): Boolean =
    redis.eval(SLIDING, listOf("demo:l07:sliding:$card"),
        listOf(now.toString(), MINUTE.toString(), LIMIT.toString(), UUID.randomUUID().toString())) == 1L

private fun slidingWithoutScript(redis: RedisClient, card: String, now: Long): Boolean {
    val key = "demo:l07:sliding:$card"
    redis.zremrangeByScore(key, Double.NEGATIVE_INFINITY, (now - MINUTE).toDouble())
    if (redis.zcard(key) >= LIMIT) return false                      // another pod can run between this and the ZADD
    redis.zadd(key, now.toDouble(), UUID.randomUUID().toString())
    redis.pexpire(key, MINUTE)
    return true
}

private fun burstAtOneInstant(redis: RedisClient, card: String, limiter: (RedisClient, String, Long) -> Boolean): Int {
    val pool = Executors.newFixedThreadPool(32)
    val start = CountDownLatch(1)
    val calls = (0 until 32).map { CompletableFuture.supplyAsync({ start.await(); limiter(redis, card, BASE) }, pool) }
    start.countDown()
    return calls.count { it.get() }.also { pool.shutdown() }
}

fun main() {
    RedisClient.builder().hostAndPort("localhost", 6379).build().use { redis ->
        redis.del("demo:l07:fixed:card:7:${BASE / MINUTE}", "demo:l07:fixed:card:7:${BASE / MINUTE + 1}",
            "demo:l07:sliding:card:7", "demo:l07:sliding:card:8", "demo:l07:sliding:card:9")    // start clean

        // five requests at 0:59.0 to 0:59.4, then five at 1:00.0 to 1:00.4
        val times = (0 until 5).map { BASE + 59_000 + it * 100 } + (0 until 5).map { BASE + MINUTE + it * 100 }
        val f = times.count { fixed(redis, "card:7", it) }
        val s = times.count { sliding(redis, "card:7", it) }
        println("Limit: 5 per card per minute. Ten requests within 1.4 s, across a minute boundary:")
        println("  fixed window, INCREX per minute    admitted %2d of 10".format(f))
        println("  sliding window, one Lua script     admitted %2d of 10".format(s))

        println("32 requests for card:8 at the same instant, from 32 threads:")
        println("  sliding window, ZCARD then ZADD    admitted %2d of 32".format(burstAtOneInstant(redis, "card:8", ::slidingWithoutScript)))
        println("  sliding window, one Lua script     admitted %2d of 32".format(burstAtOneInstant(redis, "card:9", ::sliding)))
    }
}
