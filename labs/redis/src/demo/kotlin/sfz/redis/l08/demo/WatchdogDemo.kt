package sfz.redis.l08.demo

import org.redisson.Redisson
import org.redisson.config.Config
import redis.clients.jedis.RedisClient
import java.util.concurrent.TimeUnit

/** Watch Redisson's lock watchdog renew a lease, then a lock with a fixed lease run out, then fencing tokens. */
private const val LOCK = "demo:l08:lock:settle"

fun main() {
    val config = Config().apply {
        useSingleServer().setAddress("redis://localhost:6379")
        setLockWatchdogTimeout(3_000)                        // the default is 30 s; 3 s keeps the demo short
    }
    val redisson = Redisson.create(config)
    try {
        RedisClient.builder().hostAndPort("localhost", 6379).build().use { redis ->
            redis.del(LOCK)
            val lock = redisson.getLock(LOCK)
            fun pttlEvery500ms(times: Int) = (1..times).joinToString(" ") { Thread.sleep(500); redis.pttl(LOCK).toString() }

            lock.lock()                                      // no lease given: the watchdog keeps it alive
            println("lock() with the watchdog. Redis holds a ${redis.type(LOCK)}: ${redis.hgetAll(LOCK)}")
            println("  PTTL every 500 ms for 4 s: ${pttlEvery500ms(8)}")
            lock.unlock()

            lock.lock(2, TimeUnit.SECONDS)                   // a fixed 2 s lease: no watchdog
            val ttls = pttlEvery500ms(6)
            println("lock(2, SECONDS), no watchdog.")
            println("  PTTL every 500 ms for 3 s: $ttls   (-2: the key is gone)")
            println("  isHeldByCurrentThread() = ${lock.isHeldByCurrentThread}")

            val fenced = redisson.getFencedLock("demo:l08:fenced:settle")
            val first = fenced.lockAndGetToken().also { fenced.unlock() }
            val second = fenced.lockAndGetToken().also { fenced.unlock() }
            println("RFencedLock tokens for two acquisitions: $first, $second")
        }
    } finally {
        redisson.shutdown()
    }
}
