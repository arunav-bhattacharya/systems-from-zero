package sfz.kafka.l09.demo;

import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Writes to a new one-partition topic with a transactional producer and a plain one, and after each step prints the
 * partition as a read_uncommitted reader and a read_committed reader see it: offsets, values, and where each stops.
 */
public class TxnDemo {
    static final String BOOTSTRAP = "localhost:9092";
    static TopicPartition tp;

    public static void main(String[] args) throws Exception {
        tp = new TopicPartition("txn-demo-" + System.currentTimeMillis() % 100_000, 0);
        try (var admin = Admin.create(Map.<String, Object>of("bootstrap.servers", BOOTSTRAP))) {
            admin.createTopics(List.of(new NewTopic(tp.topic(), 1, (short) 1))).all().get();
        }
        Map<String, Object> ser = Map.of("bootstrap.servers", BOOTSTRAP,
                "key.serializer", StringSerializer.class, "value.serializer", StringSerializer.class);
        Map<String, Object> txnConfig = new HashMap<>(ser);
        txnConfig.put("transactional.id", "txn-demo");
        var txn = new KafkaProducer<String, String>(txnConfig);
        var plain = new KafkaProducer<String, String>(ser);

        txn.initTransactions();
        txn.beginTransaction(); send(txn, "a"); send(txn, "b"); txn.commitTransaction();
        Thread.sleep(200);   // the coordinator writes the markers just after the commit returns
        show("1. transaction commits a, b");
        txn.beginTransaction(); send(txn, "c"); txn.abortTransaction();
        Thread.sleep(200);
        show("2. transaction writes c, then aborts");
        send(plain, "d");
        show("3. plain producer writes d");
        txn.beginTransaction(); send(txn, "e");
        send(plain, "f");
        show("4. transaction writes e and stays open; plain producer writes f");
        txn.commitTransaction();
        Thread.sleep(200);
        show("5. transaction commits e");
        txn.close();
        plain.close();
    }

    static void send(KafkaProducer<String, String> p, String v) throws Exception {
        p.send(new ProducerRecord<>(tp.topic(), 0, "acct-1", v)).get();
    }

    static void show(String step) {
        System.out.println(step);
        for (String isolation : List.of("read_uncommitted", "read_committed")) {
            try (var c = new KafkaConsumer<String, String>(Map.of("bootstrap.servers", BOOTSTRAP, "isolation.level", isolation,
                    "key.deserializer", StringDeserializer.class, "value.deserializer", StringDeserializer.class))) {
                c.assign(List.of(tp));
                c.seekToBeginning(List.of(tp));
                long end = c.endOffsets(List.of(tp)).get(tp);   // read_committed: the last stable offset
                List<String> seen = new ArrayList<>();
                while (c.position(tp) < end) c.poll(Duration.ofMillis(200)).forEach(r -> seen.add(r.offset() + "=" + r.value()));
                System.out.printf("  %-16s stops at %2d, sees %s%n", isolation, end, seen);
            }
        }
    }
}
