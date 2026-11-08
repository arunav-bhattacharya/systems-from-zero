package sfz.stream.l05.demo;

import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.config.ConfigResource;
import org.apache.kafka.common.serialization.LongSerializer;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.common.serialization.StringSerializer;
import org.apache.kafka.common.utils.Bytes;
import org.apache.kafka.streams.CloseOptions;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.KeyValue;
import org.apache.kafka.streams.StoreQueryParameters;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.Topology;
import org.apache.kafka.streams.kstream.Consumed;
import org.apache.kafka.streams.kstream.Materialized;
import org.apache.kafka.streams.kstream.Produced;
import org.apache.kafka.streams.processor.StateRestoreListener;
import org.apache.kafka.streams.state.KeyValueIterator;
import org.apache.kafka.streams.state.KeyValueStore;
import org.apache.kafka.streams.state.QueryableStoreTypes;
import org.apache.kafka.streams.state.ReadOnlyKeyValueStore;

import java.io.File;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * The balance app on a real broker. Run 1 folds 1,000 payments for 10 accounts into the store "balances" and
 * stops. Then the demo deletes the app's local state directory, as if the instance moved to a machine with an
 * empty disk, and run 2 starts: Kafka Streams rebuilds the store from the changelog topic before it processes
 * anything. Argument "eos" runs both with processing.guarantee=exactly_once_v2.
 */
public class RestoreDemo {
    static final String BOOTSTRAP = "localhost:9092";

    public static void main(String[] args) throws Exception {
        boolean eos = args.length > 0 && args[0].equals("eos");
        long run = System.currentTimeMillis() % 100_000;
        String payments = "payments-" + run, balances = "balances-" + run, appId = "balance-" + run;
        try (var admin = Admin.create(Map.<String, Object>of("bootstrap.servers", BOOTSTRAP))) {
            admin.createTopics(List.of(new NewTopic(payments, 1, (short) 1), new NewTopic(balances, 1, (short) 1))).all().get();
            try (var p = new KafkaProducer<>(Map.<String, Object>of("bootstrap.servers", BOOTSTRAP), new StringSerializer(), new LongSerializer())) {
                for (int i = 0; i < 1000; i++) p.send(new ProducerRecord<>(payments, 0, "acct-" + i % 10, (i % 7 - 3) * 1_000L));
            }
            File stateDir = new File("build/streams-state");
            StreamsConfig config = new StreamsConfig(Map.<String, Object>of(
                    StreamsConfig.APPLICATION_ID_CONFIG, appId,              // also the group id and the prefix of internal topics
                    StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, BOOTSTRAP,
                    StreamsConfig.STATE_DIR_CONFIG, stateDir.getPath(),      // where RocksDB keeps the store on local disk
                    StreamsConfig.PROCESSING_GUARANTEE_CONFIG, eos ? StreamsConfig.EXACTLY_ONCE_V2 : StreamsConfig.AT_LEAST_ONCE,
                    StreamsConfig.STATESTORE_CACHE_MAX_BYTES_CONFIG, 0,      // no record cache: every update reaches the changelog
                    "auto.offset.reset", "earliest"));

            runApp("run 1", topology(payments, balances), config);
            String changelog = appId + "-balances-changelog";
            String policy = admin.describeConfigs(List.of(new ConfigResource(ConfigResource.Type.TOPIC, changelog))).all().get()
                    .values().iterator().next().get("cleanup.policy").value();
            System.out.println("changelog topic " + changelog + " has cleanup.policy=" + policy);
            File local = new File(stateDir, appId + "/0_0/rocksdb/balances");
            System.out.println("local store: " + local.getPath() + ", " + local.listFiles().length + " files");
            File appDir = new File(stateDir, appId);
            deleteRecursively(appDir);
            System.out.println("deleted " + appDir.getPath() + ": the local copy is gone");
            runApp("run 2", topology(payments, balances), config);
        }
    }

    static Topology topology(String payments, String balances) {
        StreamsBuilder builder = new StreamsBuilder();
        builder.stream(payments, Consumed.with(Serdes.String(), Serdes.Long()))
                .groupByKey()
                .aggregate(() -> 0L, (account, amount, balance) -> balance + amount,
                        Materialized.<String, Long, KeyValueStore<Bytes, byte[]>>as("balances")
                                .withKeySerde(Serdes.String()).withValueSerde(Serdes.Long()))
                .toStream()
                .to(balances, Produced.with(Serdes.String(), Serdes.Long()));
        return builder.build();
    }

    /** What the store must hold once all 1,000 payments are in: the sum of each account's payments, in cents. */
    static Map<String, Long> expected() {
        Map<String, Long> sums = new HashMap<>();
        for (int i = 0; i < 1000; i++) sums.merge("acct-" + i % 10, (i % 7 - 3) * 1_000L, Long::sum);
        return sums;
    }

    /** Starts the app, waits until all 1,000 payments are in the store, prints two balances and stops. */
    static void runApp(String label, Topology topology, StreamsConfig config) throws InterruptedException {
        KafkaStreams streams = new KafkaStreams(topology, config);
        streams.setGlobalStateRestoreListener(new StateRestoreListener() {
            public void onRestoreStart(TopicPartition tp, String store, long start, long end) {
                System.out.println(label + ": restoring store '" + store + "' from " + tp + ", offsets " + start + " to " + end);
            }
            public void onBatchRestored(TopicPartition tp, String store, long batchEnd, long restored) {
            }
            public void onRestoreEnd(TopicPartition tp, String store, long total) {
                System.out.println(label + ": restored " + total + " records");
            }
        });
        streams.start();
        Map<String, Long> expected = expected(), balances = new HashMap<>();
        long deadline = System.nanoTime() + 120_000_000_000L;
        while (!balances.equals(expected) && System.nanoTime() < deadline) {
            Thread.sleep(200);
            balances = new HashMap<>();
            try {
                ReadOnlyKeyValueStore<String, Long> store = streams.store(
                        StoreQueryParameters.fromNameAndType("balances", QueryableStoreTypes.keyValueStore()));
                try (KeyValueIterator<String, Long> it = store.all()) {
                    while (it.hasNext()) {
                        KeyValue<String, Long> kv = it.next();
                        balances.put(kv.key, kv.value);
                    }
                }
            } catch (Exception e) {
                // not running yet, or still restoring
            }
        }
        System.out.println(label + ": " + balances.size() + " accounts in the store, acct-0 = " + balances.get("acct-0")
                + " cents, acct-1 = " + balances.get("acct-1") + " cents");
        // a clean shutdown that leaves the group at once, so run 2 doesn't wait for run 1's session to time out
        streams.close(CloseOptions.groupMembershipOperation(CloseOptions.GroupMembershipOperation.LEAVE_GROUP));
    }

    static void deleteRecursively(File f) {
        File[] children = f.listFiles();
        if (children != null) for (File c : children) deleteRecursively(c);
        f.delete();
    }
}
