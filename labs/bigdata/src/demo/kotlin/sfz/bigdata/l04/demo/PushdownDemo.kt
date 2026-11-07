package sfz.bigdata.l04.demo

import org.apache.spark.sql.Column
import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.date_format
import org.apache.spark.sql.functions.hash
import org.apache.spark.sql.functions.lit
import org.apache.spark.sql.functions.pmod
import org.apache.spark.sql.functions.timestamp_seconds
import java.io.File

/**
 * Spark writes a week of 200,000 payments sorted by created_at, in small row groups, twice: with
 * its default timestamp type (INT96) and with TIMESTAMP_MICROS. Then it runs four filters and
 * prints what it pushed to the Parquet reader and how many rows the scan handed on.
 */
fun main() {
    val spark = demoSpark()
    spark.conf().set("spark.sql.maxMetadataStringLength", "400")      // print PushedFilters in full
    val payments = spark.range(0, 200_000, 1, 4).select(
        col("id").alias("payment_id"),
        pmod(hash(col("id")), lit(500)).alias("merchant_id"),
        pmod(hash(col("id"), lit(2)), lit(250_000)).plus(100).cast("bigint").alias("amount_cents"),
        // a random second in the week starting 2026-11-01 00:00 UTC
        timestamp_seconds(lit(1_793_491_200L).plus(pmod(hash(col("id"), lit(3)), lit(7 * 86_400)))).alias("created_at"),
    )
    val files = mutableMapOf<String, String>()
    for (type in listOf("TIMESTAMP_MICROS", "INT96")) {
        spark.conf().set("spark.sql.parquet.outputTimestampType", type)
        val dir = File("build/l04/by-time-$type").absolutePath
        payments.repartition(1).sortWithinPartitions("created_at")
            .write().mode(SaveMode.Overwrite).option("parquet.block.size", 256 * 1024).parquet(dir)
        files[type] = dir
    }
    val fromNov7 = col("created_at").geq(lit("2026-11-07 00:00:00").cast("timestamp"))
    val cases = listOf<Triple<String, String, Column>>(
        Triple("created_at >= '2026-11-07'", "TIMESTAMP_MICROS", fromNov7),
        Triple("date_format(created_at, 'yyyy-MM-dd') = '2026-11-07'", "TIMESTAMP_MICROS",
            date_format(col("created_at"), "yyyy-MM-dd").equalTo("2026-11-07")),
        Triple("merchant_id = 42", "TIMESTAMP_MICROS", col("merchant_id").equalTo(42)),
        Triple("created_at >= '2026-11-07'", "INT96", fromNov7),
    )
    for ((label, type, filter) in cases) {
        val query = spark.read().parquet(files.getValue(type)).where(filter)
        val matching = query.collectAsList().size
        println("WHERE $label   ($type file)")
        println("  PushedFilters: [${pushedFilters(query)}]")
        println("  scan handed on %,d of 200,000 rows; %,d match".format(scanRows(query), matching))
    }
    spark.stop()
}
