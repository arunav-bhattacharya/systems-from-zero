package sfz.cache.l07.demo

import redis.clients.jedis.RedisClient
import redis.clients.jedis.params.SetParams
import java.util.concurrent.CompletableFuture
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** The stale-set race four times, always in the same order: reader A misses, the writer commits, A fills, B reads. */
private data class Row(val name: String, val version: Long)

private val table = ConcurrentHashMap<String, Row>()                       // the "database"
private val redis = RedisClient.builder().hostAndPort("localhost", 6379).build()
private const val KEY = "demo:l07:merchant:{m-17}"
private const val LEASE = "demo:l07:lease:{m-17}"

/** What a pod does on a read, and what the writer does after its commit. */
private interface Cache {
    fun get(who: String, beforeFill: () -> Unit): String
    fun afterWrite(newVersion: Long)
}

private fun say(who: String, what: String) = println("  $who  $what")

// 1. lesson 6's cache-aside: GET, on a miss SELECT and SET; after a write, DEL
private object Naive : Cache {
    override fun get(who: String, beforeFill: () -> Unit): String {
        redis.get(KEY)?.let { return it }
        val row = table.getValue("m-17")
        say(who, "GET: miss. SELECT: ${row.name} (v${row.version})")
        beforeFill()
        redis.set(KEY, row.name, SetParams.setParams().ex(3_600))
        say(who, "SET ${row.name} EX 3600: OK")
        return row.name
    }

    override fun afterWrite(newVersion: Long) = say("W", "DEL: ${redis.del(KEY)} keys deleted")
}

// 2. a lease: only the reader whose token is still in the lease key may fill
private val FILL_WITH_LEASE = """
    if redis.call('GET', KEYS[2]) ~= ARGV[1] then return 0 end
    redis.call('SET', KEYS[1], ARGV[2], 'EX', 3600)
    redis.call('DEL', KEYS[2])
    return 1
""".trimIndent()

private object Leased : Cache {
    override fun get(who: String, beforeFill: () -> Unit): String {
        redis.get(KEY)?.let { return it }
        val token = "t-$who"                                                // readable; real code uses a UUID
        val took = redis.set(LEASE, token, SetParams.setParams().nx().px(10_000))
        val row = table.getValue("m-17")
        say(who, "GET: miss. SET lease $token NX PX 10000: $took. SELECT: ${row.name} (v${row.version})")
        beforeFill()
        val ok = redis.eval(FILL_WITH_LEASE, listOf(KEY, LEASE), listOf(token, row.name))
        say(who, "fill with lease $token: " + if (ok == 1L) "stored" else "refused, the lease is gone")
        return row.name
    }

    override fun afterWrite(newVersion: Long) = say("W", "DEL value and lease: ${redis.del(KEY, LEASE)} keys deleted")
}

// 3 and 4. a version check: the entry is a hash {ver, name}; a fill older than what the cache has seen is refused
private val FILL_IF_NEWER = """
    local seen = tonumber(redis.call('HGET', KEYS[1], 'ver'))
    if seen and seen > tonumber(ARGV[1]) then return 0 end
    redis.call('HSET', KEYS[1], 'ver', ARGV[1], 'name', ARGV[2])
    redis.call('EXPIRE', KEYS[1], 3600)
    return 1
""".trimIndent()
private val TOMBSTONE = """
    local seen = tonumber(redis.call('HGET', KEYS[1], 'ver'))
    if seen and seen > tonumber(ARGV[1]) then return 0 end
    redis.call('DEL', KEYS[1])
    redis.call('HSET', KEYS[1], 'ver', ARGV[1])
    redis.call('PEXPIRE', KEYS[1], ARGV[2])
    return 1
""".trimIndent()

private class Versioned(val tombstone: Boolean) : Cache {
    override fun get(who: String, beforeFill: () -> Unit): String {
        redis.hget(KEY, "name")?.let { return it }                         // a tombstone has no name: a miss
        val row = table.getValue("m-17")
        say(who, "HGET: miss. SELECT: ${row.name} (v${row.version})")
        beforeFill()
        val ok = redis.eval(FILL_IF_NEWER, listOf(KEY), listOf(row.version.toString(), row.name))
        say(who, "fill v${row.version} if newer: " +
            if (ok == 1L) "stored" else "refused, the cache has seen v${redis.hget(KEY, "ver")}")
        return row.name
    }

    override fun afterWrite(newVersion: Long) {
        if (tombstone) {
            redis.eval(TOMBSTONE, listOf(KEY), listOf(newVersion.toString(), "10000"))
            say("W", "tombstone: ver $newVersion, no name, for 10 s")
        } else {
            say("W", "DEL: ${redis.del(KEY)} keys deleted")
        }
    }
}

private fun race(title: String, cache: Cache) {
    redis.del(KEY, LEASE)
    table["m-17"] = Row("Fietsen Utrecht", 1)
    println(title)
    val atFill = CountDownLatch(1)
    val writerDone = CountDownLatch(1)

    // reader A misses, reads v1, and stops just before its fill until the writer is done
    val readerA = CompletableFuture.supplyAsync {
        cache.get("A") { atFill.countDown(); check(writerDone.await(5, TimeUnit.SECONDS)) }
    }
    check(atFill.await(5, TimeUnit.SECONDS))
    table["m-17"] = Row("Velo Utrecht", 2)
    say("W", "UPDATE: Velo Utrecht (v2). COMMIT")
    cache.afterWrite(2)
    writerDone.countDown()
    readerA.get(5, TimeUnit.SECONDS)

    val b = cache.get("B") {}
    val db = table.getValue("m-17").name
    println("  B  reads: $b" + if (b == db) "  (fresh)"
        else "  (STALE: the database says $db, and the entry lives ${redis.ttl(KEY)} s more)")
    println()
}

fun main() {
    race("1. cache-aside, DEL after the commit", Naive)
    race("2. a lease that the DEL revokes", Leased)
    race("3. a version check, DEL after the commit", Versioned(tombstone = false))
    race("4. a version check, a tombstone after the commit", Versioned(tombstone = true))
    println("cleaning up: ${redis.del(KEY, LEASE)} keys deleted")
    redis.close()
}
