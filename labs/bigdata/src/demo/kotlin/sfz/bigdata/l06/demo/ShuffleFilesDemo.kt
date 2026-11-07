package sfz.bigdata.l06.demo

import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.col
import java.io.DataInputStream
import java.io.File

/**
 * Shuffles 1,000,000 payments by merchant_id into 4 partitions, then lists the shuffle files the
 * 4 map tasks left in spark.local.dir and decodes one index file by hand.
 */
fun main() {
    val local = File("build/l06/local").apply { deleteRecursively(); mkdirs() }
    val spark = demoSpark(localDir = local)
    val log = StageLog(spark)
    val byMerchant = payments(spark).repartition(4, col("merchant_id"))
    // the action: every reduce task reads its whole partition and throws the rows away
    val (_, stages) = log.run { byMerchant.foreachPartition { rows: Iterator<Row> -> rows.forEach { _ -> } } }
    for (s in stages) {
        println("stage %d: %d tasks, shuffle write %,d records / %,d bytes, shuffle read %,d bytes".format(
            s.id, s.tasks, s.recordsWritten, s.bytesWritten, s.bytesRead))
    }
    val files = local.walkTopDown().filter { it.isFile && it.name.startsWith("shuffle_") }.sortedBy { it.name }.toList()
    println("files in spark.local.dir (blockmgr-.../xx/):")
    files.filter { !it.name.contains("checksum") }.forEach { println("  %-24s %,10d bytes".format(it.name, it.length())) }
    // an index file is N + 1 longs: where each reduce partition's block starts in the .data file
    val index = files.first { it.name.endsWith(".index") }
    val offsets = DataInputStream(index.inputStream()).use { d -> List((index.length() / 8).toInt()) { d.readLong() } }
    println("${index.name}: offsets $offsets")
    println("  so reduce task r fetches bytes offsets[r] until offsets[r + 1] of ${index.name.replace(".index", ".data")}")
    spark.stop()
}
