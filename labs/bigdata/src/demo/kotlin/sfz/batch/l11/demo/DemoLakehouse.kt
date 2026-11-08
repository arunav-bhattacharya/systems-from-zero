package sfz.batch.l11.demo

import com.fasterxml.jackson.databind.JsonNode
import com.fasterxml.jackson.databind.ObjectMapper
import org.apache.avro.file.DataFileReader
import org.apache.avro.generic.GenericDatumReader
import org.apache.avro.generic.GenericRecord
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

/** The demos' warehouse: an Iceberg Hadoop catalog named `lake`, plain folders under build/l09. */
val WAREHOUSE = File("build/l09/warehouse")

/**
 * A quiet local SparkSession with the Iceberg SQL extensions and a Hadoop catalog `lake`. The
 * catalog's table cache is off, so every query reads the table pointer again, as another
 * process would.
 */
fun demoSpark(fresh: Boolean = true): SparkSession {
    if (fresh) WAREHOUSE.deleteRecursively()
    WAREHOUSE.mkdirs()
    return SparkSession.builder()
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
        .getOrCreate()
        .also { it.sparkContext().setLogLevel("ERROR") }
}

/** The payments table's columns, for CREATE TABLE. */
const val PAYMENT_COLUMNS = "payment_id BIGINT, merchant_id INT, card_country STRING, amount_cents BIGINT, status STRING, created_at TIMESTAMP"

/**
 * [n] payments with ids from [from], spread evenly over [days] days from 2026-11-01 (UTC), in
 * [files] partitions. The same rows every run.
 */
fun payments(spark: SparkSession, from: Long, n: Long, days: Int = 3, files: Int = 2): Dataset<Row> =
    spark.range(from, from + n, 1, files).select(
        col("id").alias("payment_id"),
        pmod(hash(col("id")), lit(500)).alias("merchant_id"),
        element_at(array(lit("NL"), lit("DE"), lit("FR"), lit("GB")), pmod(hash(col("id"), lit(1)), lit(4)).plus(1)).alias("card_country"),
        pmod(hash(col("id"), lit(2)), lit(250_000)).plus(100).cast("bigint").alias("amount_cents"),
        element_at(array(lit("AUTHORIZED"), lit("CAPTURED"), lit("DECLINED")), pmod(hash(col("id"), lit(3)), lit(3)).plus(1)).alias("status"),
        // 2026-11-01T00:00Z is 1793491200; each payment lands on day (id mod days), at some second of it
        timestamp_seconds(lit(1_793_491_200L).plus(col("id").mod(days).multiply(86_400)).plus(pmod(hash(col("id"), lit(4)), lit(86_400)))).alias("created_at"),
    )

/** The folder of table `lake.<namespace>.<table>`. */
fun tableDir(namespace: String, table: String) = File(WAREHOUSE, "$namespace/$table")

/** Parsed JSON of a file. */
fun json(file: File): JsonNode = ObjectMapper().readTree(file)

/** The records of an Avro file (manifest lists and manifests are Avro). */
fun avro(path: String): List<GenericRecord> =
    DataFileReader(File(path.removePrefix("file:")), GenericDatumReader<GenericRecord>()).use { it.toList() }

/** [path] relative to the table folder [dir], for printing. */
fun rel(dir: File, path: String): String = File(path.removePrefix("file:")).relativeTo(dir.absoluteFile).path
