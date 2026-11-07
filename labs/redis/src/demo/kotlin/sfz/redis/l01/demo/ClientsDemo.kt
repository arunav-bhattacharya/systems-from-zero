package sfz.redis.l01.demo

import io.lettuce.core.ExperimentalLettuceCoroutinesApi
import io.lettuce.core.api.coroutines
import kotlinx.coroutines.runBlocking
import redis.clients.jedis.RedisClient

/** The same GET through Jedis (blocking) and Lettuce (coroutines), then how each one connected. */
@OptIn(ExperimentalLettuceCoroutinesApi::class)
fun main() {
    // Jedis 8: one RedisClient, a pool of connections behind it, blocking calls
    RedisClient.builder().hostAndPort("localhost", 6379).build().use { jedis ->
        jedis.set("payment:42", "approved")
        println("Jedis   GET payment:42 -> " + jedis.get("payment:42"))

        // Lettuce 7: one connection shared by every caller; coroutines suspend instead of blocking
        val lettuce = io.lettuce.core.RedisClient.create("redis://localhost:6379")
        try {
            lettuce.connect().use { conn ->
                val redis = conn.coroutines()
                val list = runBlocking {
                    println("Lettuce GET payment:42 -> " + redis.get("payment:42"))   // suspends
                    redis.clientList().orEmpty()        // ask the server how each library connected
                }
                val fields = Regex("""(resp=\d+) (lib-name=\S+) (lib-ver=\S+)""")
                list.lineSequence()
                    .mapNotNull { fields.find(it) }
                    .filter { it.groupValues[2] != "lib-name=" }
                    .forEach { println(it.groupValues.drop(1).joinToString(" ")) }
            }
        } finally {
            lettuce.shutdown()
        }
    }
}
