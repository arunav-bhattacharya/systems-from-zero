package sfz.kafka.l10.demo

import org.apache.kafka.common.serialization.LongSerializer
import org.apache.kafka.common.serialization.Serdes
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import org.apache.kafka.common.utils.Bytes
import org.apache.kafka.streams.KeyValue
import org.apache.kafka.streams.StreamsBuilder
import org.apache.kafka.streams.StreamsConfig
import org.apache.kafka.streams.TopologyTestDriver
import org.apache.kafka.streams.kstream.Consumed
import org.apache.kafka.streams.kstream.Materialized
import org.apache.kafka.streams.kstream.Produced
import org.apache.kafka.streams.kstream.TimeWindows
import org.apache.kafka.streams.state.WindowStore
import java.time.Duration
import java.time.Instant
import java.util.Properties

/**
 * Debits per account in one-minute tumbling windows with a 30-second grace period, run in TopologyTestDriver.
 * Every record carries its own event time; two of them arrive late.
 */
fun main() {
    val builder = StreamsBuilder()
    builder.stream("payments", Consumed.with(Serdes.String(), Serdes.Long()))
        .filter { _, amount -> amount < 0 }                                         // debits only
        .groupByKey()
        .windowedBy(TimeWindows.ofSizeAndGrace(Duration.ofMinutes(1), Duration.ofSeconds(30)))
        .count(Materialized.`as`<String, Long, WindowStore<Bytes, ByteArray>>("debits"))
        .toStream()
        .filter { _, count -> count > 3 }                                           // the rule: more than 3 a minute
        .map { w, count -> KeyValue(w.key(), "$count debits in ${w.window().startTime()}/${w.window().endTime()}") }
        .to("fraud-alerts", Produced.with(Serdes.String(), Serdes.String()))

    val props = Properties().apply {
        put(StreamsConfig.APPLICATION_ID_CONFIG, "fraud-demo")
        put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "unused:9092")
        put(StreamsConfig.STATE_DIR_CONFIG, "build/streams-state")
        put(StreamsConfig.STATESTORE_CACHE_MAX_BYTES_CONFIG, 0)
    }
    TopologyTestDriver(builder.build(), props).use { driver ->
        val payments = driver.createInputTopic("payments", StringSerializer(), LongSerializer())
        val alerts = driver.createOutputTopic("fraud-alerts", StringDeserializer(), StringDeserializer())
        val store = driver.getWindowStore<String, Long>("debits")
        var streamTime = Instant.EPOCH
        println("#  account  event time  stream time  window       count")
        val arrivals = listOf("acct-7" to "10:00:05", "acct-7" to "10:00:20", "acct-7" to "10:00:40", "acct-7" to "10:00:55",
            "acct-3" to "10:01:10", "acct-7" to "10:00:50", "acct-3" to "10:01:45", "acct-7" to "10:00:58")
        for ((i, arrival) in arrivals.withIndex()) {
            val (account, time) = arrival
            val at = Instant.parse("2026-11-07T${time}Z")
            val windowStart = at.minusSeconds(at.epochSecond % 60)
            val before = store.fetch(account, windowStart.toEpochMilli()) ?: 0L
            payments.pipeInput(account, -2_500L, at)
            if (at.isAfter(streamTime)) streamTime = at                             // stream time only moves forward
            val after = store.fetch(account, windowStart.toEpochMilli()) ?: 0L
            val note = when {
                after == before -> "  dropped: the window closed at ${hms(windowStart.plusSeconds(90))}"
                !alerts.isEmpty -> "  ALERT ${alerts.readValue()}"
                else -> ""
            }
            println("%-2d %-8s %-11s %-12s %s-%s  %d%s".format(i + 1, account, time, hms(streamTime), hms(windowStart).take(5),
                hms(windowStart.plusSeconds(60)).take(5), after, note))
        }
        val dropped = driver.metrics().entries.first { it.key.name() == "dropped-records-total" }.value.metricValue()
        println("dropped-records-total = $dropped")
    }
}

private fun hms(t: Instant) = t.toString().substring(11, 19)
