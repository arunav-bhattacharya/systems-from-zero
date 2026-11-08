package sfz.batch.l07.demo

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.broadcast
import org.apache.spark.sql.functions.sum

/**
 * Joins 1,000,000 payments with 500 merchants three ways and prints, for each, the join node in
 * the plan, what the scheduler ran, the shuffle traffic and the time.
 */
fun main() {
    val spark = demoSpark()
    val log = StageLog(spark)
    val payments = payments(spark)
    val merchants = merchants(spark)
    fun query(join: Dataset<Row>) = join.groupBy("merchant_name").agg(sum("amount_cents").alias("total"))
    val cases = listOf(
        "broadcast (default, merchants < 10 MB)" to { query(payments.join(merchants, "merchant_id")) },
        "sort-merge (broadcasting turned off)" to {
            spark.conf().set("spark.sql.autoBroadcastJoinThreshold", "-1")
            query(payments.join(merchants, "merchant_id"))
        },
        "shuffled hash (SHUFFLE_HASH hint)" to { query(payments.join(merchants.hint("shuffle_hash"), "merchant_id")) },
        "broadcast hint, threshold still off" to { query(payments.join(broadcast(merchants), "merchant_id")) },
    )
    for ((label, build) in cases) {
        // a new DataFrame for every run: running the same one again would reuse its shuffle files
        build().collectAsList()                                    // warm-up
        val best = (1..3).minOf {
            val df = build()
            val t0 = System.nanoTime()
            df.collectAsList()
            (System.nanoTime() - t0) / 1e6
        }
        val df = build()
        val (jobs, stages) = log.run { df.collectAsList() }
        println(label)
        planLines(df, "Join", "Exchange").forEach { println("  $it") }
        println("  ran: %d job(s), tasks per stage %s, shuffle wrote %,d records (%,d bytes), best of 3: %.0f ms".format(
            jobs.size, stages.map { it.tasks }, stages.sumOf { it.recordsWritten }, stages.sumOf { it.bytesWritten }, best))
    }
    spark.stop()
}
