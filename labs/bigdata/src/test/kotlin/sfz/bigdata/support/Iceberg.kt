package sfz.bigdata.support

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession
import java.io.File

/** Helpers for lessons 10 to 12, which build Iceberg tables in a Hadoop catalog (plain folders). */
object Iceberg {
    /**
     * A session with an Iceberg catalog called [catalog] whose warehouse is [warehouse], usually
     * a JUnit `@TempDir`. Take the folder as a `@BeforeAll` parameter: a `@TempDir` field is
     * injected again for every test, even with `PER_CLASS`. [extra] adds more settings, for
     * example `"spark.sql.catalog.l11.cache-enabled" to "false"`.
     */
    fun session(catalog: String, warehouse: File, vararg extra: Pair<String, String>): SparkSession = LocalSpark.isolated(
        "spark.sql.catalog.$catalog" to "org.apache.iceberg.spark.SparkCatalog",
        "spark.sql.catalog.$catalog.type" to "hadoop",
        "spark.sql.catalog.$catalog.warehouse" to warehouse.absolutePath,
        *extra,
    )

    /** [rows] as the payments table's columns: [TestData.PAYMENT_SCHEMA] without `dt`. */
    fun frame(spark: SparkSession, rows: List<Payment>): Dataset<Row> = TestData.paymentsFrame(spark, rows).drop("dt")

    /** Payments with ids [from] until [from] + [n], spread over 3 days (payment i lands on day i mod 3). */
    fun payments(spark: SparkSession, from: Int, n: Int): Dataset<Row> = frame(spark, TestData.payments(from + n, days = 3).drop(from))

    /** Every file under [tableDir]/data whose name ends with [suffix], as absolute paths. */
    fun filesOnDisk(tableDir: File, suffix: String = ".parquet"): Set<String> =
        File(tableDir, "data").walkTopDown().filter { it.isFile && it.name.endsWith(suffix) }.map { it.absolutePath }.toSet()

    /** The first column of every row of [sql], as strings with any `file:` prefix removed. */
    fun strings(spark: SparkSession, sql: String): List<String> =
        spark.sql(sql).collectAsList().map { it.get(0).toString().removePrefix("file:") }
}
