package sfz.stream.l08.demo

import org.apache.spark.sql.Encoders
import org.apache.spark.sql.Row
import org.apache.spark.sql.RowFactory
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.execution.streaming.runtime.MemoryStream
import org.apache.spark.sql.streaming.StreamingQuery
import org.apache.spark.sql.types.DataTypes
import org.apache.spark.sql.types.StructType
import scala.jdk.javaapi.CollectionConverters
import java.io.File
import java.sql.Timestamp
import java.time.Instant

/** Everything the demos of lesson stream-08 write goes under build/l11. */
val DEMO_DIR = File("build/l11")

/** A quiet local SparkSession with an Iceberg Hadoop catalog `lake` under build/l11/warehouse. */
fun demoSpark(): SparkSession {
    DEMO_DIR.deleteRecursively()
    DEMO_DIR.mkdirs()
    return SparkSession.builder()
        .appName("sfz-demo")
        .master("local[2]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.lake", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.lake.type", "hadoop")
        .config("spark.sql.catalog.lake.warehouse", File(DEMO_DIR, "warehouse").absolutePath)
        .getOrCreate()
        .also { it.sparkContext().setLogLevel("ERROR") }
}

/** One authorization: which merchant, and when the card was used (event time). */
val AUTHORIZATIONS: StructType = StructType()
    .add("merchant_id", DataTypes.IntegerType, false)
    .add("event_time", DataTypes.TimestampType, false)

/** A source the demo fills by hand: each [send] is the input of the next micro-batch. */
fun authorizations(spark: SparkSession): MemoryStream<Row> = MemoryStream.apply(spark, Encoders.row(AUTHORIZATIONS))

/** 10:03 (or 10:03:30) on 2026-11-07, UTC. */
fun at(time: String): Instant = Instant.parse("2026-11-07T$time${if (time.length == 5) ":00" else ""}Z")

/** Adds one batch of authorizations for merchant 7. */
fun MemoryStream<Row>.send(vararg times: String) {
    val rows: List<Row> = times.map { RowFactory.create(7, Timestamp.from(at(it))) }
    addData(CollectionConverters.asScala(rows.toMutableList()))
}

/** The watermark the query reports after its last batch, as HH:mm (or HH:mm:ss). */
fun StreamingQuery.watermark(): String {
    val wm = lastProgress()?.eventTime()?.get("watermark") ?: return "none"
    return Instant.parse(wm).toString().substring(11, 19).removeSuffix(":00").let { if (it.startsWith("00:00")) "none" else it }
}
