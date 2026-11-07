package sfz.bigdata.l07.demo

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.count
import org.apache.spark.sql.functions.sum
import java.io.File

/**
 * When cache() pays and when it doesn't. Two reports run over a shared intermediate result, with and
 * without a cache: first a cheap one (a filtered Parquet scan), then an expensive one (totals per
 * card: a shuffle of a million rows).
 */
fun main() {
    val spark = demoSpark()
    val path = File("build/l07/payments").absolutePath
    demoPayments(spark)

    fun ms(block: () -> Unit): Double { val t0 = System.nanoTime(); block(); return (System.nanoTime() - t0) / 1e6 }
    fun best(block: () -> Unit) = (1..3).minOf { ms(block) }

    // the shared result is rebuilt by a function, so each call is a new DataFrame with the same plan
    fun compare(label: String, shared: () -> Dataset<Row>, reports: (Dataset<Row>) -> Unit) {
        reports(shared())                                                    // warm-up
        val plain = best { reports(shared()) }
        val cached = shared().cache()
        val fill = ms { cached.count() }                                     // the first action fills the cache
        val fromCache = best { reports(shared()) }                           // same plan: the cache manager swaps it in
        val plan = planLines(shared().groupBy().count().queryExecution().executedPlan(), "InMemoryTableScan").firstOrNull() ?: "(no cache in plan)"
        val info = spark.sparkContext().getRDDStorageInfo().single()
        println(label)
        println("  two reports without cache: %6.0f ms".format(plain))
        println("  filling the cache:         %6.0f ms  (%,d bytes in memory, %d partitions)".format(fill, info.memSize(), info.numCachedPartitions()))
        println("  two reports from the cache:%6.0f ms  plan reads: %s".format(fromCache, plan))
        cached.unpersist(true)
    }

    compare("cheap: captured payments, a filtered Parquet scan (%,d bytes of files)".format(
        File(path).listFiles { f -> f.name.endsWith(".parquet") }!!.sumOf { it.length() }),
        { spark.read().parquet(path).where(col("status").equalTo("CAPTURED")) },
    ) { df ->
        df.groupBy("merchant_id").agg(sum("amount_cents")).collectAsList()
        df.groupBy("card_country").count().collectAsList()
    }

    compare("expensive: totals per card, a groupBy over a million cards",
        { spark.read().parquet(path).groupBy("card_id").agg(sum("amount_cents").alias("total"), count("*").alias("n")) },
    ) { df ->
        df.where(col("n").gt(2)).count()
        df.orderBy(col("total").desc()).limit(5).collectAsList()
    }
    spark.stop()
}
