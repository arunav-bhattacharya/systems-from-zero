package sfz.cache.l08.demo

import redis.clients.jedis.RedisClient

/** A token bucket and GCRA in Lua: a burst of 10, then one request every 500 ms. The same traffic for both. */
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

// KEYS[1] the theoretical arrival time (TAT) in ms. ARGV[1] burst, ARGV[2] ms per request, ARGV[3] now in ms.
private val GCRA = """
    local burst = tonumber(ARGV[1])
    local interval = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])
    local tat = tonumber(redis.call('GET', KEYS[1])) or now
    if tat < now then tat = now end                      -- a quiet client: its schedule restarts now
    local next = tat + interval                          -- where this request would push the schedule
    if next - now > burst * interval then return 0 end   -- too far ahead of the allowed rate
    redis.call('SET', KEYS[1], next, 'PX', next - now)   -- once the clock catches up, forget it
    return 1
""".trimIndent()

private const val BUCKET_KEY = "demo:l08:bucket:merchant:m-17"
private const val GCRA_KEY = "demo:l08:gcra:merchant:m-17"

private fun run(label: String, take: (Long) -> Boolean) {
    val t0 = 1_762_500_000_000L                          // a pretend clock, passed in, so every run is the same
    val burst = (1..15).count { take(t0) }
    val steady = (1..20).map { take(t0 + it * 250L) }
    val line = steady.joinToString("") { if (it) "+" else "." }
    val afterRest = (1..15).count { take(t0 + 10_000) }
    println("%-13s burst of 15 at t = 0: %2d   every 250 ms for 5 s: %2d of 20 %s   burst after 5 quiet s: %2d".format(
        label, burst, steady.count { it }, line, afterRest))
}

fun main() {
    RedisClient.builder().hostAndPort("localhost", 6379).build().use { redis ->
        redis.del(BUCKET_KEY, GCRA_KEY)
        run("token bucket") { now -> redis.eval(TOKEN_BUCKET, listOf(BUCKET_KEY), listOf("10", "500", now.toString())) == 1L }
        run("GCRA") { now -> redis.eval(GCRA, listOf(GCRA_KEY), listOf("10", "500", now.toString())) == 1L }
        println("token bucket state: ${redis.hgetAll(BUCKET_KEY)}, PTTL ${redis.pttl(BUCKET_KEY)} ms")
        println("GCRA state:         ${redis.get(GCRA_KEY)}, PTTL ${redis.pttl(GCRA_KEY)} ms")
    }
}
