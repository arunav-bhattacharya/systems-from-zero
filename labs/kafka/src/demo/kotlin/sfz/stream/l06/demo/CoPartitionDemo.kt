package sfz.stream.l06.demo

import org.apache.kafka.common.utils.Utils
import java.util.zip.CRC32

/** The Java producer's partition for a key: murmur2 of the bytes, made positive, modulo the count. */
fun murmur2Partition(key: String, n: Int) = Utils.toPositive(Utils.murmur2(key.toByteArray())) % n

/** librdkafka's default ("consistent_random") for a non-empty key: CRC32 of the bytes, modulo the count. */
fun crc32Partition(key: String, n: Int) = (CRC32().apply { update(key.toByteArray()) }.value % n).toInt()

/**
 * Where 10,000 customer keys land in two topics, and how many land on a different partition number in the second
 * one. A partitioned join of the two topics loses every one of those keys.
 */
fun main() {
    val keys = (0 until 10_000).map { "c-$it" }
    println("c-42: partition ${murmur2Partition("c-42", 3)} of 3 in orders, partition ${murmur2Partition("c-42", 2)} of 2 in customer-tiers")
    fun share(name: String, a: (String) -> Int, b: (String) -> Int) {
        val differ = keys.count { a(it) != b(it) }
        println("%-46s %5d of %d keys on a different partition (%.1f%%)".format(name, differ, keys.size, 100.0 * differ / keys.size))
    }
    share("orders 3, tiers 3, both Java producers", { murmur2Partition(it, 3) }, { murmur2Partition(it, 3) })
    share("orders 3, tiers 2, both Java producers", { murmur2Partition(it, 3) }, { murmur2Partition(it, 2) })
    share("orders 6, tiers grown from 6 to 12", { murmur2Partition(it, 6) }, { murmur2Partition(it, 12) })
    share("orders 3 (Java), tiers 3 (librdkafka default)", { murmur2Partition(it, 3) }, { crc32Partition(it, 3) })
}
