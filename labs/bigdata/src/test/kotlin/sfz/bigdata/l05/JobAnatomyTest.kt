package sfz.bigdata.l05

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.execution.FilterExec
import org.apache.spark.sql.functions.col
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import sfz.bigdata.support.Jobs
import sfz.bigdata.support.LocalSpark
import sfz.bigdata.support.Payment
import sfz.bigdata.support.Plans
import sfz.bigdata.support.TestData
import java.io.File
import java.nio.file.Files

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class JobAnatomyTest {
    // AQE off: one job per action and a plan that doesn't change while it runs (lesson 7 turns it back on)
    private val spark: SparkSession = LocalSpark.isolated("spark.sql.adaptive.enabled" to "false")
    private val rows: List<Payment> = TestData.payments(20_000)
    private val dir: File = Files.createTempDirectory("l05 payments").toFile()
    // four Parquet files, so the first stage has four input partitions
    private val payments: Dataset<Row> = TestData.paymentsParquet(spark, rows, dir, files = 4)

    @AfterAll
    fun cleanUp() {
        dir.deleteRecursively()
    }

    @Test
    fun `shuffles finds the Exchange that a groupBy adds, with the filter below it`() {
        val narrow = payments.where(col("amount_cents").gt(1_000)).select("merchant_id", "amount_cents")
        assertThat(JobAnatomy.shuffles(narrow.queryExecution().executedPlan())).isEmpty()

        val grouped = payments.where(col("amount_cents").gt(1_000)).groupBy("merchant_id").count()
        val shuffles = JobAnatomy.shuffles(grouped.queryExecution().executedPlan())
        assertThat(shuffles).hasSize(1)
        assertThat(shuffles.single().numPartitions()).isEqualTo(4)            // spark.sql.shuffle.partitions
        // the stage boundary falls above the filter: the filter runs in the first stage, before the shuffle
        assertThat(Plans.nodes(shuffles.single()).filterIsInstance<FilterExec>()).hasSize(1)

        val sorted = grouped.orderBy(col("count").desc())
        assertThat(JobAnatomy.shuffles(sorted.queryExecution().executedPlan())).hasSize(2)
        assertThat(JobAnatomy.stageCount(sorted.queryExecution().executedPlan())).isEqualTo(3)
    }

    @Test
    fun `building the report runs no Spark job`() {
        val (report, stats) = Jobs.measure(spark) { SettlementReport.build(payments) }
        assertThat(report.columns()).containsExactly("merchant_id", "total_cents")
        assertThat(stats.jobs).describedAs("jobs started while only building the report").isZero()
    }

    @Test
    fun `the report runs one job of two stages, as the model and the plan predicted`() {
        val inputPartitions = payments.rdd().getNumPartitions()
        assertThat(inputPartitions).isEqualTo(4)
        val report = SettlementReport.build(payments)
        val plan = report.queryExecution().executedPlan()

        val (_, ran) = Jobs.measure(spark) { report.collectAsList() }

        val model = StageModel.stages(listOf(Read("payments", inputPartitions), Narrow("captured only"), Wide("total per merchant", 4)))
        assertThat(ran.jobs).isEqualTo(1)
        assertThat(ran.stageTasks).isEqualTo(model.map { it.tasks })                 // [4, 4]
        assertThat(JobAnatomy.stageCount(plan)).isEqualTo(ran.stages)
        assertThat(JobAnatomy.taskCount(plan, inputPartitions)).isEqualTo(ran.tasks)  // 8
    }

    @Test
    fun `the report sums captured payments per merchant`() {
        val expected = rows.filter { it.status == "CAPTURED" }.groupBy { it.merchantId }.mapValues { (_, ps) -> ps.sumOf { it.amountCents } }
        val actual = SettlementReport.build(payments).collectAsList().associate { it.getInt(0) to it.getLong(1) }
        assertThat(actual).isEqualTo(expected)
    }
}
