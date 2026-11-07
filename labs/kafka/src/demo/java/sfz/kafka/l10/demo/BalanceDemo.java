package sfz.kafka.l10.demo;

import org.apache.kafka.common.serialization.LongDeserializer;
import org.apache.kafka.common.serialization.LongSerializer;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;
import org.apache.kafka.common.utils.Bytes;
import org.apache.kafka.streams.KeyValue;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.Topology;
import org.apache.kafka.streams.TopologyTestDriver;
import org.apache.kafka.streams.kstream.Consumed;
import org.apache.kafka.streams.kstream.Materialized;
import org.apache.kafka.streams.kstream.Produced;
import org.apache.kafka.streams.state.KeyValueIterator;
import org.apache.kafka.streams.state.KeyValueStore;

import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

/**
 * A running balance per account: the payments stream folded into a table. Runs in TopologyTestDriver, so it needs
 * no broker: the driver pushes each record through the topology and keeps what it writes.
 */
public class BalanceDemo {
    public static void main(String[] args) {
        StreamsBuilder builder = new StreamsBuilder();
        builder.stream("payments", Consumed.with(Serdes.String(), Serdes.Long()))     // KStream: one record per payment
                .groupByKey()
                .aggregate(() -> 0L, (account, amount, balance) -> balance + amount,  // KTable: one row per account
                        Materialized.<String, Long, KeyValueStore<Bytes, byte[]>>as("balances")
                                .withKeySerde(Serdes.String()).withValueSerde(Serdes.Long()))
                .toStream()                                                           // the table's changes, as a stream
                .to("balances", Produced.with(Serdes.String(), Serdes.Long()));
        Topology topology = builder.build();
        System.out.println(topology.describe());

        Properties props = new Properties();
        props.put(StreamsConfig.APPLICATION_ID_CONFIG, "balance-demo");
        props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "unused:9092");   // the driver never connects
        props.put(StreamsConfig.STATE_DIR_CONFIG, "build/streams-state");
        props.put(StreamsConfig.STATESTORE_CACHE_MAX_BYTES_CONFIG, 0);      // show every update (section 2 explains)
        try (var driver = new TopologyTestDriver(topology, props)) {
            var payments = driver.createInputTopic("payments", new StringSerializer(), new LongSerializer());
            var balances = driver.createOutputTopic("balances", new StringDeserializer(), new LongDeserializer());
            String[] accounts = {"acct-1", "acct-2", "acct-1", "acct-1"};
            long[] amounts = {10_000, 5_000, -3_000, 500};
            for (int i = 0; i < accounts.length; i++) {
                payments.pipeInput(accounts[i], amounts[i]);
                KeyValue<String, Long> out = balances.readKeyValue();
                System.out.printf("payment %s %8s  ->  balances: %s = %s%n", accounts[i], money(amounts[i], true), out.key, money(out.value, false));
            }
            var changelog = driver.createOutputTopic("balance-demo-balances-changelog", new StringDeserializer(), new LongDeserializer());
            List<String> entries = new ArrayList<>();
            for (KeyValue<String, Long> kv : changelog.readKeyValuesToList()) entries.add(kv.key + "=" + money(kv.value, false));
            System.out.println("changelog topic balance-demo-balances-changelog: " + String.join(", ", entries));
            KeyValueStore<String, Long> store = driver.getKeyValueStore("balances");
            List<String> rows = new ArrayList<>();
            try (KeyValueIterator<String, Long> it = store.all()) {
                it.forEachRemaining(kv -> rows.add(kv.key + "=" + money(kv.value, false)));
            }
            System.out.println("store 'balances': " + String.join(", ", rows));
        }
    }

    static String money(long cents, boolean signed) {
        return String.format(signed ? "%+.2f" : "%.2f", cents / 100.0);
    }
}
