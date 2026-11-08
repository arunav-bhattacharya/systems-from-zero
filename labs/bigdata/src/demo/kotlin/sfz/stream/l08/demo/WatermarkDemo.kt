package sfz.stream.l08.demo

import org.apache.spark.api.java.function.VoidFunction2
import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.date_format
import org.apache.spark.sql.functions.window
import java.io.File
import java.util.concurrent.ConcurrentLinkedQueue

/**
 * A windowed count with a 10-minute watermark, in append mode. Six batches of events arrive, some
 * out of order and late. After each one, prints the watermark, what append mode wrote, how many
 * windows the state holds and how many events were dropped as too late.
 */
fun main() {
    val spark = demoSpark()
    val events = authorizations(spark)
    val written = ConcurrentLinkedQueue<String>()
    val query = events.toDF()
        .withWatermark("event_time", "10 minutes")
        .groupBy(window(col("event_time"), "5 minutes"))
        .count()
        .select(date_format(col("window.start"), "HH:mm").alias("start"), date_format(col("window.end"), "HH:mm").alias("end"), col("count"))
        .writeStream()
        .outputMode("append")
        .option("checkpointLocation", File(DEMO_DIR, "watermark-checkpoint").absolutePath)
        // print-friendly sink: collect what each micro-batch writes
        .foreachBatch(VoidFunction2<Dataset<Row>, Long> { df, _ ->
            df.collectAsList().forEach { written += "[${it.getString(0)}, ${it.getString(1)}) = ${it.getLong(2)}" }
        })
        .start()

    var batch = 0
    fun step(vararg times: String) {
        val before = query.watermark()
        events.send(*times)
        query.processAllAvailable()
        val ops = query.recentProgress().flatMap { it.stateOperators().toList() }
        val dropped = ops.sumOf { it.numRowsDroppedByWatermark() }
        val inState = query.lastProgress().stateOperators().first().numRowsTotal()
        val out = generateSequence { written.poll() }.toList().sorted()
        println("batch ${++batch}: sent ${times.joinToString(" ")}")
        println("   watermark ${before} -> ${query.watermark()}; append wrote ${if (out.isEmpty()) "nothing" else out.joinToString()}; " +
            "windows in state: $inState; dropped so far: $dropped")
    }
    step("10:01", "10:02", "10:06")
    step("10:14")
    step("10:03")
    step("10:21")
    step("10:04", "10:08")
    step("10:13")
    query.stop()
    spark.stop()
}
