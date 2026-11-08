package sfz.store.l05.demo

import kotlin.math.exp
import kotlin.math.roundToInt

/**
 * Builds Bloom filters for 100,000 payment ids (or as many as the first argument says) at several sizes,
 * and measures how often each one says "maybe" for 1,000,000 ids it never saw. Prints the measured
 * false-positive rate next to the formula (1 - e^(-k/b))^k, where b is bits per key and k the number of hashes.
 */
fun main(args: Array<String>) {
    val keys = args.firstOrNull()?.toInt() ?: 100_000
    val probes = 1_000_000
    println("bits/key  hashes  filter size  measured FP  formula")
    for (bitsPerKey in listOf(2, 4, 6, 8, 10, 12, 16)) {
        val k = (bitsPerKey * 0.69).roundToInt().coerceAtLeast(1)    // the best k is about 0.69 x bits per key
        val bits = keys * bitsPerKey
        val words = LongArray((bits + 63) / 64)
        fun positions(key: String, each: (Int) -> Unit) {
            val h = hash64(key)
            val h1 = h.toInt()
            val h2 = (h ushr 32).toInt()
            for (i in 0 until k) each(Math.floorMod(h1 + i * h2, bits))
        }
        for (i in 0 until keys) positions("pay-$i") { words[it ushr 6] = words[it ushr 6] or (1L shl (it and 63)) }
        var yes = 0
        for (i in 0 until probes) {
            var all = true
            positions("ref-$i") { if (words[it ushr 6] and (1L shl (it and 63)) == 0L) all = false }
            if (all) yes++                                                // a false positive: never added
        }
        val formula = Math.pow(1 - exp(-k.toDouble() / bitsPerKey), k.toDouble())
        println("%8d  %6d  %8.1f KB  %10.2f%%  %6.2f%%".format(bitsPerKey, k, bits / 8 / 1024.0, 100.0 * yes / probes, 100 * formula))
    }
}

/** FNV-1a over the UTF-8 bytes, then MurmurHash3's finalizer: the same hash as the lab's BloomFilter. */
private fun hash64(key: String): Long {
    var h = -0x340d631b7bdddcdbL
    for (b in key.encodeToByteArray()) {
        h = h xor (b.toLong() and 0xff)
        h *= 0x100000001b3L
    }
    h = h xor (h ushr 33)
    h *= -0xae502812aa7333L
    h = h xor (h ushr 33)
    h *= -0x3b314601e57a13adL
    return h xor (h ushr 33)
}
