package sfz.batch.l07

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.execution.exchange.ShuffleExchangeExec
import org.apache.spark.sql.execution.joins.BroadcastHashJoinExec
import org.apache.spark.sql.execution.joins.SortMergeJoinExec
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.concat
import org.apache.spark.sql.functions.lit
import org.apache.spark.sql.functions.spark_partition_id
import org.apache.spark.sql.functions.sum
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
class ShuffleTest {
    // AQE off, and broadcasting off, like a cluster whose planner thinks every table is big
    private val spark: SparkSession = LocalSpark.isolated(
        "spark.sql.adaptive.enabled" to "false",
        "spark.sql.autoBroadcastJoinThreshold" to "-1",
    )
    private val dir: File = Files.createTempDirectory("l06 shuffle").toFile()
    private val rows: List<Payment> = TestData.payments(20_000)
    private val payments: Dataset<Row> = TestData.paymentsParquet(spark, rows, File(dir, "payments"), files = 4)
    private val merchants: Dataset<Row> = spark.range(0, 500).select(
        col("id").cast("int").alias("merchant_id"),
        concat(lit("Merchant "), col("id")).alias("merchant_name"),
        col("id").mod(20).plus(5_000).cast("int").alias("mcc"),
    )

    @AfterAll
    fun cleanUp() {
        dir.deleteRecursively()
    }

    /** Runs [action] with [meter] (yours, fresh by default) registered, and returns the meter. */
    private fun metered(meter: ShuffleMeter = ShuffleMeter(), action: () -> Unit): ShuffleMeter {
        val bus = spark.sparkContext().listenerBus()
        bus.waitUntilEmpty()
        spark.sparkContext().addSparkListener(meter)
        try {
            action()
            bus.waitUntilEmpty()
        } finally {
            spark.sparkContext().removeSparkListener(meter)
        }
        return meter
    }

    private fun shuffles(df: Dataset<Row>) = Plans.nodes(df).filterIsInstance<ShuffleExchangeExec>()

    @Test
    fun `the meter sees no shuffle when every step is narrow`() {
        val meter = metered { payments.repartition(2).collectAsList() }
        assertThat(meter.recordsWritten).describedAs("records a repartition wrote").isPositive()
        meter.reset()
        metered(meter) { payments.where(col("amount_cents").gt(100_000)).select("payment_id").collectAsList() }
        assertThat(meter.recordsWritten).isZero()
        assertThat(meter.bytesWritten).isZero()
        assertThat(meter.bytesRead).isZero()
    }

    @Test
    fun `the meter counts every row a repartition moves, and reduce tasks read back what map tasks wrote`() {
        val meter = metered { payments.repartition(8).collectAsList() }
        assertThat(meter.recordsWritten).isEqualTo(20_000L)
        assertThat(meter.recordsRead).isEqualTo(20_000L)
        assertThat(meter.bytesWritten).isPositive()
        assertThat(meter.bytesRead).isEqualTo(meter.bytesWritten)
    }

    @Test
    fun `a groupBy shuffles one partial sum per merchant per map task, not one row per payment`() {
        val totals = payments.groupBy("merchant_id").agg(sum("amount_cents"))
        var stats: sfz.bigdata.support.RunStats? = null
        val meter = metered { stats = Jobs.measure(spark) { totals.collectAsList() }.second }
        // each of the 4 map tasks sends one (merchant, partial sum) row per merchant it saw
        val pairs = payments.select(spark_partition_id().alias("p"), col("merchant_id")).distinct().count()
        assertThat(meter.recordsWritten).isEqualTo(pairs)
        assertThat(meter.recordsWritten).isLessThan(20_000L / 5)
        // your meter agrees with the totals Spark keeps per stage
        assertThat(meter.recordsWritten).isEqualTo(stats!!.shuffleRecordsWritten)
        assertThat(meter.bytesWritten).isEqualTo(stats!!.shuffleBytesWritten)
    }

    @Test
    fun `enrich broadcasts the merchants even when Spark thinks they are too big`() {
        val plain = payments.join(merchants, "merchant_id")
        assertThat(Plans.nodes(plain).filterIsInstance<SortMergeJoinExec>()).describedAs("the slow plan").hasSize(1)

        val enriched = Joins.enrich(payments, merchants)
        assertThat(Plans.nodes(enriched).filterIsInstance<BroadcastHashJoinExec>()).hasSize(1)
        assertThat(Plans.nodes(enriched).filterIsInstance<SortMergeJoinExec>()).isEmpty()
        assertThat(shuffles(enriched)).describedAs("Exchange nodes in the plan").isEmpty()
        val out = enriched.select("payment_id", "merchant_id", "merchant_name").collectAsList()
        assertThat(out).hasSize(20_000)
        assertThat(out).allSatisfy { assertThat(it.getString(2)).isEqualTo("Merchant ${it.getInt(1)}") }
    }

    @Test
    fun `the broadcast join moves no payment through a shuffle, the sort-merge join moves all of them`() {
        val sortMerge = metered { payments.join(merchants, "merchant_id").collectAsList() }
        val broadcast = metered { Joins.enrich(payments, merchants).collectAsList() }
        assertThat(sortMerge.recordsWritten).isEqualTo(20_000L + 500L)     // both sides, every row
        assertThat(broadcast.recordsWritten).isZero()
    }

    @Test
    fun `fewer merges partitions without a shuffle and writes fewer files`() {
        val eight = TestData.paymentsParquet(spark, rows, File(dir, "eight"), files = 8)
        val two = Layout.fewer(eight, 2)
        assertThat(two.rdd().getNumPartitions()).isEqualTo(2)
        assertThat(shuffles(two)).isEmpty()
        val out = File(dir, "fewer")
        val meter = metered { two.write().mode("overwrite").parquet(out.absolutePath) }
        assertThat(out.listFiles { f -> f.name.endsWith(".parquet") }!!).hasSize(2)
        assertThat(meter.recordsWritten).isZero()
    }

    @Test
    fun `even spreads lopsided partitions into equal ones`() {
        // partition 0 keeps 10,000 rows, the other three about 500 each
        val lopsided = spark.range(0, 100_000, 1, 4).where(col("id").lt(10_000).or(col("id").mod(50).equalTo(0)))
            .withColumnRenamed("id", "payment_id")
        val spread = Layout.even(lopsided, 4)
        assertThat(shuffles(spread).map { it.outputPartitioning().toString() }).singleElement().asString().startsWith("RoundRobinPartitioning")
        val sizes = spread.groupBy(spark_partition_id()).count().collectAsList().map { it.getLong(1) }
        assertThat(sizes).hasSize(4)
        assertThat(sizes.max() - sizes.min()).isLessThanOrEqualTo(4L)
    }

    @Test
    fun `byKey keeps each merchant in one partition, so the groupBy after it needs no second shuffle`() {
        val byMerchant = Layout.byKey(payments, "merchant_id", 4)
        val placements = byMerchant.select(col("merchant_id"), spark_partition_id().alias("p")).distinct()
            .groupBy("merchant_id").count().where(col("count").gt(1)).count()
        assertThat(placements).describedAs("merchants found in more than one partition").isZero()
        val totals = byMerchant.groupBy("merchant_id").agg(sum("amount_cents"))
        assertThat(shuffles(totals)).describedAs("Exchange nodes: only the one byKey added").hasSize(1)
        assertThat(totals.count()).isEqualTo(rows.map { it.merchantId }.distinct().size.toLong())
    }
}
