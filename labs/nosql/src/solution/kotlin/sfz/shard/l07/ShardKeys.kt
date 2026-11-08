package sfz.shard.l07

import java.nio.ByteBuffer
import java.security.MessageDigest

/** One payment, as the shard-key simulator sees it. Given. */
data class Payment(
    val paymentId: String,
    val merchantId: String,
    val accountId: String,
    val createdAtMillis: Long,
)

/** A 64-bit hash of [value]: the first 8 bytes of its MD5. Plays the hashed index's hash. Given. */
fun hash64(value: String): Long = ByteBuffer.wrap(MessageDigest.getInstance("MD5").digest(value.toByteArray())).long

/**
 * A point in the shard-key space. Given.
 *
 * A key is a list of 64-bit parts compared left to right, so `{ merchantId: "hashed", createdAt: 1 }`
 * has two parts: the merchant's hash, then the time. A key that runs out of parts sorts first, the way
 * MongoDB fills missing fields with MinKey. [MIN] and [MAX] are MongoDB's MinKey and MaxKey: lower and
 * higher than every real key. They only ever appear as chunk bounds.
 */
class Key private constructor(val parts: List<Long>, private val rank: Int) : Comparable<Key> {
    override fun compareTo(other: Key): Int {
        if (rank != other.rank) return rank.compareTo(other.rank)
        for (i in 0 until minOf(parts.size, other.parts.size)) {
            val c = parts[i].compareTo(other.parts[i])
            if (c != 0) return c
        }
        return parts.size.compareTo(other.parts.size)
    }

    override fun equals(other: Any?): Boolean = other is Key && compareTo(other) == 0
    override fun hashCode(): Int = parts.hashCode() * 31 + rank
    override fun toString(): String = when (rank) {
        -1 -> "MinKey"
        1 -> "MaxKey"
        else -> parts.joinToString(", ", "(", ")")
    }

    companion object {
        val MIN = Key(emptyList(), -1)
        val MAX = Key(emptyList(), 1)
        fun of(vararg parts: Long): Key = Key(parts.toList(), 0)
    }
}

/** Every key from [lo] to [hi], both included. Given. */
data class KeyRange(val lo: Key, val hi: Key)

/** A find() on payments: any field left null is not in the filter. Times are epoch millis, both ends included. Given. */
data class PaymentQuery(
    val paymentId: String? = null,
    val merchantId: String? = null,
    val fromMillis: Long? = null,
    val toMillis: Long? = null,
)

/** The four shard keys this lab compares, with the MongoDB key pattern each one stands for. */
enum class ShardKeyPattern(val mongo: String, val hashedPrefix: Boolean) {
    RANGED_CREATED_AT("{ createdAt: 1 }", false),
    HASHED_PAYMENT_ID("{ _id: \"hashed\" }", true),
    HASHED_MERCHANT("{ merchantId: \"hashed\" }", true),
    HASHED_MERCHANT_THEN_TIME("{ merchantId: \"hashed\", createdAt: 1 }", true);

    /**
     * The shard key value of [p].
     *
     * - RANGED_CREATED_AT: one part, the creation time as it is.
     * - HASHED_PAYMENT_ID: one part, `hash64(paymentId)` (the payment id is the document's `_id`).
     * - HASHED_MERCHANT: one part, `hash64(merchantId)`.
     * - HASHED_MERCHANT_THEN_TIME: two parts, `hash64(merchantId)`, then the creation time.
     */
    fun keyOf(p: Payment): Key = when (this) {
        RANGED_CREATED_AT -> Key.of(p.createdAtMillis)                         // the raw value: neighbours stay together
        HASHED_PAYMENT_ID -> Key.of(hash64(p.paymentId))                       // the hash: neighbours scatter
        HASHED_MERCHANT -> Key.of(hash64(p.merchantId))                        // one value per merchant, however busy
        HASHED_MERCHANT_THEN_TIME -> Key.of(hash64(p.merchantId), p.createdAtMillis) // a merchant, then its time order
    }

    /**
     * The smallest range of keys that holds every payment [q] can match, or null when the filter
     * doesn't pin the shard key down at all (mongos must then ask every shard). Given.
     */
    fun rangeFor(q: PaymentQuery): KeyRange? = when (this) {
        RANGED_CREATED_AT ->
            if (q.fromMillis == null && q.toMillis == null) null
            else KeyRange(Key.of(q.fromMillis ?: Long.MIN_VALUE), Key.of(q.toMillis ?: Long.MAX_VALUE))
        HASHED_PAYMENT_ID -> q.paymentId?.let { Key.of(hash64(it)).let { k -> KeyRange(k, k) } }
        HASHED_MERCHANT -> q.merchantId?.let { Key.of(hash64(it)).let { k -> KeyRange(k, k) } }
        HASHED_MERCHANT_THEN_TIME -> q.merchantId?.let {
            val h = hash64(it)
            KeyRange(Key.of(h, q.fromMillis ?: Long.MIN_VALUE), Key.of(h, q.toMillis ?: Long.MAX_VALUE))
        }
    }
}
