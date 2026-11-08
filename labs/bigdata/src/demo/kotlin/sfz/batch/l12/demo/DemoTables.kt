package sfz.batch.l12.demo

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.array
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.element_at
import org.apache.spark.sql.functions.hash
import org.apache.spark.sql.functions.lit
import org.apache.spark.sql.functions.pmod
import org.apache.spark.sql.functions.timestamp_seconds
import java.io.File

/** The lesson 12 demos' warehouse: an Iceberg Hadoop catalog named `lake`, plain folders under build/l10. */
val WAREHOUSE = File("build/l10/warehouse")

/**
 * A quiet local SparkSession with the Iceberg SQL extensions and a Hadoop catalog `lake`.
 * [extra] adds settings, for example a second catalog.
 */
fun demoSpark(vararg extra: Pair<String, String>): SparkSession {
    WAREHOUSE.deleteRecursively()
    WAREHOUSE.mkdirs()
    val b = SparkSession.builder()
        .appName("sfz-demo")
        .master("local[2]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.lake", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.lake.type", "hadoop")
        .config("spark.sql.catalog.lake.warehouse", WAREHOUSE.absolutePath)
        .config("spark.sql.catalog.lake.cache-enabled", "false")
    for ((k, v) in extra) b.config(k, v)
    return b.getOrCreate().also { it.sparkContext().setLogLevel("ERROR") }
}

/** The payments table's columns, for CREATE TABLE. */
const val PAYMENT_COLUMNS = "payment_id BIGINT, merchant_id INT, card_country STRING, amount_cents BIGINT, status STRING, created_at TIMESTAMP"

/** [n] payments with ids from [from], spread evenly over [days] days from 2026-11-01 (UTC). The same rows every run. */
fun payments(spark: SparkSession, from: Long, n: Long, days: Int = 3): Dataset<Row> =
    spark.range(from, from + n, 1, 2).select(
        col("id").alias("payment_id"),
        pmod(hash(col("id")), lit(500)).alias("merchant_id"),
        element_at(array(lit("NL"), lit("DE"), lit("FR"), lit("GB")), pmod(hash(col("id"), lit(1)), lit(4)).plus(1)).alias("card_country"),
        pmod(hash(col("id"), lit(2)), lit(250_000)).plus(100).cast("bigint").alias("amount_cents"),
        lit("CAPTURED").alias("status"),
        // 2026-11-01T00:00Z is 1793491200; payment i lands on day (i mod days), at some second of it
        timestamp_seconds(lit(1_793_491_200L).plus(col("id").mod(days).multiply(86_400)).plus(pmod(hash(col("id"), lit(4)), lit(86_400)))).alias("created_at"),
    )

/** The summary map of the newest snapshot of [table]. */
fun lastSummary(spark: SparkSession, table: String): Map<String, String> =
    spark.sql("SELECT summary FROM $table.snapshots ORDER BY committed_at DESC LIMIT 1").first().getJavaMap<String, String>(0).toMap()

/** The folder of table `lake.<namespace>.<table>`. */
fun tableDir(namespace: String, table: String) = File(WAREHOUSE, "$namespace/$table")

/** Every file under the table's data folder. */
fun dataFolderFiles(dir: File): List<File> = File(dir, "data").walkTopDown().filter { it.isFile && !it.name.startsWith(".") }.toList()

/** Bytes as KB or MB, for printing. */
fun size(bytes: Long): String = if (bytes >= 1_000_000) "%.1f MB".format(bytes / 1e6) else "%.1f KB".format(bytes / 1e3)

/** A path with the uuid parts cut out, for printing. */
fun short(path: String): String =
    path.substringAfterLast("/data/").replace(Regex("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"), "<uuid>")
