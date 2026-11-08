package sfz.stream.l05.demo;

import org.apache.kafka.common.serialization.LongSerializer;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;
import org.apache.kafka.common.utils.Bytes;
import org.apache.kafka.streams.KeyValue;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.TopologyTestDriver;
import org.apache.kafka.streams.kstream.Consumed;
import org.apache.kafka.streams.kstream.Materialized;
import org.apache.kafka.streams.kstream.Produced;
import org.apache.kafka.streams.kstream.TimeWindows;
import org.apache.kafka.streams.state.WindowStore;

import java.time.Duration;
import java.time.Instant;
import java.util.Properties;

/**
 * Debits per account in one-minute tumbling windows with a 30-second grace period, run in TopologyTestDriver.
 * Every record carries its own event time; two of them arrive late.
 */
public class WindowDemo {
    public static void main(String[] args) {
        StreamsBuilder builder = new StreamsBuilder();
        builder.stream("payments", Consumed.with(Serdes.String(), Serdes.Long()))
                .filter((account, amount) -> amount < 0)                                   // debits only
                .groupByKey()
                .windowedBy(TimeWindows.ofSizeAndGrace(Duration.ofMinutes(1), Duration.ofSeconds(30)))
                .count(Materialized.<String, Long, WindowStore<Bytes, byte[]>>as("debits"))
                .toStream()
                .filter((w, count) -> count > 3)                                           // the rule: more than 3 a minute
                .map((w, count) -> KeyValue.pair(w.key(), count + " debits in " + w.window().startTime() + "/" + w.window().endTime()))
                .to("fraud-alerts", Produced.with(Serdes.String(), Serdes.String()));

        Properties props = new Properties();
        props.put(StreamsConfig.APPLICATION_ID_CONFIG, "fraud-demo");
        props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "unused:9092");
        props.put(StreamsConfig.STATE_DIR_CONFIG, "build/streams-state");
        props.put(StreamsConfig.STATESTORE_CACHE_MAX_BYTES_CONFIG, 0);
        try (var driver = new TopologyTestDriver(builder.build(), props)) {
            var payments = driver.createInputTopic("payments", new StringSerializer(), new LongSerializer());
            var alerts = driver.createOutputTopic("fraud-alerts", new StringDeserializer(), new StringDeserializer());
            WindowStore<String, Long> store = driver.getWindowStore("debits");
            Instant streamTime = Instant.EPOCH;
            System.out.println("#  account  event time  stream time  window       count");
            String[][] arrivals = {{"acct-7", "10:00:05"}, {"acct-7", "10:00:20"}, {"acct-7", "10:00:40"}, {"acct-7", "10:00:55"},
                    {"acct-3", "10:01:10"}, {"acct-7", "10:00:50"}, {"acct-3", "10:01:45"}, {"acct-7", "10:00:58"}};
            for (int i = 0; i < arrivals.length; i++) {
                String account = arrivals[i][0], time = arrivals[i][1];
                Instant at = Instant.parse("2026-11-07T" + time + "Z");
                Instant windowStart = at.minusSeconds(at.getEpochSecond() % 60);
                long before = count(store, account, windowStart);
                payments.pipeInput(account, -2_500L, at);
                if (at.isAfter(streamTime)) streamTime = at;                                // stream time only moves forward
                long after = count(store, account, windowStart);
                String note = after == before ? "  dropped: the window closed at " + hms(windowStart.plusSeconds(90))
                        : !alerts.isEmpty() ? "  ALERT " + alerts.readValue() : "";
                System.out.printf("%-2d %-8s %-11s %-12s %s-%s  %d%s%n", i + 1, account, time, hms(streamTime),
                        hms(windowStart).substring(0, 5), hms(windowStart.plusSeconds(60)).substring(0, 5), after, note);
            }
            Object dropped = driver.metrics().entrySet().stream().filter(e -> e.getKey().name().equals("dropped-records-total"))
                    .findFirst().orElseThrow().getValue().metricValue();
            System.out.println("dropped-records-total = " + dropped);
        }
    }

    static long count(WindowStore<String, Long> store, String account, Instant windowStart) {
        Long n = store.fetch(account, windowStart.toEpochMilli());
        return n == null ? 0 : n;
    }

    static String hms(Instant t) {
        return t.toString().substring(11, 19);
    }
}
