package sfz.redis.l07.demo

import redis.clients.jedis.RedisClient

/** A token bucket in Lua: 10 tokens, one new token every 500 ms. A burst of 15, then one request every 250 ms. */
// KEYS[1] the bucket (a hash with tokens and ts). ARGV[1] capacity, ARGV[2] ms per new token, ARGV[3] now in ms.
private val TOKEN_BUCKET = """
    local capacity = tonumber(ARGV[1])
    local interval = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])
    local b = redis.call('HMGET', KEYS[1], 'tokens', 'ts')
    local tokens, ts = tonumber(b[1]), tonumber(b[2])
    if tokens == nil then                                -- a bucket nobody used yet starts full
        tokens, ts = capacity, now
    end
    local earned = math.floor((now - ts) / interval)     -- whole tokens since ts
    if earned > 0 then
        tokens = math.min(capacity, tokens + earned)
        ts = ts + earned * interval                      -- keep the part of a token not earned yet
    end
    local allowed = 0
    if tokens > 0 then
        tokens = tokens - 1
        allowed = 1
    end
    redis.call('HSET', KEYS[1], 'tokens', tokens, 'ts', ts)
    redis.call('PEXPIRE', KEYS[1], capacity * interval)  -- idle that long, it is full again: forget it
    return allowed
""".trimIndent()

private const val KEY = "demo:l07:bucket:merchant:m-17"

private fun RedisClient.take(now: Long): Boolean =
    eval(TOKEN_BUCKET, listOf(KEY), listOf("10", "500", now.toString())) == 1L

fun main() {
    RedisClient.builder().hostAndPort("localhost", 6379).build().use { redis ->
        redis.del(KEY)
        val t0 = 1_762_500_000_000L                      // a pretend clock, passed in, so every run is the same

        val burst = (1..15).count { redis.take(t0) }
        println("t = 0.00 s     a burst of 15:                  %2d admitted, %d refused".format(burst, 15 - burst))

        val steady = (1..20).map { redis.take(t0 + it * 250L) }
        val line = steady.joinToString("") { if (it) "+" else "." }
        println("t = 0.25-5.00  one request every 250 ms:       %2d of 20 admitted  %s".format(steady.count { it }, line))

        val afterRest = (1..15).count { redis.take(t0 + 10_000) }
        println("t = 10.00 s    another burst of 15, after 5 s: %2d admitted".format(afterRest))
        println("bucket: ${redis.hgetAll(KEY)}, PTTL ${redis.pttl(KEY)} ms")
    }
}
