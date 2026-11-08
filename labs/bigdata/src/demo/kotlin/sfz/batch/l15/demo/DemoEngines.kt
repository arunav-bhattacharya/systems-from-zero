package sfz.batch.l15.demo

import org.apache.spark.sql.SparkSession
import java.io.File
import java.sql.Connection
import java.sql.DriverManager

/** Everything the lesson 15 demos write goes under build/l12. */
val DEMO_DIR = File("build/l12")

/** A fresh demo folder. */
fun freshDemoDir(): File = DEMO_DIR.apply { deleteRecursively(); mkdirs() }

/**
 * A quiet local SparkSession using every core, with an Iceberg Hadoop catalog `lake` under
 * build/l12/warehouse.
 */
fun demoSpark(): SparkSession = SparkSession.builder()
    .appName("sfz-demo")
    .master("local[*]")
    .config("spark.ui.enabled", "false")
    .config("spark.sql.shuffle.partitions", Runtime.getRuntime().availableProcessors().toString())
    .config("spark.sql.session.timeZone", "UTC")
    .config("spark.driver.host", "127.0.0.1")
    .config("spark.driver.bindAddress", "127.0.0.1")
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
    .config("spark.sql.catalog.lake", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.lake.type", "hadoop")
    .config("spark.sql.catalog.lake.warehouse", File(DEMO_DIR, "warehouse").absolutePath)
    .getOrCreate()
    .also { it.sparkContext().setLogLevel("ERROR") }

/** A new in-memory DuckDB database. */
fun duck(): Connection = DriverManager.getConnection("jdbc:duckdb:")

fun Connection.run(sql: String) {
    createStatement().use { it.execute(sql) }
}

fun Connection.rows(sql: String): List<List<Any?>> = createStatement().use { s ->
    s.executeQuery(sql).use { rs ->
        buildList { while (rs.next()) add((1..rs.metaData.columnCount).map { rs.getObject(it) }) }
    }
}

/**
 * Writes [n] payments as 8 Parquet files under [dir] with DuckDB: `payment_id`, `merchant_id`
 * (0 to 499), `card_country`, `status`, `amount_cents` and `dt` (7 days from 2026-11-01, as a
 * DATE). Also writes 500 merchants with `merchant_id`, `merchant_name` and `mcc`
 * (5000 + id mod 20) under [merchants].
 */
fun writePayments(c: Connection, n: Long, dir: File, merchants: File) {
    dir.deleteRecursively()
    dir.mkdirs()
    merchants.deleteRecursively()
    merchants.mkdirs()
    for (part in 0 until 8) {
        c.run("""
            COPY (
              SELECT i AS payment_id,
                     (hash(i) % 500)::INTEGER AS merchant_id,
                     ['NL', 'DE', 'FR', 'GB', 'US', 'IN', 'BR', 'JP'][(hash(i + 1) % 8)::INTEGER + 1] AS card_country,
                     ['AUTHORIZED', 'CAPTURED', 'CAPTURED', 'DECLINED', 'REFUNDED'][(hash(i + 2) % 5)::INTEGER + 1] AS status,
                     (hash(i + 3) % 250000 + 100)::BIGINT AS amount_cents,
                     DATE '2026-11-01' + (i % 7)::INTEGER AS dt
              FROM range(${part * n / 8}, ${(part + 1) * n / 8}) t(i)
            ) TO '${File(dir, "part-$part.parquet").absolutePath}' (FORMAT parquet)""")
    }
    c.run("""
        COPY (SELECT i::INTEGER AS merchant_id, 'Merchant ' || i AS merchant_name, (5000 + i % 20)::INTEGER AS mcc
              FROM range(500) t(i))
        TO '${File(merchants, "merchants.parquet").absolutePath}' (FORMAT parquet)""")
}

/** The size of every file under [dir], in MB. */
fun megabytes(dir: File): Double = dir.walkTopDown().filter { it.isFile }.sumOf { it.length() } / 1e6
