package sfz.shard.l01.demo

import java.nio.ByteBuffer
import java.security.MessageDigest
import java.util.Random

/** The first 8 bytes of MD5: the same number in every process, and neighbouring keys land far apart. */
fun md5(key: String): Long = ByteBuffer.wrap(MessageDigest.getInstance("MD5").digest(key.toByteArray())).long

/** Hash sharding: shard = hash mod 8. Same payments as the range demo, plus a Black Friday afternoon. */
fun main() {
    val shardOf = { key: String -> Math.floorMod(md5(key), 8L).toInt() }
    val afternoon = payments(10_000, startMillis = hours(14), everyMillis = 5, firstId = 20_000, seed = 8)
    // Black Friday: the same afternoon, but M-0042 takes every fifth payment
    val blackFriday = afternoon.mapIndexed { i, p -> if (i % 5 == 0) p.copy(merchant = "M-0042") else p }

    val byTime = { p: Pay -> "%013d#%s".format(p.atMillis, p.id) }
    val byMerchant = { p: Pay -> p.merchant } // the partition key alone; rows sort by time inside it

    for ((name, key) in listOf("time + id" to byTime, "merchant" to byMerchant)) {
        fun inserts(day: List<Pay>) = IntArray(8).also { c -> day.forEach { c[shardOf(key(it))]++ } }.toList()
        fun shardsHolding(match: (Pay) -> Boolean) = blackFriday.filter(match).map { shardOf(key(it)) }.toSortedSet()
        println("partition key = $name")
        println("  normal afternoon, inserts per shard: ${inserts(afternoon)}")
        println("  Black Friday,     inserts per shard: ${inserts(blackFriday)}")
        println("  shards holding 14:00 to 14:05:  ${shardsHolding { it.atMillis in hours(14) until hours(14, 5) }}")
        println("  shards holding M-0042's day:    ${shardsHolding { it.merchant == "M-0042" }}")
    }
    println("String.hashCode() of pay-1, pay-2, pay-3: ${listOf("pay-1", "pay-2", "pay-3").map { it.hashCode() }}")
}
