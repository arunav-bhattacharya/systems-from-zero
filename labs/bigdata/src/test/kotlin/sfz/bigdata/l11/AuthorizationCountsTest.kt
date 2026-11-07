package sfz.bigdata.l11

import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.execution.streaming.runtime.MemoryStream
import org.apache.spark.sql.streaming.StreamingQuery
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.junit.jupiter.api.io.TempDir
import sfz.bigdata.support.Iceberg
import sfz.bigdata.support.Streams
import sfz.bigdata.support.Streams.at
import sfz.bigdata.support.Streams.drain
import sfz.bigdata.support.Streams.droppedByWatermark
import sfz.bigdata.support.Streams.send
import java.io.File
import java.time.Duration

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class AuthorizationCountsTest {
    private lateinit var dir: File
    private lateinit var spark: SparkSession
    private val running = mutableListOf<StreamingQuery>()

    @BeforeAll
    fun setUp(@TempDir tmp: File) {
        dir = tmp
        // an Iceberg catalog `l11` in a temp folder; no table cache, so every read sees the latest commit
        spark = Iceberg.session("l11", File(tmp, "warehouse"), "spark.sql.catalog.l11.cache-enabled" to "false")
    }

    @AfterEach
    fun stopQueries() {
        running.forEach { it.stop() }
        running.clear()
    }

    /** Creates the sink table `l11.fraud.<name>` (the first time) and starts the query with checkpoint `<tmp>/<name>`. */
    private fun start(name: String, events: MemoryStream<Row>): StreamingQuery {
        spark.sql("CREATE TABLE IF NOT EXISTS l11.fraud.$name (window_start TIMESTAMP, window_end TIMESTAMP, " +
            "merchant_id INT, authorizations BIGINT) USING iceberg")
        return AuthorizationCounts.start(AuthorizationCounts.perWindow(events.toDF()), "l11.fraud.$name", File(dir, "checkpoints/$name"))
            .also { running += it }
    }

    /** What the sink table holds: (window start as HH:mm, merchant, count), in order. */
    private fun output(name: String): List<Triple<String, Int, Long>> =
        spark.sql("SELECT window_start, window_end, merchant_id, authorizations FROM l11.fraud.$name ORDER BY window_start, merchant_id")
            .collectAsList().map { r ->
                val start = r.getTimestamp(0).toInstant()
                assertThat(r.getTimestamp(1).toInstant()).isEqualTo(start.plus(Duration.ofMinutes(5)))
                Triple(start.toString().substring(11, 16), r.getInt(2), r.getLong(3))
            }

    @Test
    fun `perWindow has the four columns, and append mode writes a window only after the watermark passes its end`() {
        val events = Streams.authorizations(spark)
        assertThat(AuthorizationCounts.perWindow(events.toDF()).columns()).containsExactly("window_start", "window_end", "merchant_id", "authorizations")
        val q = start("append", events)
        events.send("10:01", "10:02", "10:06")
        events.send("10:03", merchant = 8)
        assertThat(q.drain()).isEqualTo(at("09:56"))
        assertThat(output("append")).describedAs("nothing is final yet").isEmpty()
        events.send("10:21")
        assertThat(q.drain()).isEqualTo(at("10:11"))
        assertThat(output("append")).containsExactly(Triple("10:00", 7, 2), Triple("10:00", 8, 1), Triple("10:05", 7, 1))
    }

    @Test
    fun `a late event inside the grace period is counted and one after its window closed is dropped`() {
        val events = Streams.authorizations(spark)
        val q = start("late", events)
        events.send("10:01", "10:02", "10:06")
        events.send("10:14")
        assertThat(q.drain()).isEqualTo(at("10:04"))
        events.send("10:03")                                   // window [10:00, 10:05) is still open
        q.drain()
        events.send("10:21")                                   // watermark 10:11 closes it
        q.drain()
        events.send("10:04", "10:08")                          // both windows are closed now
        q.drain()
        assertThat(output("late")).containsExactly(Triple("10:00", 7, 3), Triple("10:05", 7, 1))
        assertThat(q.droppedByWatermark()).isEqualTo(2)
    }

    @Test
    fun `a restarted query carries on from its checkpoint without losing counts`() {
        val events = Streams.authorizations(spark)
        val first = start("restart", events)
        events.send("10:01", "10:02")
        first.drain()
        first.stop()                                           // the job dies; the open window's state is in the checkpoint
        val second = start("restart", events)                  // a new query, same checkpoint folder
        events.send("10:03", "10:21")
        second.drain()
        assertThat(output("restart")).describedAs("2 events before the restart, 1 after").containsExactly(Triple("10:00", 7, 3))
    }

    @Test
    fun `a batch replayed after a crash is not written twice`() {
        val events = Streams.authorizations(spark)
        val first = start("replay", events)
        events.send("10:01", "10:02", "10:06")
        events.send("10:21")
        first.drain()
        first.stop()
        assertThat(output("replay")).hasSize(2)
        // fake a crash after the sink committed but before Spark wrote its commit log entry
        val commits = File(dir, "checkpoints/replay/commits")
        val last = commits.list()!!.filter { !it.startsWith(".") }.maxOf { it.toInt() }
        File(commits, "$last").delete()
        File(commits, ".$last.crc").delete()
        val second = start("replay", events)
        second.drain()
        assertThat(second.recentProgress().first().batchId()).describedAs("Spark ran the last batch again").isEqualTo(last.toLong())
        assertThat(output("replay")).describedAs("the Iceberg sink skipped the batch it already had")
            .containsExactly(Triple("10:00", 7, 2), Triple("10:05", 7, 1))
    }

    @Test
    fun `the model and Spark agree on the same micro-batches`() {
        val batches = listOf(
            listOf("10:00:30", "10:07", "10:02"), listOf("10:12", "10:04"), listOf("10:19:59", "10:01"),
            listOf("10:26", "10:11", "10:16"), listOf("10:09", "10:24"), listOf("10:41"), listOf("10:30", "10:44:10", "10:29"),
        )
        val events = Streams.authorizations(spark)
        val q = start("model", events)
        val model = WindowedCounter(Duration.ofMinutes(5), Duration.ofMinutes(10))
        val emitted = mutableListOf<Triple<String, Int, Long>>()
        for (b in batches) {
            events.send(*b.toTypedArray())
            val watermark = q.drain()
            emitted += model.batch(b.map(::at)).map { Triple(it.window.start.toString().substring(11, 16), 7, it.count) }
            assertThat(watermark).describedAs("watermark after $b").isEqualTo(model.watermark)
        }
        assertThat(output("model")).isEqualTo(emitted.sortedBy { it.first })
        assertThat(q.droppedByWatermark()).isEqualTo(model.dropped)
    }
}
