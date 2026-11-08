package sfz.batch.l08

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.execution.joins.SortMergeJoinExec
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import sfz.bigdata.support.Jobs
import sfz.bigdata.support.LocalSpark
import sfz.bigdata.support.Plans
import sfz.bigdata.support.RunStats
import sfz.bigdata.support.TestData
import java.io.File
import java.nio.file.Files

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class SkewTest {
    // AQE off and broadcasting off: a plain sort-merge join, 16 reduce tasks, so one hot task stands out
    private val base = arrayOf(
        "spark.sql.adaptive.enabled" to "false",
        "spark.sql.autoBroadcastJoinThreshold" to "-1",
        "spark.sql.shuffle.partitions" to "16",
    )
    private val spark: SparkSession = LocalSpark.isolated(*base)
    private val dir: File = Files.createTempDirectory("l07 skew").toFile()
    // 40,000 payments, 30% of them for merchant 7, in 4 files
    private val payments: Dataset<Row> = TestData.paymentsParquet(spark, TestData.skewedPayments(40_000), File(dir, "payments"))
    private val merchants: Dataset<Row> = TestData.merchantsFrame(spark)

    @AfterAll
    fun cleanUp() {
        dir.deleteRecursively()
    }

    /** What the tests collect from a join: every column, so every payment column goes through the shuffle. */
    private fun out(join: Dataset<Row>): Dataset<Row> = join

    /** Runs [df] to the end and returns its rows and what the scheduler ran, with every task's shuffle reads. */
    private fun run(session: SparkSession, df: Dataset<Row>): Pair<List<Row>, RunStats> =
        Jobs.measure(session) { df.collectAsList() }

    private val plainRun: Pair<List<Row>, RunStats> by lazy { run(spark, out(SkewedJoin.plain(payments, merchants))) }

    @Test
    fun `salted returns exactly the rows of the plain join, with the same columns`() {
        val salted = SkewedJoin.salted(payments, merchants, 8)
        assertThat(salted.columns()).containsExactlyInAnyOrder(*SkewedJoin.plain(payments, merchants).columns())
        val plain = plainRun.first.map { it.getLong(it.fieldIndex("payment_id")) to it.getString(it.fieldIndex("merchant_name")) }.sortedBy { it.first }
        val mine = salted.select("payment_id", "merchant_name").collectAsList().map { it.getLong(0) to it.getString(1) }.sortedBy { it.first }
        assertThat(mine).hasSize(40_000).isEqualTo(plain)
    }

    @Test
    fun `salting spreads the hot merchant, so no task reads more than half of what the hot task read`() {
        val hot = plainRun.second.maxTaskShuffleRead
        // the plain join's hot task holds merchant 7's 12,000 payments plus its share of the rest
        assertThat(hot).describedAs("records the hottest task fetched, plain join").isGreaterThan(12_000L)
        val (_, salted) = run(spark, out(SkewedJoin.salted(payments, merchants, 8)))
        assertThat(salted.maxTaskShuffleRead).describedAs("records the hottest task fetched, salted").isLessThan(hot / 2)
    }

    @Test
    fun `with your settings AQE splits the hot partition at run time and the plain join gets faster tasks`() {
        val settings = SkewedJoin.aqeSkewSettings()
        // coalescing off in this test only, so the effect you see is the skew split and nothing else
        val aqe = LocalSpark.isolated(*base, *settings.toList().toTypedArray(), "spark.sql.adaptive.coalescePartitions.enabled" to "false")
        assertThat(aqe.conf().get("spark.sql.adaptive.enabled")).isEqualTo("true")
        val join = out(SkewedJoin.plain(aqe.read().parquet(File(dir, "payments").absolutePath), TestData.merchantsFrame(aqe)))
        val (rows, stats) = run(aqe, join)
        assertThat(rows).hasSize(40_000)
        // after the run, the plan that ran is the final adaptive plan: a sort-merge join marked as a skew join
        val smj = Plans.nodes(join).filterIsInstance<SortMergeJoinExec>().single()
        assertThat(smj.isSkewJoin()).describedAs("SortMergeJoin(skew=true) in the final plan").isTrue()
        assertThat(stats.maxTaskShuffleRead).isLessThan(plainRun.second.maxTaskShuffleRead / 2)
    }

    @Test
    fun `AQE with its default thresholds leaves the half-megabyte hot partition alone`() {
        // the defaults are sized for clusters: 256 MB. Your settings are why the test above splits.
        val defaults = LocalSpark.isolated(*base, "spark.sql.adaptive.enabled" to "true", "spark.sql.adaptive.coalescePartitions.enabled" to "false")
        val join = out(SkewedJoin.plain(defaults.read().parquet(File(dir, "payments").absolutePath), TestData.merchantsFrame(defaults)))
        val (_, stats) = run(defaults, join)
        assertThat(Plans.nodes(join).filterIsInstance<SortMergeJoinExec>().single().isSkewJoin()).isFalse()
        assertThat(stats.maxTaskShuffleRead).isEqualTo(plainRun.second.maxTaskShuffleRead)
        assertThat(SkewedJoin.aqeSkewSettings()["spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes"])
            .describedAs("your skew threshold").isNotNull()
    }
}
