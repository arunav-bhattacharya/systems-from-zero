package sfz.batch.l07.demo

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.max
import org.apache.spark.sql.functions.min
import org.apache.spark.sql.functions.spark_partition_id

/**
 * Five ways to change the partitions of 1,000,000 payments (4 input partitions). For each one it
 * prints the plan node that does it, how many jobs ran, and what ended up in each partition.
 */
fun main() {
    val spark = demoSpark()
    val log = StageLog(spark)
    val p = payments(spark)
    val cases = listOf<Pair<String, Dataset<Row>>>(
        "groupBy(merchant_id).count()" to p.groupBy("merchant_id").count(),
        "orderBy(amount_cents)" to p.orderBy("amount_cents"),
        "repartition(4)" to p.repartition(4),
        "repartition(4, merchant_id)" to p.repartition(4, col("merchant_id")),
        "coalesce(2)" to p.coalesce(2),
    )
    for ((label, df) in cases) {
        val node = planLines(df, "Exchange", "Coalesce").firstOrNull() ?: "no Exchange"
        val (jobs, stages) = log.run { df.foreachPartition { rows: Iterator<Row> -> rows.forEach { _ -> } } }
        val perPartition = df.withColumn("p", spark_partition_id()).groupBy("p").count().orderBy("p").collectAsList()
        println(label)
        println("  plan:  $node")
        println("  ran:   ${jobs.size} job(s), tasks per stage ${stages.map { it.tasks }}")
        println("  rows per partition: ${perPartition.map { "%,d".format(it.getLong(1)) }}")
        if (label.startsWith("orderBy")) {
            val ranges = df.withColumn("p", spark_partition_id()).groupBy("p")
                .agg(min("amount_cents"), max("amount_cents")).orderBy("p").collectAsList()
            println("  amounts per partition: ${ranges.map { "${it.getLong(1)}..${it.getLong(2)}" }}")
        }
    }
    spark.stop()
}
