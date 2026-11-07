package sfz.bigdata.l03.demo

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.date_format
import org.apache.spark.sql.functions.element_at
import org.apache.spark.sql.functions.array
import org.apache.spark.sql.functions.hash
import org.apache.spark.sql.functions.lit
import org.apache.spark.sql.functions.pmod
import org.apache.spark.sql.functions.timestamp_seconds
import java.io.File

/** A quiet local SparkSession for the demos: no web UI, loopback only, 4 shuffle partitions. */
fun demoSpark(): SparkSession =
    SparkSession.builder()
        .appName("sfz-demo")
        .master("local[2]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
        .also { it.sparkContext().setLogLevel("ERROR") }

/** 10,000 made-up payments a day for [days] days from 2026-11-01, the same rows every run. */
fun demoPayments(spark: SparkSession, days: Int = 7, firstEpochSecond: Long = 1_793_491_200L): Dataset<Row> =
    spark.range(0L, days * 10_000L).select(
        col("id").alias("payment_id"),
        pmod(hash(col("id")), lit(500)).alias("merchant_id"),
        element_at(array(lit("NL"), lit("DE"), lit("FR"), lit("GB")), pmod(hash(col("id"), lit(1)), lit(4)).plus(1)).alias("card_country"),
        pmod(hash(col("id"), lit(2)), lit(250_000)).plus(100).cast("bigint").alias("amount_cents"),
        // day = id / 10,000, plus a pseudo-random second inside that day
        timestamp_seconds(col("id").divide(10_000).cast("long").multiply(86_400).plus(firstEpochSecond)
            .plus(pmod(hash(col("id"), lit(3)), lit(86_400)))).alias("created_at"),
    ).withColumn("dt", date_format(col("created_at"), "yyyy-MM-dd"))

/** Relative paths of the data files under [root], skipping Spark's .crc and _SUCCESS files. */
fun dataFiles(root: File): List<String> =
    root.walkTopDown().filter { it.isFile && it.name.endsWith(".parquet") }.map { it.relativeTo(root).path }.sorted().toList()
