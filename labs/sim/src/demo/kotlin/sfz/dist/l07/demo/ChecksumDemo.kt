package sfz.dist.l07.demo

import java.util.zip.CRC32C

/**
 * Lesson dist-07, section 5: cheap defences against data that lies.
 *
 * One payment record, damaged three ways. The Internet checksum (RFC 1071, the 16-bit sum that IP,
 * TCP and UDP use) and CRC-32C (what many storage engines and Kafka record batches use) each check
 * it, and so does a plain validation rule.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l07.demo.ChecksumDemoKt
 */
fun main() {
    // fixed-width fields; the amount (cents, 8 digits) starts at an even offset, so it is 4 whole 16-bit words
    val record = "pay-7731|m-cafe|EUR|00004000|CAPTURED"
    val amountAt = record.indexOf("00004000")
    check(amountAt % 2 == 0)
    val good = record.toByteArray(Charsets.US_ASCII)
    val sum = internetChecksum(good)
    val crc = crc32c(good)
    println("stored:   $record   inet=%04x  crc32c=%08x".format(sum, crc))
    println()

    // 1. one bit flips on the way: '4' is 0x34, '5' is 0x35
    val flipped = good.copyOf().also { it[amountAt + 4] = (it[amountAt + 4].toInt() xor 1).toByte() }
    report("one bit flipped", flipped, sum, crc)

    // 2. two 16-bit words swap places ("00" "40" swapped): a sum doesn't care about order
    val swapped = good.copyOf().also {
        val w1 = amountAt + 2
        val w2 = amountAt + 4
        for (k in 0..1) { val t = it[w1 + k]; it[w1 + k] = it[w2 + k]; it[w2 + k] = t }
    }
    report("two words swapped", swapped, sum, crc)

    // 3. a faulty CPU core computed the wrong amount before anyone took a checksum
    val wrongAtSource = record.replace("00004000", "04000000")
    val written = wrongAtSource.toByteArray(Charsets.US_ASCII)
    val writtenSum = internetChecksum(written)             // the checksums describe the wrong bytes faithfully
    val writtenCrc = crc32c(written)
    val read = written.copyOf()                            // nothing changes on the way to disk and back
    println("%-19s %s".format("wrong at source:", wrongAtSource))
    println("%-19s inet %s, crc32c %s, validation: %s".format(
        "",
        if (internetChecksum(read) == writtenSum) "passes" else "caught",
        if (crc32c(read) == writtenCrc) "passes" else "caught",
        validate(String(read, Charsets.US_ASCII)) ?: "ok",
    ))
}

private fun report(what: String, bytes: ByteArray, sum: Int, crc: Long) {
    val text = String(bytes, Charsets.US_ASCII)
    val inet = if (internetChecksum(bytes) == sum) "MISSED" else "caught"
    val c = if (crc32c(bytes) == crc) "MISSED" else "caught"
    println("%-19s %s   inet=%04x  crc32c=%08x".format("$what:", text, internetChecksum(bytes), crc32c(bytes)))
    println("%-19s inet %s, crc32c %s, validation: %s".format("", inet, c, validate(text) ?: "ok"))
    println()
}

/** RFC 1071: add the data as 16-bit big-endian words, fold the carries back in, take the ones' complement. */
fun internetChecksum(data: ByteArray): Int {
    var sum = 0L
    var i = 0
    while (i < data.size) {
        val hi = data[i].toInt() and 0xff
        val lo = if (i + 1 < data.size) data[i + 1].toInt() and 0xff else 0
        sum += (hi shl 8) or lo
        i += 2
    }
    while (sum shr 16 != 0L) sum = (sum and 0xffff) + (sum shr 16)
    return (sum.inv() and 0xffff).toInt()
}

fun crc32c(data: ByteArray): Long = CRC32C().apply { update(data) }.value

/** The business rules a record must meet, whatever its checksum says. Null if it passes. */
fun validate(record: String): String? {
    val (id, merchant, currency, cents, status) = record.split("|")
    val limit = 500_000L                                   // m-cafe never takes more than 5,000.00 in one payment
    return when {
        !id.startsWith("pay-") -> "bad id $id"
        currency !in setOf("EUR", "USD", "GBP") -> "unknown currency $currency"
        status !in setOf("AUTHORIZED", "CAPTURED", "REFUNDED") -> "unknown status $status"
        cents.toLong() > limit -> "amount ${cents.toLong() / 100}.%02d is over $merchant's limit".format(cents.toLong() % 100)
        else -> null
    }
}
