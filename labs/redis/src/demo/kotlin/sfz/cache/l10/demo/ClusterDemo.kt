package sfz.cache.l10.demo

import io.lettuce.core.ExperimentalLettuceCoroutinesApi
import io.lettuce.core.RedisCommandExecutionException
import io.lettuce.core.cluster.RedisClusterClient
import io.lettuce.core.cluster.SlotHash
import io.lettuce.core.cluster.api.coroutines
import kotlinx.coroutines.runBlocking
import redis.clients.jedis.RedisClient

/**
 * Talks to the three-node cluster from env/redis-cluster.yml: first with a plain client that knows only node 1,
 * then with Lettuce's cluster client and its coroutines API, which loads the slot table and routes every key.
 * Start the cluster first: docker compose -f env/redis-cluster.yml up -d --wait
 */
@OptIn(ExperimentalLettuceCoroutinesApi::class)
fun main() {
    // a plain client: one node, no slot table (Jedis here, because its MOVED exception carries the slot and node)
    RedisClient.builder().hostAndPort("127.0.0.1", 7001).build().use { node1 ->
        runCatching { node1.get("payment:42") }
            .onFailure { println("plain client on 7001, GET payment:42 -> ${it.message}") }
    }

    // Lettuce's cluster client: one seed node, then the whole slot table and a connection per node
    val client = RedisClusterClient.create("redis://127.0.0.1:7001")
    try {
        client.connect().use { conn ->
            val redis = conn.coroutines()
            runBlocking {
                for (key in listOf("payment:42", "payment:43", "{merchant:7}:payments", "{merchant:7}:refunds")) {
                    redis.set(key, "approved")
                    val slot = SlotHash.getSlot(key)
                    val owner = client.partitions.getPartitionBySlot(slot).uri
                    println("%-22s slot %5d  on %s:%d".format(key, slot, owner.host, owner.port))
                }
                // Lettuce splits a cross-slot MSET into one MSET per slot and sends them to their nodes:
                // it succeeds, but the two halves are separate commands, not one atomic step
                println("MSET payment:42 payment:43 -> " + redis.mset(mapOf("payment:42" to "settled", "payment:43" to "settled")))
                // the same command sent as raw MSET to one node is refused by the server
                val raw = runCatching {
                    conn.getConnection("127.0.0.1", 7001).sync().mset(mapOf("payment:42" to "x", "payment:43" to "y"))
                }
                println("raw MSET on one node    -> " + (raw.exceptionOrNull() as? RedisCommandExecutionException)?.message)
                println("MSET with one hash tag  -> " + redis.mset(mapOf("{merchant:7}:payments" to "10", "{merchant:7}:refunds" to "2")))
            }
        }
    } finally {
        client.shutdown()
    }
}
