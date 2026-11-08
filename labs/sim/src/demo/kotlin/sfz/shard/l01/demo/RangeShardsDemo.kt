package sfz.shard.l01.demo

import java.util.Random

/** A payment on virtual time: milliseconds since midnight, no clock involved. */
data class Pay(val id: String, val merchant: String, val atMillis: Long)

fun payments(count: Int, startMillis: Long, everyMillis: Long, firstId: Int, seed: Long): List<Pay> {
    val rnd = Random(seed)
    return (0 until count).map { i -> Pay("pay-${firstId + i}", "M-%04d".format(rnd.nextInt(500)), startMillis + i * everyMillis) }
}

fun hours(h: Int, m: Int = 0) = (h * 60L + m) * 60_000L

/** Key-range shards: sorted split points; a key belongs to the shard after the last boundary <= key. */
class Ranges(val boundaries: List<String>) {
    fun shardOf(key: String) = boundaries.count { it <= key }

    companion object {
        // cut a sample into equal runs, so the shards follow the data
        fun fromSample(keys: List<String>, n: Int) = keys.sorted().let { s -> Ranges((1 until n).map { s[it * s.size / n] }) }
    }
}

/** Eight range shards cut from the morning's keys. Then the afternoon arrives. Where do the inserts go? */
fun main() {
    val morning = payments(20_000, startMillis = hours(8), everyMillis = 1_000, firstId = 0, seed = 7)
    val afternoon = payments(10_000, startMillis = hours(14), everyMillis = 5, firstId = 20_000, seed = 8)
    val day = morning + afternoon

    val byTime = { p: Pay -> "%013d#%s".format(p.atMillis, p.id) }
    val byMerchant = { p: Pay -> "%s#%013d#%s".format(p.merchant, p.atMillis, p.id) }

    for ((name, key) in listOf("time first" to byTime, "merchant first" to byMerchant)) {
        val shards = Ranges.fromSample(morning.map(key), 8)
        val inserts = IntArray(8).also { c -> afternoon.forEach { c[shards.shardOf(key(it))]++ } }
        // which shards would a query have to ask? the ones that hold at least one matching payment
        fun shardsHolding(match: (Pay) -> Boolean) = day.filter(match).map { shards.shardOf(key(it)) }.toSortedSet()
        println("key = $name, for example ${key(afternoon[0])}")
        println("  afternoon inserts per shard: ${inserts.toList()}")
        println("  shards holding 14:00 to 14:05:  ${shardsHolding { it.atMillis in hours(14) until hours(14, 5) }}")
        println("  shards holding M-0042's day:    ${shardsHolding { it.merchant == "M-0042" }}")
    }
}
