package sfz.redis.l06.demo

import io.lettuce.core.ExperimentalLettuceCoroutinesApi
import io.lettuce.core.api.coroutines
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import redis.clients.jedis.RedisClient

/** 5,000 SETs three ways: one round trip each, one Jedis pipeline, and Lettuce coroutines on one connection. */
private const val N = 5_000

private fun report(label: String, t0: Long) {
    val ms = (System.nanoTime() - t0) / 1e6
    println("%-30s %8.1f ms  %,10.0f SETs/s".format(label, ms, N / (ms / 1000)))
}

@OptIn(ExperimentalLettuceCoroutinesApi::class)
fun main() {
    RedisClient.builder().hostAndPort("localhost", 6379).build().use { jedis ->
        repeat(2_000) { jedis.set("warm:$it", "1") }                         // warm up the JIT and the pool

        var t0 = System.nanoTime()
        repeat(N) { jedis.set("acct:$it", "100") }                            // send, wait, send, wait...
        report("one by one", t0)

        t0 = System.nanoTime()
        jedis.pipelined().use { pipe ->
            repeat(N) { pipe.set("acct:$it", "100") }                         // buffered, nothing waits
            pipe.sync()                                                       // flush, then read all replies
        }
        report("one Jedis pipeline", t0)
    }

    val lettuce = io.lettuce.core.RedisClient.create("redis://localhost:6379")
    try {
        lettuce.connect().use { conn ->
            val redis = conn.coroutines()
            runBlocking {
                redis.set("warm", "1")
                val t0 = System.nanoTime()
                coroutineScope {
                    repeat(N) { launch { redis.set("acct:$it", "100") } }     // 5,000 coroutines, one socket
                }
                report("Lettuce coroutines, one conn", t0)
            }
        }
    } finally {
        lettuce.shutdown()
    }
}
