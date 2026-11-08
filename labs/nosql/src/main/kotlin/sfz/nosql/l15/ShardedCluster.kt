package sfz.nosql.l15

import java.math.BigInteger
import java.util.TreeMap

/**
 * One chunk (the MongoDB 9.0 docs also say "range"): every shard key from [min] (included) to [max]
 * (excluded) lives on [shard]. Given.
 */
class Chunk(val min: Key, val max: Key, var shard: String) {
    /** The shard key of every document in this chunk. */
    val keys: MutableList<Key> = ArrayList()

    /** Set when the chunk is bigger than the chunk size but can't be cut, because all its keys are equal. */
    var jumbo: Boolean = false

    override fun toString(): String = "[$min, $max) on $shard, ${keys.size} docs${if (jumbo) ", jumbo" else ""}"
}

/** What mongos did with a query: the shards it asked, and the stage explain() would print. Given. */
data class Route(val shards: Set<String>) {
    val stage: String get() = if (shards.size == 1) "SINGLE_SHARD" else "SHARD_MERGE"
}

/** One chunk the balancer moved. Given. */
data class Migration(val min: Key, val max: Key, val from: String, val to: String, val bytes: Long)

/**
 * A sharded payments collection: chunks of shard-key space, each on one shard, plus what mongos and
 * the balancer do with them. Every document is [docBytes] long, so a chunk's size is
 * `keys.size * docBytes`.
 *
 * Your job: [chunkFor], [insert], [route], [splitLargeChunks] and [balancerRound].
 */
class ShardedCluster(
    val shardKey: ShardKeyPattern,
    val shards: List<String>,
    val chunkSizeBytes: Long = 1_000_000,
    val docBytes: Int = 1_000,
) {
    /** Every chunk, keyed by its min. Together they cover MIN to MAX with no gaps and no overlaps. */
    val chunks = TreeMap<Key, Chunk>()

    init {
        require(shards.isNotEmpty() && shards.toSet().size == shards.size) { "distinct shard names" }
        // Sharding an empty collection, as MongoDB 8.0 and later do it. Given.
        if (shardKey.hashedPrefix) {
            // a hashed prefix: one chunk per shard, cutting the 64-bit hash space into equal slices
            val width = BigInteger.ONE.shiftLeft(64).divide(BigInteger.valueOf(shards.size.toLong()))
            val bounds = listOf(Key.MIN) +
                (1 until shards.size).map { Key.of(BigInteger.valueOf(Long.MIN_VALUE).add(width.multiply(BigInteger.valueOf(it.toLong()))).toLong()) } +
                Key.MAX
            for (i in shards.indices) chunks[bounds[i]] = Chunk(bounds[i], bounds[i + 1], shards[i])
        } else {
            // a ranged key: one chunk, MinKey to MaxKey, on the database's primary shard (the first one)
            chunks[Key.MIN] = Chunk(Key.MIN, Key.MAX, shards.first())
        }
    }

    /**
     * The chunk whose range holds [key]: the one with the greatest min that is at or below the key.
     * YOUR JOB: one `TreeMap` lookup.
     */
    fun chunkFor(key: Key): Chunk {
        TODO("chunks.floorEntry(key)")
    }

    /**
     * mongos routes one insert: compute the payment's shard key, add it to the chunk that owns it,
     * and return that chunk's shard. Nothing splits here: since MongoDB 6.0.3 inserts never split a
     * chunk. YOUR JOB.
     */
    fun insert(p: Payment): String {
        TODO("shardKey.keyOf(p), chunkFor(...), add the key, return the shard")
    }

    /**
     * mongos decides which shards must run [q]. If the shard key pattern gives a range for the
     * query (`shardKey.rangeFor(q)`), ask only the shards whose chunks overlap that range; if it
     * gives null, ask every shard. YOUR JOB.
     *
     * A chunk `[min, max)` overlaps `[lo, hi]` when `min <= hi` and `max > lo`.
     */
    fun route(q: PaymentQuery): Route {
        TODO("the set of shards owning a chunk that overlaps the range, or all shards")
    }

    /**
     * Cuts every chunk bigger than [chunkSizeBytes] into pieces of at most the chunk size. YOUR JOB.
     *
     * The one rule: a boundary can only fall between two DIFFERENT keys, because all documents with
     * the same shard key value must live in one chunk. So:
     * 1. Sort the chunk's keys and group equal neighbours into runs.
     * 2. Pack runs into pieces in order: a run joins the current piece if the piece is empty or the
     *    piece plus the run still fits in the chunk size; otherwise the run starts a new piece.
     * 3. The first piece starts at the old chunk's min, each later piece at its first key, and the
     *    last piece ends at the old chunk's max. Every piece stays on the old chunk's shard.
     * 4. A piece still bigger than the chunk size is one huge run of a single key: mark it jumbo.
     * Replace the old chunk in [chunks] with its pieces. Chunks at or under the size stay as they are.
     */
    fun splitLargeChunks() {
        TODO("cut oversized chunks between different keys; mark single-key giants jumbo")
    }

    /**
     * One balancer round on the config server primary. YOUR JOB.
     *
     * 1. Call [splitLargeChunks] (MongoDB cuts a chunk-size range off a big chunk when it moves one).
     * 2. Sort the shards by bytes, most first; when two hold the same, the one listed first in
     *    [shards] counts as fuller. Pair the first with the last, the second with the second to
     *    last, and so on. A shard takes part in at most one migration per round, so n shards allow
     *    at most n / 2 migrations.
     * 3. For each pair, migrate only if the difference is at least 3 x [chunkSizeBytes] (the
     *    docs: 384 MB for the default 128 MB). Move the donor's non-jumbo chunk with the smallest
     *    min to the receiver, by changing its shard. If the donor has no movable chunk, skip it.
     * 4. Return the migrations, in the order you made them (empty when the round moved nothing).
     *
     * Compute every shard's bytes once at the start of the round, with [bytesOn].
     */
    fun balancerRound(): List<Migration> {
        TODO("split, pair the most and least loaded shards, move one chunk per pair")
    }

    /** Runs balancer rounds until one moves nothing; returns every migration. Given. */
    fun balance(maxRounds: Int = 10_000): List<Migration> {
        val all = ArrayList<Migration>()
        repeat(maxRounds) {
            val moved = balancerRound()
            if (moved.isEmpty()) return all
            all += moved
        }
        error("the balancer never settled after $maxRounds rounds")
    }

    /** Bytes of documents in the chunks [shard] owns. Given. */
    fun bytesOn(shard: String): Long = chunks.values.filter { it.shard == shard }.sumOf { it.keys.size.toLong() } * docBytes

    /** Documents in the chunks [shard] owns. Given. */
    fun docsOn(shard: String): Int = chunks.values.filter { it.shard == shard }.sumOf { it.keys.size }

    /** The chunk that ends at MaxKey: with an increasing key, every new insert lands here. Given. */
    fun lastChunk(): Chunk = chunks.lastEntry().value
}
