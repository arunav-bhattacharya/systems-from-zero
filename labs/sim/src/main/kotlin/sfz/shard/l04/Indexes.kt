package sfz.shard.l04

import java.nio.ByteBuffer
import java.security.MessageDigest
import java.util.PriorityQueue

/** A card payment. The table is sharded by [id]; the fraud check wants to find payments by [card]. */
data class Payment(val id: String, val merchant: String, val card: String, val amountCents: Long)

/** What a query found, and how many shards it had to ask to find it. */
data class QueryResult(val ids: Set<String>, val shardsContacted: Int)

/** Virtual time in milliseconds. Nothing happens between two calls to [advance], so tests are exact. Given. */
class VirtualClock {
    var now = 0L
        private set

    fun advance(millis: Long) {
        require(millis >= 0) { "time only goes forward" }
        now += millis
    }
}

/** The first 8 bytes of MD5, mod [shards]: the same shard in every process. Given. */
fun shardFor(key: String, shards: Int): Int =
    Math.floorMod(ByteBuffer.wrap(MessageDigest.getInstance("MD5").digest(key.toByteArray())).long, shards.toLong()).toInt()

/** The base table: payments split over [shards] shards by a hash of the payment id. Given. */
open class PaymentShards(val shards: Int) {
    private val rows = List(shards) { HashMap<String, Payment>() }

    fun shardOf(paymentId: String): Int = shardFor(paymentId, shards)

    /** A lookup by the partition key asks one shard, and sees every write the moment it's made. */
    fun findById(id: String): Payment? = rows[shardOf(id)][id]

    protected fun store(p: Payment) {
        rows[shardOf(p.id)][p.id] = p
    }
}

/**
 * A LOCAL index (document-partitioned), the kind MongoDB, Cassandra's SAI and OpenSearch keep: each
 * shard indexes only its own rows, card -> ids of the payments stored on that same shard.
 */
class LocalIndexTable(shards: Int) : PaymentShards(shards) {
    private val index = List(shards) { HashMap<String, MutableSet<String>>() }

    /** Stores [p] on its shard and adds it to that shard's own index. Returns how many shards the write touched. */
    fun insert(p: Payment): Int {
        TODO("store(p), then add p.id under p.card in the index of shardOf(p.id)")
    }

    /** Every payment made with [card]. Any shard may hold some, so every shard's index has to be asked. */
    fun findByCard(card: String): QueryResult {
        TODO("ask every shard's index for the card and put the answers together")
    }
}

/**
 * A GLOBAL index (term-partitioned), the kind DynamoDB's GSIs and CockroachDB's secondary indexes are:
 * one index over all rows, itself split over [indexShards] index shards by a hash of the card. So all
 * the entries for one card sit on one index shard.
 *
 * The index entry for a write lands [lagMillis] after the write, the way DynamoDB updates a GSI
 * asynchronously. With a lag of 0 it lands at the same moment, like an index written in the same
 * distributed transaction as the row.
 */
class GlobalIndexTable(shards: Int, val indexShards: Int, val lagMillis: Long, private val clock: VirtualClock) :
    PaymentShards(shards) {
    private val index = List(indexShards) { HashMap<String, MutableSet<String>>() }

    private data class Pending(val dueAt: Long, val seq: Long, val card: String, val id: String)

    private val pending = PriorityQueue<Pending>(compareBy({ it.dueAt }, { it.seq }))
    private var seq = 0L

    /** The index shard that holds every entry for [card]. Given. */
    fun indexShardOf(card: String): Int = shardFor(card, indexShards)

    /** Index entries written to the queue but not applied yet. Given. */
    val pendingUpdates: Int get() = pending.size

    /**
     * Stores [p] on its base shard now, and queues its index entry (card -> id) to land on
     * `indexShardOf(p.card)` at `clock.now + lagMillis`. Returns how many shards the write touched:
     * the base shard and the index shard.
     */
    fun insert(p: Payment): Int {
        TODO("store(p) now; queue Pending(clock.now + lagMillis, seq++, p.card, p.id)")
    }

    /**
     * Every payment made with [card], as the index knows it right now. First apply every queued entry
     * whose time has come (`dueAt <= clock.now`), oldest first. Then read the one index shard for the
     * card and fetch the rows it names from their base shards: shardsContacted is 1 plus the number of
     * distinct base shards those rows live on.
     */
    fun findByCard(card: String): QueryResult {
        TODO("apply the due entries from pending, then read index[indexShardOf(card)]")
    }
}
