package sfz.bigdata.l11.demo

import org.apache.spark.api.java.function.VoidFunction2
import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.window
import org.apache.spark.sql.streaming.StreamingQuery
import java.io.File

/**
 * One windowed count, written by two queries with their own checkpoints: one to an Iceberg table,
 * one through foreachBatch to a plain Parquet folder (append, ignoring the batch id). Then a
 * crash is faked between "the sink wrote" and "the commit log says so", and both restart.
 */
fun main() {
    val spark = demoSpark()
    val events = authorizations(spark)
    val counts = events.toDF()
        .withWatermark("event_time", "10 minutes")
        .groupBy(window(col("event_time"), "5 minutes"), col("merchant_id"))
        .count()
        .select(col("window.start").alias("window_start"), col("merchant_id"), col("count").alias("authorizations"))
    spark.sql("CREATE TABLE lake.pay.auth_counts (window_start TIMESTAMP, merchant_id INT, authorizations BIGINT) USING iceberg")
    val icebergCheckpoint = File(DEMO_DIR, "checkpoint-iceberg")
    val folderCheckpoint = File(DEMO_DIR, "checkpoint-folder")
    val folder = File(DEMO_DIR, "auth-counts-parquet")

    fun startIceberg(): StreamingQuery = counts.writeStream().format("iceberg").outputMode("append")
        .option("checkpointLocation", icebergCheckpoint.absolutePath).toTable("lake.pay.auth_counts")
    fun startFolder(): StreamingQuery = counts.writeStream().outputMode("append")
        .option("checkpointLocation", folderCheckpoint.absolutePath)
        // a sink that is NOT idempotent: it appends whatever the batch holds, ignoring the batch id
        .foreachBatch(VoidFunction2<Dataset<Row>, Long> { df, _ -> df.write().mode("append").parquet(folder.absolutePath) })
        .start()
    fun rows(): String {
        val ice = spark.table("lake.pay.auth_counts").count()
        val par = if (folder.exists()) spark.read().parquet(folder.absolutePath).count() else 0
        return "Iceberg table $ice rows, Parquet folder $par rows"
    }
    fun logs(dir: File, name: String) = File(dir, name).list()!!.filter { !it.startsWith(".") }.map { it.toInt() }.sorted()

    var ice = startIceberg()
    var par = startFolder()
    for (b in listOf(listOf("10:01", "10:02", "10:06"), listOf("10:21"))) {
        events.send(*b.toTypedArray())
        ice.processAllAvailable()
        par.processAllAvailable()
    }
    println("before the crash: ${rows()}")
    println("checkpoint: offsets ${logs(icebergCheckpoint, "offsets")}, commits ${logs(icebergCheckpoint, "commits")}, " +
        "state/ holds ${File(icebergCheckpoint, "state").walkTopDown().count { it.isFile && it.name.endsWith(".delta") }} delta files")
    println("offsets/3 starts with: " + File(icebergCheckpoint, "offsets/3").readLines()[1].substringBefore(",\"conf\"") + "}")
    ice.stop()
    par.stop()

    // the crash: both sinks wrote batch 3, but the process died before the commit log recorded it
    for (dir in listOf(icebergCheckpoint, folderCheckpoint)) {
        val last = logs(dir, "commits").last()
        File(dir, "commits/$last").delete()
        File(dir, "commits/.$last.crc").delete()
    }
    println("deleted commits/3 in both checkpoints; restarting")
    ice = startIceberg()
    par = startFolder()
    ice.processAllAvailable()
    par.processAllAvailable()
    println("after the restart, Spark ran batch ${ice.recentProgress().first().batchId()} again: ${rows()}")
    println("Iceberg snapshots by epoch: " + spark.sql(
        "SELECT summary['spark.sql.streaming.epochId'] AS epoch, coalesce(summary['added-records'], '0') AS added " +
            "FROM lake.pay.auth_counts.snapshots ORDER BY committed_at").collectAsList().joinToString { "${it.getString(0)}:+${it.getString(1)}" })
    ice.stop()
    par.stop()
    spark.stop()
}
