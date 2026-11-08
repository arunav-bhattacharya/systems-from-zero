package sfz.shard.l08

import java.nio.ByteBuffer
import java.security.MessageDigest

/** Per-partition ceilings from the AWS docs: 3,000 read units and 1,000 write units a second, about 10 GB. */
const val PARTITION_MAX_RCU = 3_000
const val PARTITION_MAX_WCU = 1_000
const val PARTITION_MAX_BYTES = 10L * 1024 * 1024 * 1024

/** DynamoDB keeps up to five minutes (300 seconds) of a partition's unused capacity as burst capacity. */
const val BURST_SECONDS = 300

/** A 64-bit hash of a partition key value (the first 8 bytes of its MD5). Given. */
fun hash64(value: String): Long = ByteBuffer.wrap(MessageDigest.getInstance("MD5").digest(value.toByteArray())).long

/**
 * The partition a partition key lands in when the hash space is cut into [partitions] equal slices,
 * numbered 0 to partitions - 1 from the bottom. When every partition splits in two, slice i becomes
 * slices 2i and 2i + 1, as DynamoDB splits a partition's key range into two children. Given.
 */
fun partitionOf(pk: String, partitions: Int): Int = Math.unsignedMultiplyHigh(hash64(pk), partitions.toLong()).toInt()

/** What one second of writes did, per partition and in total. Given. */
data class SecondResult(val admittedByPartition: List<Int>, val throttledByPartition: List<Int>) {
    val admitted: Int get() = admittedByPartition.sum()
    val throttled: Int get() = throttledByPartition.sum()
}

/** How many partitions a table needs. Your job: [forNewTable] and [afterSplits]. */
object Partitions {
    /**
     * Partitions for a NEW provisioned table, from the per-partition ceilings: enough for the reads
     * (3,000 RCU each), enough for the writes (1,000 WCU each), enough for the data (10 GB each),
     * and never fewer than one. Round each up. YOUR JOB.
     *
     * Example from the 2022 DynamoDB paper: 3,200 WCU needs 4 partitions.
     */
    fun forNewTable(rcu: Int, wcu: Int, bytes: Long = 0): Int {
        TODO("the largest of ceil(rcu / 3,000), ceil(wcu / 1,000), ceil(bytes / 10 GB) and 1")
    }

    /**
     * Partitions after a change that needs [needed] of them, starting from [current]. A partition
     * only ever splits in two, and partitions never merge: double [current] until it reaches
     * [needed], and never go below [current]. YOUR JOB.
     *
     * Example from the paper: 4 partitions, and the table is raised to 6,000 WCU: 8 partitions.
     */
    fun afterSplits(current: Int, needed: Int): Int {
        TODO("double current until it is at least needed")
    }
}

/**
 * A provisioned table, writes only. The table has [wcu] write units a second in total; each
 * partition is allocated an equal share, and DynamoDB enforces that share at the partition.
 *
 * [adaptive] is on in every DynamoDB table today. Turn it off to see the original 2012 design, which
 * the paper describes: fixed shares plus burst capacity, nothing else.
 *
 * Your job: [serve].
 */
class ProvisionedTable(wcu: Int, partitions: Int = Partitions.forNewTable(0, wcu), val adaptive: Boolean = true) {
    var wcu: Int = wcu
        private set
    var partitions: Int = partitions
        private set
    var bytes: Long = 0
        private set

    /** Each partition's saved burst units. A new table has none. */
    var burst: MutableList<Long> = MutableList(partitions) { 0L }
        private set

    /** One partition's share of the table's write units. Given. */
    fun allocation(): Int = wcu / partitions

    /** UpdateTable: a new provisioned WCU. More than the partitions can take splits them. Given. */
    fun updateProvisioned(newWcu: Int) {
        wcu = newWcu
        resize(Partitions.afterSplits(partitions, Partitions.forNewTable(0, newWcu, bytes)))
    }

    /** The table holds [more] bytes. A partition that fills up splits, and the share is divided. Given. */
    fun grow(more: Long) {
        bytes += more
        resize(Partitions.afterSplits(partitions, Partitions.forNewTable(0, wcu, bytes)))
    }

    private fun resize(to: Int) {
        if (to == partitions) return
        val factor = to / partitions // splits double, so this is a power of two
        burst = MutableList(to) { burst[it / factor] / factor } // children share the parent's saved units
        partitions = to
    }

    /**
     * One second of writes: partition key value -> write units it asks for. YOUR JOB.
     *
     * 1. Add up each partition's demand (use [partitionOf]).
     * 2. Every partition admits up to its [allocation], never above [PARTITION_MAX_WCU].
     * 3. If [adaptive]: the table's unused write units (wcu minus everything admitted so far) go to
     *    partitions that still want more, lowest partition number first, each up to the partition max.
     * 4. Burst: a partition still short takes from its own [burst] units, up to the partition max.
     * 5. Each partition then saves what it left unused of its allocation (allocation minus admitted,
     *    if positive) into its [burst], up to [BURST_SECONDS] times its allocation.
     * 6. Whatever was asked for and not admitted is throttled.
     */
    fun serve(writes: Map<String, Int>): SecondResult {
        TODO("allocation, then adaptive capacity, then burst; save unused units; the rest is throttled")
    }
}

/**
 * An on-demand table, writes only. There is nothing to provision: DynamoDB admits up to double the
 * previous peak, and splits partitions ahead of that. Every partition still has the 1,000 WCU ceiling.
 *
 * A new table can take 4,000 writes a second, as the AWS docs say, so it starts as if its previous
 * peak were 2,000, with 4 partitions. The model counts a new peak as soon as one call reaches it.
 * AWS asks you to spread growth beyond double over at least 30 minutes, so read each call as a
 * sustained level of traffic, not one literal second.
 *
 * Your job: [serve].
 */
class OnDemandTable {
    var previousPeak: Int = 2_000
        private set
    var partitions: Int = 4
        private set

    /** The most the table admits in one second: double the previous peak. Given. */
    fun ceiling(): Int = 2 * previousPeak

    /**
     * One second of writes. YOUR JOB.
     *
     * 1. Add up each partition's demand, and admit each partition up to [PARTITION_MAX_WCU].
     * 2. If the total admitted is above [ceiling], take the excess back, from the highest partition
     *    number down, so the table admits exactly [ceiling].
     * 3. The rest is throttled.
     * 4. Then remember the new peak (the larger of [previousPeak] and the total admitted), and split
     *    ahead: [Partitions.afterSplits] to enough partitions for the new [ceiling] at 1,000 each.
     */
    fun serve(writes: Map<String, Int>): SecondResult {
        TODO("partition max, then the table ceiling; record the peak and split ahead")
    }
}
