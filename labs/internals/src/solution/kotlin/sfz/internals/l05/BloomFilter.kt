package sfz.internals.l05

import java.nio.ByteBuffer
import kotlin.math.roundToInt

/**
 * A Bloom filter: an array of [bits] bits and [hashes] hash functions.
 *
 * - [add] sets the [hashes] bits that the key hashes to.
 * - [mightContain] checks those same bits. If any is 0, the key was never added: the answer "no" is
 *   always right. If all are 1, the key was probably added, or other keys happened to set those bits
 *   (a false positive).
 *
 * The k bit positions come from one 64-bit hash split into two 32-bit halves, h1 and h2: position i is
 * `(h1 + i * h2) mod bits` (Kirsch and Mitzenmacher's double hashing; RocksDB does something similar).
 */
class BloomFilter(val bits: Int, val hashes: Int) {
    init {
        require(bits > 0 && hashes > 0) { "bits and hashes must be positive" }
    }

    private val words = LongArray((bits + 63) / 64)

    /** Records [key]: sets bit [bitIndex] for i = 0 until [hashes]. */
    fun add(key: String) {
        val h = hash64(key)
        val h1 = h.toInt()                      // low 32 bits
        val h2 = (h ushr 32).toInt()            // high 32 bits
        for (i in 0 until hashes) setBit(bitIndex(h1, h2, i))
    }

    /** False means [key] was certainly never added. True means it probably was. */
    fun mightContain(key: String): Boolean {
        val h = hash64(key)
        val h1 = h.toInt()
        val h2 = (h ushr 32).toInt()
        for (i in 0 until hashes) {
            if (!getBit(bitIndex(h1, h2, i))) return false   // one clear bit is proof: never added
        }
        return true                                          // all set: added, or a false positive
    }

    // ---------------------------------------------------------------- provided

    /** The i-th bit position for a key whose hash halves are [h1] and [h2]. */
    fun bitIndex(h1: Int, h2: Int, i: Int): Int = Math.floorMod(h1 + i * h2, bits)

    fun setBit(i: Int) {
        words[i ushr 6] = words[i ushr 6] or (1L shl (i and 63))
    }

    fun getBit(i: Int): Boolean = words[i ushr 6] and (1L shl (i and 63)) != 0L

    /** How many bits are 1. A filter with about half its bits set is sized well. */
    fun bitsSet(): Int = words.sumOf { java.lang.Long.bitCount(it) }

    /** The filter as bytes, for the SSTable file: `[bits int][hashes int][words long...]`. */
    fun toBytes(): ByteArray {
        val b = ByteBuffer.allocate(8 + 8 * words.size).putInt(bits).putInt(hashes)
        for (w in words) b.putLong(w)
        return b.array()
    }

    companion object {
        /** A filter for [keys] keys with [bitsPerKey] bits each, and the number of hashes that suits it. */
        fun forKeys(keys: Int, bitsPerKey: Int): BloomFilter =
            BloomFilter(maxOf(64, keys * bitsPerKey), optimalHashes(bitsPerKey))

        /** k = bits per key x ln 2, about 0.69 x bits per key: 10 bits per key gives 7 hashes. */
        fun optimalHashes(bitsPerKey: Int): Int = (bitsPerKey * 0.69).roundToInt().coerceIn(1, 30)

        /** Reads a filter written by [toBytes]. */
        fun fromBytes(bytes: ByteArray): BloomFilter {
            val b = ByteBuffer.wrap(bytes)
            val f = BloomFilter(b.getInt(), b.getInt())
            for (i in f.words.indices) f.words[i] = b.getLong()
            return f
        }

        /** A 64-bit hash of the key's UTF-8 bytes: FNV-1a, then MurmurHash3's finalizer to mix the bits. */
        fun hash64(key: String): Long {
            var h = -0x340d631b7bdddcdbL            // FNV-1a 64-bit offset basis
            for (b in key.encodeToByteArray()) {
                h = h xor (b.toLong() and 0xff)
                h *= 0x100000001b3L                 // FNV prime
            }
            h = h xor (h ushr 33)
            h *= -0xae502812aa7333L
            h = h xor (h ushr 33)
            h *= -0x3b314601e57a13adL
            return h xor (h ushr 33)
        }
    }
}
