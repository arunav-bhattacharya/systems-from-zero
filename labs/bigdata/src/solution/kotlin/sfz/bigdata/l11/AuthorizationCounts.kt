package sfz.bigdata.l11

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.window
import org.apache.spark.sql.streaming.StreamingQuery
import java.io.File

object AuthorizationCounts {

    fun perWindow(events: Dataset<Row>): Dataset<Row> =
        events
            // the watermark must be on the same column the window uses, and come before the aggregation
            .withWatermark("event_time", "10 minutes")
            .groupBy(window(col("event_time"), "5 minutes"), col("merchant_id"))
            .count()
            .select(
                col("window.start").alias("window_start"),
                col("window.end").alias("window_end"),
                col("merchant_id"),
                col("count").alias("authorizations"),
            )

    fun start(counts: Dataset<Row>, table: String, checkpoint: File): StreamingQuery =
        counts.writeStream()
            .format("iceberg")
            // append: a window is written once, after the watermark passes its end, and never changes
            .outputMode("append")
            // offsets, commit log and window state live here, so a restart carries on where it stopped
            .option("checkpointLocation", checkpoint.absolutePath)
            // every micro-batch is one Iceberg commit, tagged with the query id and batch id
            .toTable(table)
}
