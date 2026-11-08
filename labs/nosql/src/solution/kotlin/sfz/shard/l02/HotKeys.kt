package sfz.shard.l02

/**
 * Finds partition keys that get more requests in one second than one partition can serve.
 *
 * A DynamoDB partition serves at most 1,000 write units a second, and every item with the
 * same partition key lives in the same partition. So a key that takes 4,000 writes in one
 * second is throttled however many partitions the table has.
 *
 * Count requests per key per whole second (`atMillis / 1000`). A key is hot when, in any one
 * second, it got MORE than [limitPerSecond] requests.
 *
 * Your job: [record] and [hotKeys].
 */
class HotKeyDetector(val limitPerSecond: Int) {
    /** second -> (key -> requests in that second) */
    private val counts = HashMap<Long, HashMap<String, Int>>()

    /** Counts one request for [key] at [atMillis] (epoch milliseconds). */
    fun record(key: String, atMillis: Long) {
        val second = Math.floorDiv(atMillis, 1000L)
        counts.getOrPut(second) { HashMap() }.merge(key, 1, Int::plus)
    }

    /**
     * Every key that went over the limit in some second, mapped to its busiest second's count.
     * Keys that never went over are not in the map.
     */
    fun hotKeys(): Map<String, Int> {
        val busiest = HashMap<String, Int>()
        for (perKey in counts.values) {
            for ((key, n) in perKey) busiest.merge(key, n, ::maxOf)
        }
        return busiest.filterValues { it > limitPerSecond }
    }
}

/**
 * Write sharding: spread one hot partition key over several keys, `MERCH#M-0042#0` to `MERCH#M-0042#9`.
 *
 * The shard is CALCULATED from the payment id, not random, so whoever knows a payment id can
 * compute its key again. A reader that wants all of a merchant's payments must query every shard.
 */
object WriteSharding {
    /** The unsharded key, `MERCH#<merchantId>`. Given. */
    fun merchantKey(merchantId: String): String = "MERCH#$merchantId"

    /**
     * The key a payment is written under: `MERCH#<merchantId>#<shard>`, where shard is
     * `position(paymentId) mod shards` (use `Math.floorMod`: positions can be negative), so it is
     * between 0 and shards - 1.
     */
    fun shardKey(merchantId: String, paymentId: String, shards: Int): String {
        // the same payment id always gives the same shard; different ids spread evenly
        val shard = Math.floorMod(HashRing.position(paymentId), shards.toLong())
        return "${merchantKey(merchantId)}#$shard"
    }

    /** Every key a reader must query, in shard order: `MERCH#<merchantId>#0` ... `#<shards - 1>`. Given. */
    fun allShardKeys(merchantId: String, shards: Int): List<String> =
        (0 until shards).map { "${merchantKey(merchantId)}#$it" }
}
