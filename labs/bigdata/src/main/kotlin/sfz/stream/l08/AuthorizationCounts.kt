package sfz.stream.l08

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.streaming.StreamingQuery
import java.io.File

/** A fraud-velocity feed: card authorizations per merchant per 5 minutes of event time. */
object AuthorizationCounts {

    /**
     * From a stream of authorizations with columns `merchant_id INT` and `event_time TIMESTAMP`,
     * counts authorizations per merchant per 5-minute tumbling window of `event_time`, accepting
     * events up to 10 minutes late (a watermark on `event_time`).
     *
     * Returns the columns `window_start`, `window_end` (both TIMESTAMP), `merchant_id` and
     * `authorizations` (BIGINT).
     */
    fun perWindow(events: Dataset<Row>): Dataset<Row> {
        TODO("withWatermark, then groupBy(window(...), merchant_id).count(), then flatten the window struct")
    }

    /**
     * Starts [counts] as a streaming query that writes each window once, when it is final
     * (append mode), into the existing Iceberg table [table] (`format("iceberg")`, then
     * `toTable(...)`), keeping its offsets and state in [checkpoint].
     */
    fun start(counts: Dataset<Row>, table: String, checkpoint: File): StreamingQuery {
        TODO("counts.writeStream().format(\"iceberg\").outputMode(...).option(\"checkpointLocation\", ...).toTable(table)")
    }
}
