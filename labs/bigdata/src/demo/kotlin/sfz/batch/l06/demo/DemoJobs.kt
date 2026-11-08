package sfz.batch.l06.demo

import org.apache.spark.scheduler.SparkListener
import org.apache.spark.scheduler.SparkListenerJobStart
import org.apache.spark.scheduler.SparkListenerStageCompleted
import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.array
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.element_at
import org.apache.spark.sql.functions.hash
import org.apache.spark.sql.functions.lit
import org.apache.spark.sql.functions.pmod
import java.io.File
import java.util.concurrent.CopyOnWriteArrayList

/** A quiet local SparkSession for the demos: loopback only, 4 shuffle partitions, UI off unless asked. */
fun demoSpark(master: String = "local[2]", ui: Boolean = false): SparkSession =
    SparkSession.builder()
        .appName("sfz-demo")
        .master(master)
        .config("spark.ui.enabled", ui.toString())
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
        .also { it.sparkContext().setLogLevel("ERROR") }

/** 400,000 made-up payments as 4 Parquet files under build/l05/payments, the same rows every run. */
fun demoPayments(spark: SparkSession): Dataset<Row> {
    val dir = File("build/l05/payments")
    if (!File(dir, "_SUCCESS").exists()) {
        spark.range(0, 400_000, 1, 4).select(
            col("id").alias("payment_id"),
            pmod(hash(col("id")), lit(500)).alias("merchant_id"),
            element_at(array(lit("AUTHORIZED"), lit("CAPTURED"), lit("DECLINED"), lit("REFUNDED")),
                pmod(hash(col("id"), lit(1)), lit(4)).plus(1)).alias("status"),
            pmod(hash(col("id"), lit(2)), lit(250_000)).plus(100).cast("bigint").alias("amount_cents"),
        ).write().mode(SaveMode.Overwrite).parquet(dir.absolutePath)
    }
    return spark.read().parquet(dir.absolutePath)
}

/** Records the jobs and completed stages the scheduler reports, so a demo can print them. */
class JobLog(private val spark: SparkSession) : SparkListener() {
    val jobs = CopyOnWriteArrayList<Int>()
    /** (stage id, tasks) for every stage that ran. */
    val stages = CopyOnWriteArrayList<Pair<Int, Int>>()

    init {
        spark.sparkContext().addSparkListener(this)
    }

    override fun onJobStart(jobStart: SparkListenerJobStart) {
        jobs += jobStart.jobId()
    }

    override fun onStageCompleted(stageCompleted: SparkListenerStageCompleted) {
        stages += stageCompleted.stageInfo().stageId() to stageCompleted.stageInfo().numTasks()
    }

    /** Waits until Spark has delivered every event so far, then returns a one-line summary. */
    fun summary(): String {
        spark.sparkContext().listenerBus().waitUntilEmpty()
        val done = stages.sortedBy { it.first }
        return "%d job(s), %d stage(s), %d tasks %s".format(jobs.size, done.size, done.sumOf { it.second }, done.map { it.second })
    }

    fun clear() {
        spark.sparkContext().listenerBus().waitUntilEmpty()
        jobs.clear()
        stages.clear()
    }
}
