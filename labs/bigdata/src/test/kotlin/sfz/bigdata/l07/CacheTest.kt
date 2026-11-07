package sfz.bigdata.l07

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.execution.FileSourceScanExec
import org.apache.spark.sql.execution.FilterExec
import org.apache.spark.sql.execution.SparkPlan
import org.apache.spark.sql.execution.columnar.InMemoryTableScanExec
import org.apache.spark.storage.StorageLevel
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import sfz.bigdata.support.LocalSpark
import sfz.bigdata.support.Payment
import sfz.bigdata.support.Plans
import sfz.bigdata.support.TestData
import java.io.File
import java.nio.file.Files

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class CacheTest {
    private val spark: SparkSession = LocalSpark.isolated()
    private val dir: File = Files.createTempDirectory("l07 cache").toFile()
    private val rows: List<Payment> = TestData.payments(20_000)
    private val payments: Dataset<Row> = TestData.paymentsParquet(spark, rows, File(dir, "payments"))
    private val captured: Long = rows.count { it.status == "CAPTURED" }.toLong()

    @AfterEach
    fun release() {
        // whatever your code left behind, don't let it leak into the next test
        payments.unpersist(true)
        NightlyReports.captured(payments).unpersist(true)
    }

    @AfterAll
    fun cleanUp() {
        dir.deleteRecursively()
    }

    private fun cachedScans(plans: List<SparkPlan>) = plans.flatMap { Plans.nodes(it).filterIsInstance<InMemoryTableScanExec>() }

    @Test
    fun `both reports are right`() {
        val (byMerchant, byCountry) = NightlyReports.run(payments)
        val ok = rows.filter { it.status == "CAPTURED" }
        assertThat(byMerchant.associate { it.getInt(0) to it.getLong(1) })
            .isEqualTo(ok.groupBy { it.merchantId }.mapValues { (_, ps) -> ps.sumOf { it.amountCents } })
        assertThat(byCountry.associate { it.getString(0) to it.getLong(1) })
            .isEqualTo(ok.groupingBy { it.cardCountry }.eachCount().mapValues { it.value.toLong() })
    }

    @Test
    fun `both reports read the cache, and neither one scans the Parquet files itself`() {
        val plans = Plans.executedDuring(spark) { NightlyReports.run(payments) }
        val reports = plans.filter { p -> Plans.nodes(p).any { it.nodeName() == "HashAggregate" } }
        assertThat(reports).describedAs("the two report actions").hasSize(2)
        assertThat(reports).allSatisfy { p ->
            assertThat(Plans.nodes(p).filterIsInstance<InMemoryTableScanExec>()).describedAs("InMemoryTableScan").isNotEmpty()
            assertThat(Plans.nodes(p).filterIsInstance<FileSourceScanExec>()).describedAs("a direct file scan").isEmpty()
        }
    }

    @Test
    fun `the cache holds only the captured payments, filtered before they were cached`() {
        val plans = Plans.executedDuring(spark) { NightlyReports.run(payments) }
        val scans = cachedScans(plans)
        assertThat(scans).isNotEmpty()
        for (scan in scans) {
            // the plan that filled the cache must contain the filter, so only captured rows went into memory
            assertThat(Plans.nodes(scan.relation().cachedPlan()).filterIsInstance<FilterExec>())
                .describedAs("a Filter inside the cached plan").isNotEmpty()
            // every row the cached scan handed on was a captured payment: a quarter of the table, not all of it
            assertThat(Plans.metric(scan, "numOutputRows")).isEqualTo(captured)
        }
    }

    @Test
    fun `nothing stays cached after the job`() {
        NightlyReports.run(payments)
        assertThat(payments.storageLevel()).describedAs("payments still cached").isEqualTo(StorageLevel.NONE())
        assertThat(NightlyReports.captured(payments).storageLevel()).describedAs("captured payments still cached").isEqualTo(StorageLevel.NONE())
    }
}
