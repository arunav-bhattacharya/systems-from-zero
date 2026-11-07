package sfz.bigdata.l03

import org.apache.spark.sql.functions.col
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import sfz.bigdata.support.Duck
import sfz.bigdata.support.Duck.filesScanned
import sfz.bigdata.support.Duck.longOf
import sfz.bigdata.support.LocalSpark
import sfz.bigdata.support.TestData
import java.io.File
import java.nio.file.Files
import java.time.LocalDate

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class PaymentsLakeTest {
    private val spark = LocalSpark.session
    // seven days of payments, 1,000 a day
    private val payments = TestData.payments(7_000, days = 7)
    private val days = payments.map { it.dt }.distinct().sorted()
    // a directory name with a space, like many real home folders
    private val dir: File = Files.createTempDirectory("l03 lake").toFile()
    private var written = false

    /** The lake, written by your writeByDay the first time a test asks for it. */
    private val root: File
        get() {
            if (!written) {
                PaymentsLake.writeByDay(TestData.paymentsFrame(spark, payments), dir.absolutePath)
                written = true
            }
            return dir
        }

    @AfterAll
    fun cleanUp() {
        dir.deleteRecursively()
    }

    private fun parquetFiles(dir: File) =
        dir.walkTopDown().filter { it.isFile && it.name.endsWith(".parquet") }.toList()

    private fun expectedTotal(dt: String) = payments.filter { it.dt == dt }.sumOf { it.amountCents }

    @Test
    fun `writeByDay makes one dt directory per day and keeps dt out of the files`() {
        val dirs = root.listFiles { f -> f.isDirectory }!!.map { it.name }.sorted()
        assertThat(dirs).containsExactlyElementsOf(days.map { "dt=$it" })
        assertThat(parquetFiles(root)).isNotEmpty()
        // read one file on its own, without looking at its path: there is no dt column inside
        val oneFile = parquetFiles(root).first().absolutePath
        Duck.connect().use { c ->
            val columns = c.createStatement().use { s ->
                s.executeQuery("DESCRIBE SELECT * FROM read_parquet('$oneFile', hive_partitioning = false)").use { rs ->
                    buildList { while (rs.next()) add(rs.getString(1)) }
                }
            }
            assertThat(columns).contains("payment_id", "amount_cents").doesNotContain("dt")
        }
    }

    @Test
    fun `the registered table finds every day that is already on disk`() {
        spark.sql("DROP TABLE IF EXISTS l03_register")
        PaymentsLake.registerTable(spark, "l03_register", root.absolutePath)
        val perDay = spark.table("l03_register").groupBy("dt").count().collectAsList()
            .associate { it.get(0).toString() to it.getLong(1) }
        assertThat(perDay).hasSize(7)
        assertThat(perDay.values).allSatisfy { assertThat(it).isEqualTo(1_000L) }
    }

    @Test
    fun `dailyTotal sums one day and reads only that day's files`() {
        spark.sql("DROP TABLE IF EXISTS l03_daily")
        PaymentsLake.registerTable(spark, "l03_daily", root.absolutePath)
        val day = days[2]
        val query = PaymentsLake.dailyTotal(spark, "l03_daily", day)
        assertThat(query.collectAsList().single().getLong(0)).isEqualTo(expectedTotal(day))
        // inputFiles() lists the files the scan will open, after partition pruning
        val touched = query.inputFiles().toList()
        assertThat(touched).hasSize(parquetFiles(File(root, "dt=$day")).size)
        assertThat(touched).allSatisfy { assertThat(it).contains("/dt=$day/") }
    }

    @Test
    fun `a day written straight to disk is invisible until the partitions are refreshed`() {
        val lake = Files.createTempDirectory("l03 refresh").toFile()
        try {
            PaymentsLake.writeByDay(TestData.paymentsFrame(spark, payments), lake.absolutePath)
            spark.sql("DROP TABLE IF EXISTS l03_refresh")
            PaymentsLake.registerTable(spark, "l03_refresh", lake.absolutePath)

            // a late batch for 2026-11-08 lands in the table's directory, bypassing the catalog
            val late = TestData.payments(500, days = 1, firstDay = LocalDate.of(2026, 11, 8), seed = 9)
            TestData.paymentsFrame(spark, late).drop("dt").write().parquet(File(lake, "dt=2026-11-08").absolutePath)
            val lateDay = spark.table("l03_refresh").where(col("dt").equalTo("2026-11-08"))
            assertThat(lateDay.count()).isZero()

            PaymentsLake.refreshPartitions(spark, "l03_refresh")
            assertThat(spark.table("l03_refresh").where(col("dt").equalTo("2026-11-08")).count()).isEqualTo(500)
        } finally {
            spark.sql("DROP TABLE IF EXISTS l03_refresh")
            lake.deleteRecursively()
        }
    }

    @Test
    fun `DuckDB gets the same total from the files alone and opens only that day's files`() {
        val day = days[4]
        val sql = PaymentsLake.dailyTotalSql(root.absolutePath, day)
        Duck.connect().use { c ->
            assertThat(c.longOf(sql)).isEqualTo(expectedTotal(day))
            val (read, total) = c.filesScanned(sql) ?: error("no 'Scanning Files' line in DuckDB's plan for: $sql")
            assertThat(total).isEqualTo(parquetFiles(root).size)
            assertThat(read).isEqualTo(parquetFiles(File(root, "dt=$day")).size)
        }
    }
}
