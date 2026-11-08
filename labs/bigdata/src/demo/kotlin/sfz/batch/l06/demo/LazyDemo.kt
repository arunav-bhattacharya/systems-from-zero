package sfz.batch.l06.demo

import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.sum

/** Builds a query step by step and shows that nothing runs until the action at the end. */
fun main() {
    val spark = demoSpark("local[4]")
    spark.conf().set("spark.sql.adaptive.enabled", "false")      // the plain model; lesson 8 turns AQE back on
    demoPayments(spark)                                            // writes the files on the first run
    val log = JobLog(spark)
    log.clear()

    fun <T> step(label: String, block: () -> T): T {
        val t0 = System.nanoTime()
        val result = block()
        println("%-32s %7.1f ms   so far: %s".format(label, (System.nanoTime() - t0) / 1e6, log.summary()))
        return result
    }
    val payments = step("read the Parquet files") { spark.read().parquet("build/l05/payments") }
    val captured = step("where(status = CAPTURED)") { payments.where(col("status").equalTo("CAPTURED")) }
    val euros = step("withColumn(amount_eur)") { captured.withColumn("amount_eur", col("amount_cents").divide(100)) }
    val totals = step("groupBy(merchant_id).agg(sum)") { euros.groupBy("merchant_id").agg(sum("amount_eur").alias("total_eur")) }
    step("collect()  <- the action") { totals.collectAsList() }
    println()
    totals.explain("extended")
    spark.stop()
}
