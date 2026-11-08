package sfz.cache.l06.demo

import redis.clients.jedis.RedisClient
import redis.clients.jedis.params.SetParams
import redis.clients.jedis.util.CompareCondition
import java.util.UUID
import java.util.concurrent.CompletableFuture
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicInteger

/** 100 requests miss the same cold key at once. How many reach the 200 ms database? */
private const val KEY = "merchant:m-17"
private val dbCalls = AtomicInteger()

private fun loadFromDatabase(): String {
    dbCalls.incrementAndGet()
    Thread.sleep(200)
    return "m-17|Fietsen Utrecht|NL|5940"
}

/** One service instance: its own Redis client and its own in-process single-flight map. */
private class Pod {
    val redis: RedisClient = RedisClient.builder().hostAndPort("localhost", 6379).build()
    private val flights = ConcurrentHashMap<String, CompletableFuture<String>>()

    fun plain(): String {                                    // cache-aside, no protection
        redis.get(KEY)?.let { return it }
        val v = loadFromDatabase()
        redis.set(KEY, v, SetParams.setParams().ex(3_600))
        return v
    }

    fun singleFlight(): String {                             // one load per key per pod
        redis.get(KEY)?.let { return it }
        val mine = CompletableFuture<String>()
        flights.putIfAbsent(KEY, mine)?.let { return it.join() }   // a follower waits for the leader
        try {
            val row = redis.get(KEY) ?: loadFromDatabase().also {  // filled while we became leader?
                redis.set(KEY, it, SetParams.setParams().ex(3_600))
            }
            mine.complete(row)
            return row
        } finally {
            flights.remove(KEY, mine)
        }
    }

    fun redisLock(): String {                                // one load per key across all pods
        redis.get(KEY)?.let { return it }
        val token = UUID.randomUUID().toString()
        if (redis.set("lock:$KEY", token, SetParams.setParams().nx().px(2_000)) != null) {
            try {
                return loadFromDatabase().also { redis.set(KEY, it, SetParams.setParams().ex(3_600)) }
            } finally {
                // Redis 8.4+: delete the lock only if it is still ours (it may have expired and gone to another pod)
                redis.delex("lock:$KEY", CompareCondition.valueEq(token))
            }
        }
        repeat(100) {                                        // someone else is loading: wait for the cache
            Thread.sleep(10)
            redis.get(KEY)?.let { return it }
        }
        return loadFromDatabase()                            // waited a second: load it ourselves
    }
}

private fun run(label: String, pods: Int, strategy: (Pod) -> String) {
    val fleet = List(pods) { Pod() }
    fleet[0].redis.del(KEY, "lock:$KEY")
    dbCalls.set(0)
    val threads = Executors.newFixedThreadPool(100)
    val start = CountDownLatch(1)
    val requests = (0 until 100).map { i ->
        CompletableFuture.supplyAsync({ start.await(); strategy(fleet[i % pods]) }, threads)
    }
    val t0 = System.nanoTime()
    start.countDown()
    requests.forEach { it.join() }
    println("%-40s database calls: %3d   %4d ms".format(label, dbCalls.get(), (System.nanoTime() - t0) / 1_000_000))
    threads.shutdown()
    fleet.forEach { it.redis.close() }
}

fun main() {
    run("no protection, 1 pod", 1, Pod::plain)
    run("single-flight, 1 pod", 1, Pod::singleFlight)
    run("single-flight, 4 pods", 4, Pod::singleFlight)
    run("Redis lock (SET NX PX), 4 pods", 4, Pod::redisLock)
}
