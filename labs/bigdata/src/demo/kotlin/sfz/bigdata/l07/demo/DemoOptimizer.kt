package sfz.bigdata.l07.demo

import org.apache.spark.scheduler.SparkListener
import org.apache.spark.scheduler.SparkListenerJobStart
import org.apache.spark.scheduler.SparkListenerTaskEnd
import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.array
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.concat
import org.apache.spark.sql.functions.element_at
import org.apache.spark.sql.functions.hash
import org.apache.spark.sql.functions.lit
import org.apache.spark.sql.functions.pmod
import org.apache.spark.sql.functions.`when`
import java.io.File
import java.util.concurrent.CopyOnWriteArrayList

/** A quiet local SparkSession for the lesson 7 demos: loopback only, UTC, 4 shuffle partitions. */
fun demoSpark(): SparkSession =
    SparkSession.builder()
        .appName("sfz-demo")
        .master("local[4]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
        .also { it.sparkContext().setLogLevel("ERROR") }

/**
 * 1,000,000 made-up payments as 4 Parquet files under build/l07/[name], the same rows every run.
 * With [hotMerchant] set, 30% of them (ids ending in 00 to 29) belong to that one merchant.
 */
fun demoPayments(spark: SparkSession, name: String = "payments", hotMerchant: Int? = null): Dataset<Row> {
    val dir = File("build/l07/$name")
    if (!File(dir, "_SUCCESS").exists()) {
        val merchant = pmod(hash(col("id")), lit(500))
        spark.range(0, 1_000_000, 1, 4).select(
            col("id").alias("payment_id"),
            (if (hotMerchant == null) merchant else `when`(pmod(col("id"), lit(100)).lt(30), lit(hotMerchant)).otherwise(merchant))
                .alias("merchant_id"),
            element_at(array(lit("NL"), lit("DE"), lit("FR"), lit("GB"), lit("US"), lit("IN"), lit("BR"), lit("JP")),
                pmod(hash(col("id"), lit(1)), lit(8)).plus(1)).alias("card_country"),
            element_at(array(lit("AUTHORIZED"), lit("CAPTURED"), lit("DECLINED"), lit("REFUNDED")),
                pmod(hash(col("id"), lit(3)), lit(4)).plus(1)).alias("status"),
            pmod(hash(col("id"), lit(2)), lit(250_000)).plus(100).cast("bigint").alias("amount_cents"),
            pmod(hash(col("id"), lit(4)), lit(1_000_000)).alias("card_id"),
        ).write().mode(SaveMode.Overwrite).parquet(dir.absolutePath)
    }
    return spark.read().parquet(dir.absolutePath)
}

/** 500 merchants, one row each, with a made-up category code (mcc) from 5000 to 5019. */
fun demoMerchants(spark: SparkSession): Dataset<Row> =
    spark.range(0, 500, 1, 2).select(
        col("id").cast("int").alias("merchant_id"),
        concat(lit("Merchant "), col("id")).alias("merchant_name"),
        col("id").mod(20).plus(5_000).cast("int").alias("mcc"),
    )

/** Records jobs, and for every task its stage and the shuffle records it fetched. */
class TaskLog(private val spark: SparkSession) : SparkListener() {
    val jobs = CopyOnWriteArrayList<Int>()
    /** (stage id, shuffle records read, shuffle bytes written) per finished task. */
    val tasks = CopyOnWriteArrayList<Triple<Int, Long, Long>>()

    init {
        spark.sparkContext().addSparkListener(this)
    }

    override fun onJobStart(jobStart: SparkListenerJobStart) {
        jobs += jobStart.jobId()
    }

    override fun onTaskEnd(taskEnd: SparkListenerTaskEnd) {
        val m = taskEnd.taskMetrics() ?: return
        tasks += Triple(taskEnd.stageId(), m.shuffleReadMetrics().recordsRead(), m.shuffleWriteMetrics().bytesWritten())
    }

    /** Runs [action] and returns the jobs it started and, per stage, the shuffle records each task read. */
    fun <T> run(action: () -> T): Pair<Int, Map<Int, List<Long>>> {
        val bus = spark.sparkContext().listenerBus()
        bus.waitUntilEmpty()
        jobs.clear()
        tasks.clear()
        action()
        bus.waitUntilEmpty()
        return jobs.size to tasks.groupBy({ it.first }, { it.second }).toSortedMap()
    }

    /** Shuffle bytes written by the tasks of the last [run]. */
    fun bytesWritten(): Long = tasks.sumOf { it.third }
}

/** A plan as text, with expression ids, plan ids and the long file location cut, for printing. */
fun clean(plan: Any): String =
    plan.toString()
        .replace(Regex("""#\d+L?"""), "")
        .replace(Regex(""", \[plan_id=\d+]"""), "")
        .replace(Regex("""Location: InMemoryFileIndex\([^)]*\)\[[^\]]*]"""), "Location: ...")
        .replace(Regex("""Batched: true, DataFilters: \[[^\]]*], Format: Parquet, """), "")
        .trimEnd()

/** The lines of [df]'s physical plan that contain any of [words], cleaned and unindented. */
fun planLines(plan: Any, vararg words: String): List<String> =
    clean(plan).lines().filter { line -> words.any { it in line } }.map { it.replace(Regex("""^[\s:|+-]+"""), "") }
