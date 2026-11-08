package sfz.batch.l08.demo

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.explode
import org.apache.spark.sql.functions.lit
import org.apache.spark.sql.functions.pmod
import org.apache.spark.sql.functions.sequence
import org.apache.spark.sql.functions.sum

/**
 * A million payments, 30% of them for merchant 7, joined with 500 merchants by sort-merge join
 * into 16 reduce partitions. Four ways to run it, and for each one the shuffle records every join
 * task fetched.
 */
fun main() {
    val spark = demoSpark()
    spark.conf().set("spark.sql.autoBroadcastJoinThreshold", "-1")       // force the sort-merge join
    spark.conf().set("spark.sql.shuffle.partitions", "16")
    spark.conf().set("spark.sql.adaptive.coalescePartitions.enabled", "false") // show the skew effect alone
    val log = TaskLog(spark)
    val payments = demoPayments(spark, "skewed", hotMerchant = 7)
    val merchants = demoMerchants(spark)

    fun plain(): Dataset<Row> = payments.join(merchants, "merchant_id")
    fun salted(buckets: Long): Dataset<Row> =
        payments.withColumn("salt", pmod(col("payment_id"), lit(buckets)))
            .join(merchants.withColumn("salt", explode(sequence(lit(0L), lit(buckets - 1)))), arrayOf("merchant_id", "salt"))
            .drop("salt")

    val cases = listOf(
        Triple("AQE off", mapOf("spark.sql.adaptive.enabled" to "false"), ::plain),
        Triple("AQE on, default thresholds", mapOf("spark.sql.adaptive.enabled" to "true"), ::plain),
        Triple("AQE on, thresholds scaled down", mapOf(
            "spark.sql.adaptive.enabled" to "true",
            "spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes" to "1MB",
            "spark.sql.adaptive.advisoryPartitionSizeInBytes" to "256KB"), ::plain),
        Triple("salted, 8 buckets, AQE off", mapOf("spark.sql.adaptive.enabled" to "false")) { salted(8) },
    )
    for ((label, conf, build) in cases) {
        conf.forEach { (k, v) -> spark.conf().set(k, v) }
        val df = build().groupBy("merchant_name").agg(sum("amount_cents"))
        val (_, stages) = log.run { df.collectAsList() }
        // the join stage is the one whose tasks fetched the most shuffle records
        val join = stages.values.maxBy { it.sum() }.sorted()
        val skew = planLines(df.queryExecution().executedPlan(), "SortMergeJoin").first().substringBefore(" [").replace(Regex("""^\*\(\d+\) """), "")
        println("%-31s %-25s %2d join tasks, records fetched: median %,6d, max %,7d (%.1fx)"
            .format(label, skew, join.size, join[join.size / 2], join.last(), join.last().toDouble() / join[join.size / 2]))
    }
    spark.stop()
}
