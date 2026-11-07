package sfz.redis.l11.demo

import redis.clients.jedis.CommandArguments
import redis.clients.jedis.DefaultJedisClientConfig
import redis.clients.jedis.Protocol
import redis.clients.jedis.RedisClient
import redis.clients.jedis.params.ScanParams
import redis.clients.jedis.resps.Slowlog
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicLong
import kotlin.concurrent.thread

/**
 * Loads 1,000,000 payments, then looks for refund keys twice while a second client sends GETs back to back:
 * once with KEYS (one command walks the whole keyspace) and once with SCAN (a thousand small steps).
 * Prints the slowest GET during each, the slow log's top entry, then deletes its keys.
 */
private const val PREFIX = "demo:l11:payment:"
private const val N = 1_000_000
private const val FILL = "for i = tonumber(ARGV[1]), tonumber(ARGV[2]) do redis.call('SET', KEYS[1] .. i, 'settled') end return 1"
private const val CLEAN = "for i = tonumber(ARGV[1]), tonumber(ARGV[2]) do redis.call('UNLINK', KEYS[1] .. i) end return 1"

fun main() {
    // a busy server can take more than the default 2 s to answer: wait up to 30 s
    val config = DefaultJedisClientConfig.builder().socketTimeoutMillis(30_000).build()
    RedisClient.builder().hostAndPort("localhost", 6379).clientConfig(config).build().use { redis ->
        for (from in 1..N step 100_000) redis.eval(FILL, 1, PREFIX, "$from", "${from + 99_999}")
        redis.slowlogReset()
        println("loaded %,d payments; %,d keys in the database".format(N, redis.dbSize()))

        val (keysMs, keysWorst) = redis.whileReading { redis.keys("demo:l11:refund:*") }
        println("KEYS: 1 command, %,5d ms in all; the slowest GET meanwhile waited %,4d ms".format(keysMs, keysWorst))

        var calls = 0
        val (scanMs, scanWorst) = redis.whileReading {
            val match = ScanParams().match("demo:l11:refund:*").count(1_000)
            var cursor = ScanParams.SCAN_POINTER_START
            do {
                cursor = redis.scan(cursor, match).cursor                // one small slice of the table per call
                calls++
            } while (cursor != ScanParams.SCAN_POINTER_START)
        }
        println("SCAN: %,d commands, %,5d ms in all; the slowest GET meanwhile waited %,4d ms".format(calls, scanMs, scanWorst))

        @Suppress("UNCHECKED_CAST")
        val log = Slowlog.from(redis.executeCommand(CommandArguments(Protocol.Command.SLOWLOG).add("GET").add(128)) as List<Any>)
        val top = log.maxBy { it.executionTime }
        println("entries in the slow log: ${log.size}; the slowest: ${top.args}, %,d microseconds".format(top.executionTime))

        for (from in 1..N step 100_000) redis.eval(CLEAN, 1, PREFIX, "$from", "${from + 99_999}")
    }
}

/** Runs [task] while a second thread sends GETs back to back; returns the task's ms and the slowest GET's ms. */
private fun RedisClient.whileReading(task: () -> Unit): Pair<Long, Long> {
    val running = AtomicBoolean(true)
    val slowestNanos = AtomicLong()
    val reader = thread {
        while (running.get()) {
            val t0 = System.nanoTime()
            get("${PREFIX}42")
            slowestNanos.accumulateAndGet(System.nanoTime() - t0) { a, b -> maxOf(a, b) }
        }
    }
    Thread.sleep(200)
    slowestNanos.set(0)                                              // only count what happens during the task
    val t0 = System.nanoTime()
    task()
    val millis = (System.nanoTime() - t0) / 1_000_000
    running.set(false)
    reader.join()
    return millis to slowestNanos.get() / 1_000_000
}
