package sfz.shard.l01

import java.nio.ByteBuffer
import java.security.MessageDigest

/**
 * The first of the two maps every sharded store keeps: from a partition key to a shard.
 * Shards are numbered 0 until [shardCount]. (The second map, from a shard to a node, is lesson 3's.)
 */
interface Sharding {
    val shardCount: Int

    /** The one shard that holds [key]. */
    fun shardOf(key: String): Int

    /** Every shard that may hold a key k with `fromInclusive <= k < toExclusive`, in string order. */
    fun shardsForRange(fromInclusive: String, toExclusive: String): Set<Int>
}

/**
 * Key-range sharding, the way Bigtable, HBase, MongoDB's ranged sharding and CockroachDB do it.
 *
 * [boundaries] are sorted split points. Shard 0 holds every key below `boundaries[0]`, shard i holds
 * `boundaries[i - 1] <= key < boundaries[i]`, and the last shard holds every key at or above the last
 * boundary. So a key that equals a boundary belongs to the shard on its right.
 */
class RangeSharding(val boundaries: List<String>) : Sharding {
    init {
        require(boundaries.zipWithNext().all { (a, b) -> a < b }) { "boundaries must be strictly increasing" }
    }

    override val shardCount: Int get() = boundaries.size + 1

    override fun shardOf(key: String): Int {
        TODO("the number of boundaries <= key; find it with a binary search, not a loop")
    }

    override fun shardsForRange(fromInclusive: String, toExclusive: String): Set<Int> {
        TODO("the shards from the one holding fromInclusive to the one holding the largest key below toExclusive")
    }

    companion object {
        /**
         * Boundaries that cut a sample of keys into [shards] runs of nearly equal size, so the shards
         * follow the data instead of the alphabet. Sort the distinct keys, then take the key at
         * position `i * size / shards` for i = 1 until [shards] as the start of shard i.
         */
        fun fromSample(sample: Collection<String>, shards: Int): RangeSharding {
            TODO("sort the distinct keys and take the key at i * size / shards for i = 1 until shards")
        }
    }
}

/**
 * Hash sharding, the way Cassandra and DynamoDB spread partition keys: hash the key, then pick a shard
 * from the hash. Here the pick is `hash mod N`, the simplest rule (lesson 3 shows what it costs when N
 * changes).
 */
class HashSharding(override val shardCount: Int) : Sharding {
    init {
        require(shardCount >= 1) { "need at least one shard" }
    }

    /** The hash of [key] mod [shardCount]. The hash is signed: use `Math.floorMod`, never `%`. */
    override fun shardOf(key: String): Int = TODO("floorMod(stableHash(key), shardCount)")

    /** Hashing scatters neighbouring keys on purpose, so any range may touch every shard. Given. */
    override fun shardsForRange(fromInclusive: String, toExclusive: String): Set<Int> =
        if (fromInclusive >= toExclusive) emptySet() else (0 until shardCount).toSet()
}

/**
 * A hash every process computes the same way: the first 8 bytes of MD5, as a signed Long. Given.
 * (Java's `String.hashCode()` is stable too, but it maps "pay-1" and "pay-2" to neighbouring numbers,
 * and `Object.hashCode()` changes from one JVM to the next.)
 */
fun stableHash(key: String): Long =
    ByteBuffer.wrap(MessageDigest.getInstance("MD5").digest(key.toByteArray())).long

/** How many of [keys] land on each shard. Given. */
fun load(sharding: Sharding, keys: Iterable<String>): IntArray {
    val counts = IntArray(sharding.shardCount)
    for (k in keys) counts[sharding.shardOf(k)]++
    return counts
}

/** The busiest shard's load divided by the average: 1.0 is perfectly even, N means one shard takes it all. Given. */
fun skew(load: IntArray): Double {
    val mean = load.sum().toDouble() / load.size
    return if (mean == 0.0) 1.0 else load.max() / mean
}
