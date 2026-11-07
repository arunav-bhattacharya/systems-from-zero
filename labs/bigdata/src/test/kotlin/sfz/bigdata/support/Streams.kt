package sfz.bigdata.support

import org.apache.spark.sql.Encoders
import org.apache.spark.sql.Row
import org.apache.spark.sql.RowFactory
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.execution.streaming.runtime.MemoryStream
import org.apache.spark.sql.streaming.StreamingQuery
import org.apache.spark.sql.types.DataTypes
import org.apache.spark.sql.types.StructType
import scala.jdk.javaapi.CollectionConverters
import java.sql.Timestamp
import java.time.Instant

/**
 * Helpers for streaming tests. A [MemoryStream] is a source the test fills by hand: every
 * [send] becomes the input of the next micro-batch, so a test decides exactly which events arrive
 * together and in what order. No Kafka needed.
 */
object Streams {
    /** One authorization event: which merchant, and when the card was used. */
    val AUTHORIZATION_SCHEMA: StructType = StructType()
        .add("merchant_id", DataTypes.IntegerType, false)
        .add("event_time", DataTypes.TimestampType, false)

    /** A new, empty in-memory stream of authorizations. `toDF()` gives the streaming DataFrame. */
    fun authorizations(spark: SparkSession): MemoryStream<Row> = MemoryStream.apply(spark, Encoders.row(AUTHORIZATION_SCHEMA))

    /** 10:03 on 2026-11-07, UTC, from "10:03" (or "10:03:30"). */
    fun at(time: String): Instant = Instant.parse("2026-11-07T$time${if (time.length == 5) ":00" else ""}Z")

    /** Adds one batch of events for [merchant], at the given times. */
    fun MemoryStream<Row>.send(vararg times: String, merchant: Int = 7) {
        val rows: List<Row> = times.map { RowFactory.create(merchant, Timestamp.from(at(it))) }
        addData(CollectionConverters.asScala(rows.toMutableList()))
    }

    /** Runs every batch the source has, then returns the watermark the query reports (epoch if none yet). */
    fun StreamingQuery.drain(): Instant {
        processAllAvailable()
        val wm = lastProgress()?.eventTime()?.get("watermark")
        return if (wm == null) Instant.EPOCH else Instant.parse(wm)
    }

    /** Rows the stateful operator dropped as too late, summed over every batch so far. */
    fun StreamingQuery.droppedByWatermark(): Long =
        recentProgress().sumOf { p -> p.stateOperators().sumOf { it.numRowsDroppedByWatermark() } }
}
