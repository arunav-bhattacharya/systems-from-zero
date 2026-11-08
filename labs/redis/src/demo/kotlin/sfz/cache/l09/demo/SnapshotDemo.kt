package sfz.cache.l09.demo

import redis.clients.jedis.CommandArguments
import redis.clients.jedis.DefaultJedisClientConfig
import redis.clients.jedis.Protocol
import redis.clients.jedis.RedisClient
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicLong
import kotlin.concurrent.thread
import kotlin.random.Random

/**
 * Loads 1,000,000 payments, then snapshots them twice while a second client keeps updating payments:
 * once with SAVE (the main thread writes the file itself) and once with BGSAVE (a forked child writes it).
 * Prints how many updates got through and the slowest one, then deletes its keys.
 */
private const val PREFIX = "demo:l09:payment:"
private const val N = 1_000_000
private val FILL = """
    for i = tonumber(ARGV[1]), tonumber(ARGV[2]) do
        redis.call('SET', KEYS[1] .. i, 'settled:EUR:1250:merchant-' .. (i % 500))
    end
    return 1
""".trimIndent()
private val CLEAN = """
    for i = tonumber(ARGV[1]), tonumber(ARGV[2]) do redis.call('UNLINK', KEYS[1] .. i) end
    return 1
""".trimIndent()

/** How long [snapshot] took, how many updates the other client got done meanwhile, and the slowest one. */
private data class Probe(val millis: Long, val updates: Long, val slowestMillis: Long)

fun main() {
    // SAVE holds the server for seconds: wait up to 30 s for a reply instead of the default 2 s
    val config = DefaultJedisClientConfig.builder().socketTimeoutMillis(30_000).build()
    RedisClient.builder().hostAndPort("localhost", 6379).clientConfig(config).build().use { redis ->
        for (from in 1..N step 100_000) {                            // in slices of 100,000, so no script runs for long
            redis.eval(FILL, 1, PREFIX, "$from", "${from + 99_999}")
        }
        println("loaded %,d payments, used_memory %d MB".format(N, redis.stat("memory", "used_memory") / 1_000_000))
        if (redis.stat("persistence", "rdb_bgsave_in_progress") == 1L) {
            // a million changes trip the default save point "60 10000": the server started a BGSAVE by itself
            println("a save point already started a BGSAVE; waiting for it to finish")
            while (redis.stat("persistence", "rdb_bgsave_in_progress") == 1L) Thread.sleep(50)
        }

        val save = redis.whileUpdating { redis.executeCommand(CommandArguments(Protocol.Command.SAVE)) }
        println("SAVE:   %,6d ms; updates done meanwhile: %,5d; slowest update: %,5d ms".format(save.millis, save.updates, save.slowestMillis))

        val bg = redis.whileUpdating {
            redis.executeCommand(CommandArguments(Protocol.Command.BGSAVE))                 // forks, then answers at once
            while (redis.stat("persistence", "rdb_bgsave_in_progress") == 1L) Thread.sleep(5)
        }
        println("BGSAVE: %,6d ms; updates done meanwhile: %,5d; slowest update: %,5d ms".format(bg.millis, bg.updates, bg.slowestMillis))
        println("        fork took %.1f ms, the child copied %.1f MB of pages the parent changed meanwhile".format(
            redis.stat("stats", "latest_fork_usec") / 1000.0, redis.stat("persistence", "rdb_last_cow_size") / 1e6))

        for (from in 1..N step 100_000) redis.eval(CLEAN, 1, PREFIX, "$from", "${from + 99_999}")
    }
}

/** Runs [snapshot] while a second thread updates random payments. */
private fun RedisClient.whileUpdating(snapshot: () -> Unit): Probe {
    val running = AtomicBoolean(true)
    val updates = AtomicLong()
    val slowestNanos = AtomicLong()
    val writer = thread {
        while (running.get()) {
            val t0 = System.nanoTime()
            set(PREFIX + Random.nextInt(1, N + 1), "refunded")
            slowestNanos.accumulateAndGet(System.nanoTime() - t0) { a, b -> maxOf(a, b) }
            updates.incrementAndGet()
        }
    }
    Thread.sleep(200)                                                // let the writer get going first
    val before = updates.get()
    val t0 = System.nanoTime()
    snapshot()
    val millis = (System.nanoTime() - t0) / 1_000_000
    val during = updates.get() - before
    running.set(false)
    writer.join()
    return Probe(millis, during, slowestNanos.get() / 1_000_000)
}

private fun RedisClient.stat(section: String, field: String): Long =
    info(section).lineSequence().map { it.trim() }.first { it.startsWith("$field:") }.substringAfter(':').toLong()
