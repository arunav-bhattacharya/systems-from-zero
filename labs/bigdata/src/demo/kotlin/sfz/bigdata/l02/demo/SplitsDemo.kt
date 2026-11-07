package sfz.bigdata.l02.demo

import java.io.File
import kotlin.random.Random

/**
 * Writes a 300 MB text file once, then asks Spark how many input partitions (tasks) it cuts the
 * file into: first with the default 128 MB split size, then with 32 MB.
 */
fun main() {
    val file = File("build/l02/auth-log.txt")
    if (!file.exists()) writeLog(file, targetBytes = 300_000_000L)
    val spark = demoSpark(threads = 2)
    println("file: %s, %,.0f MB".format(file.name, file.length() / 1e6))
    for (split in listOf("128m", "32m")) {
        spark.conf().set("spark.sql.files.maxPartitionBytes", split)   // the most bytes one task reads
        val partitions = spark.read().text(file.absolutePath).javaRDD().getNumPartitions()
        println("maxPartitionBytes=%-4s -> %d partitions, so %d map tasks".format(split, partitions, partitions))
    }
    spark.stop()
}

/** Lines of made-up authorization log events, about [targetBytes] in total. */
private fun writeLog(file: File, targetBytes: Long) {
    file.parentFile.mkdirs()
    val words = listOf("approved", "declined", "refunded", "captured", "reversed", "card", "merchant", "issuer", "timeout", "retry")
    val rnd = Random(1)
    file.bufferedWriter().use { out ->
        var written = 0L
        while (written < targetBytes) {
            val line = (1..10).joinToString(" ") { words[rnd.nextInt(words.size)] }
            out.write(line); out.newLine()
            written += line.length + 1
        }
    }
}
