package sfz.bigdata.l11.demo

import org.apache.spark.api.java.function.VoidFunction2
import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.date_format
import org.apache.spark.sql.functions.window
import java.io.File
import java.time.Duration
import java.util.concurrent.ConcurrentLinkedQueue

/**
 * The same windowed count with a 10-minute watermark, run as three queries side by side: in
 * append, update and complete mode. After each of four batches, prints what each mode writes,
 * and at the end how many late events each one dropped.
 */
fun main() {
    val spark = demoSpark()
    val modes = listOf("append", "update", "complete")
    val inputs = modes.associateWith { authorizations(spark) }
    val written = modes.associateWith { ConcurrentLinkedQueue<String>() }
    val queries = modes.associateWith { mode ->
        inputs.getValue(mode).toDF()
            .withWatermark("event_time", "10 minutes")
            .groupBy(window(col("event_time"), "5 minutes"))
            .count()
            .select(date_format(col("window.start"), "HH:mm").alias("start"), col("count"))
            .writeStream()
            .outputMode(mode)
            .option("checkpointLocation", File(DEMO_DIR, "modes-$mode").absolutePath)
            .foreachBatch(VoidFunction2<Dataset<Row>, Long> { df, _ ->
                df.collectAsList().forEach { written.getValue(mode) += "${it.getString(0)}=${it.getLong(1)}" }
            })
            .start()
    }
    val batches = listOf(listOf("10:01", "10:06"), listOf("10:02", "10:14"), listOf("10:21"), listOf("10:23", "10:04"))
    var latest = at("00:00")
    for ((i, b) in batches.withIndex()) {
        // the watermark after this batch: the latest event time so far minus 10 minutes, the same in every mode
        latest = maxOf(latest, b.maxOf(::at))
        println("batch ${i + 1}: sent ${b.joinToString(" ")}; watermark after it ${latest.minus(Duration.ofMinutes(10)).toString().substring(11, 16)}")
        for (mode in modes) {
            inputs.getValue(mode).send(*b.toTypedArray())
            queries.getValue(mode).processAllAvailable()
            val out = generateSequence { written.getValue(mode).poll() }.toList().sorted()
            println("   %-8s writes %s".format(mode, out.ifEmpty { listOf("nothing") }.joinToString(" ")))
        }
    }
    for (mode in modes) {
        val dropped = queries.getValue(mode).recentProgress().sumOf { p -> p.stateOperators().sumOf { it.numRowsDroppedByWatermark() } }
        println("late events dropped by $mode mode: $dropped")
    }
    queries.values.forEach { it.stop() }
    spark.stop()
}
