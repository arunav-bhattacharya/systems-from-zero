package sfz.bigdata.l08.demo

import org.apache.logging.log4j.Level
import org.apache.logging.log4j.core.config.Configurator
import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.array
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.element_at
import org.apache.spark.sql.functions.hash
import org.apache.spark.sql.functions.lit
import org.apache.spark.sql.functions.pmod
import java.io.File

/** A quiet local SparkSession for the lesson 8 demos: loopback only, UTC, 4 shuffle partitions. */
fun demoSpark(configure: SparkSession.Builder.() -> Unit = {}): SparkSession =
    SparkSession.builder()
        .appName("sfz-demo")
        .master("local[2]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .apply(configure)
        .getOrCreate()
        .also {
            it.sparkContext().setLogLevel("ERROR")
            // the demos fail some queries on purpose; the error reaches the demo, so skip the executor's log
            Configurator.setLevel("org.apache.spark.executor.Executor", Level.OFF)
            Configurator.setLevel("org.apache.spark.scheduler.TaskSetManager", Level.OFF)
        }

/** 400,000 made-up payments as 4 Parquet files under build/l08/payments, the same rows every run. */
fun demoPayments(spark: SparkSession): Dataset<Row> {
    val dir = File("build/l08/payments")
    if (!File(dir, "_SUCCESS").exists()) {
        spark.range(0, 400_000, 1, 4).select(
            col("id").alias("payment_id"),
            pmod(hash(col("id")), lit(500)).alias("merchant_id"),
            element_at(array(lit("AUTHORIZED"), lit("CAPTURED"), lit("DECLINED"), lit("REFUNDED")),
                pmod(hash(col("id"), lit(1)), lit(4)).plus(1)).alias("status"),
            pmod(hash(col("id"), lit(2)), lit(250_000)).plus(100).cast("bigint").alias("amount_cents"),
        ).write().mode(SaveMode.Overwrite).parquet(dir.absolutePath)
    }
    return spark.read().parquet(dir.absolutePath)
}

/** Runs [sql] and returns its single value as text (NULL for null), or the error class and first line if it fails. */
fun valueOrError(spark: SparkSession, sql: String): String =
    runCatching { (spark.sql(sql).collectAsList().first().get(0) ?: "NULL").toString() }
        .getOrElse { e ->
            val msg = (e.message ?: "").lines().first()
            e.javaClass.simpleName + ": " + msg.substringBefore(". ").take(110)
        }
