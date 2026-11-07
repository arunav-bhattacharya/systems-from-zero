package sfz.bigdata.l11.demo

import org.apache.spark.sql.RowFactory
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.date_format
import org.apache.spark.sql.functions.window
import org.apache.spark.sql.types.DataTypes
import org.apache.spark.sql.types.StructType
import java.sql.Timestamp
import java.time.Duration

/**
 * Merchant 7 gets one authorization every 20 seconds from 10:00 to 10:30. The fraud consumer is
 * down from 10:10 to 10:20; when it comes back it reads the backlog in about a minute. Counts per
 * 5 minutes, once by arrival (processing time) and once by when the card was used (event time).
 */
fun main() {
    val spark = demoSpark()
    val outageStart = at("10:10")
    val outageEnd = at("10:20")
    val rows = (0 until 90).map { i ->
        val eventTime = at("10:00").plusSeconds(20L * i)
        val arrival = if (!eventTime.isBefore(outageStart) && eventTime.isBefore(outageEnd)) {
            // the backlog: 10 minutes of events read back in 1 minute, in order
            outageEnd.plusMillis(Duration.between(outageStart, eventTime).toMillis() / 10)
        } else {
            eventTime.plusSeconds(2)                                        // normally a 2-second lag
        }
        RowFactory.create(7, Timestamp.from(eventTime), Timestamp.from(arrival))
    }
    val schema = StructType().add("merchant_id", DataTypes.IntegerType)
        .add("event_time", DataTypes.TimestampType).add("arrival_time", DataTypes.TimestampType)
    val events = spark.createDataFrame(rows, schema)

    fun countBy(column: String) = events.groupBy(window(col(column), "5 minutes")).count()
        .select(date_format(col("window.start"), "HH:mm").alias("w"), col("count"))
        .collectAsList().associate { it.getString(0) to it.getLong(1) }
    val byArrival = countBy("arrival_time")
    val byEvent = countBy("event_time")
    println("window   by arrival time   by event time")
    for (w in (byArrival.keys + byEvent.keys).sorted()) {
        println("%-8s %10d %17d".format(w, byArrival[w] ?: 0, byEvent[w] ?: 0))
    }
    println("events: ${rows.size}; rule \"more than 30 in 5 minutes\" fires on arrival time: " +
        byArrival.filterValues { it > 30 }.keys + ", on event time: " + byEvent.filterValues { it > 30 }.keys)
    spark.stop()
}
