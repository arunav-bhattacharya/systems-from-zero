package sfz.batch.l08.demo

import org.apache.spark.sql.functions.col

/**
 * Joins a million payments with the few flagged ones on card_id. Spark's estimate for the
 * filtered side is megabytes; the real size is a few kilobytes. With AQE off, Spark keeps the
 * sort-merge join it planned. With AQE on, it re-plans after the first stages and broadcasts.
 */
fun main() {
    val spark = demoSpark()
    // this laptop table is 14 MB, not 14 GB: shrink the broadcast threshold from 10 MB to 1 MB to match
    spark.conf().set("spark.sql.autoBroadcastJoinThreshold", "1MB")
    val log = TaskLog(spark)
    val payments = demoPayments(spark)
    val flagged = payments.where(col("amount_cents").gt(249_900)).select(col("card_id"), col("payment_id").alias("flagged_payment"))
    println("planner's size estimate for the flagged side: ${flagged.queryExecution().optimizedPlan().stats().simpleString()}")
    println("rows it really has: ${flagged.count()}")
    for (aqe in listOf(false, true)) {
        spark.conf().set("spark.sql.adaptive.enabled", aqe.toString())
        fun query() = payments.join(flagged, "card_id").groupBy("card_country").count()
        query().collectAsList()                                   // warm-up
        val df = query()
        val t0 = System.nanoTime()
        val (jobs, stages) = log.run { df.collectAsList() }
        val ms = (System.nanoTime() - t0) / 1e6
        println()
        println("AQE ${if (aqe) "on" else "off"}: %d job(s), tasks per stage %s, shuffle write %,d bytes, %.0f ms"
            .format(jobs, stages.values.map { it.size }, log.bytesWritten(), ms))
        val plan = df.queryExecution().executedPlan()
        if (aqe) {
            val text = clean(plan)
            val final = text.substringAfter("== Final Plan ==").substringBefore("== Initial Plan ==")
            val initial = text.substringAfter("== Initial Plan ==")
            println("  initial plan: " + planLines(initial, "Join").joinToString())
            println("  final plan:")
            planLines(final, "Join", "QueryStage", "AQEShuffleRead", "Exchange").forEach { println("    $it") }
        } else {
            planLines(plan, "Join", "Exchange").forEach { println("  $it") }
        }
    }
    spark.stop()
}
