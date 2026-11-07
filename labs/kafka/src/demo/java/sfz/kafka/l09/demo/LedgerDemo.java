package sfz.kafka.l09.demo;

import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.OffsetAndMetadata;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

import java.time.Duration;
import java.util.*;

/**
 * A ledger service reads six payments from a new topic and writes one ledger entry per payment to another. Instance 1
 * crashes after writing four entries, before it commits; instance 2 takes over from the committed offset.
 * Argument: "plain" (the default: a normal producer, then commitSync) or "txn" (entries and offsets in one transaction).
 */
public class LedgerDemo {
    static final String BOOTSTRAP = "localhost:9092";
    static String group;

    public static void main(String[] args) throws Exception {
        boolean txn = args.length > 0 && args[0].equals("txn");
        long run = System.currentTimeMillis() % 100_000;
        TopicPartition input = new TopicPartition("payments-" + run, 0);
        TopicPartition output = new TopicPartition("ledger-entries-" + run, 0);
        try (var admin = Admin.create(Map.<String, Object>of("bootstrap.servers", BOOTSTRAP))) {
            admin.createTopics(List.of(new NewTopic(input.topic(), 1, (short) 1), new NewTopic(output.topic(), 1, (short) 1))).all().get();
        }
        try (var p = producer(null)) {
            for (int i = 0; i < 6; i++) p.send(new ProducerRecord<>(input.topic(), 0, "acct-" + i, "pay-" + i)).get();
        }

        group = "ledger-" + run;
        String txnId = "ledger-" + run + "-0";   // one transactional.id per input partition this instance owns

        // instance 1: four entries reach the broker, then the process dies: no commit, no abort, no close
        var c1 = consumer(input);
        var p1 = producer(txn ? txnId : null);
        if (txn) {
            p1.initTransactions();
            p1.beginTransaction();
        }
        for (ConsumerRecord<String, String> r : pollAll(c1, 6).subList(0, 4))
            p1.send(new ProducerRecord<>(output.topic(), 0, r.key(), "entry:" + r.value())).get();
        System.out.println("instance 1: wrote entries for pay-0 .. pay-3" + (txn ? " inside a transaction" : "") + ", then crashed before committing");

        // instance 2: same group (and, for txn, the same transactional.id), starts from the committed offset
        try (var c2 = consumer(input); var p2 = producer(txn ? txnId : null)) {
            if (txn) {
                p2.initTransactions();   // aborts what instance 1 left open, and fences instance 1
                System.out.println("instance 2: initTransactions() aborted instance 1's open transaction");
                p2.beginTransaction();
            }
            System.out.println("instance 2: starts at offset " + c2.position(input));
            List<ConsumerRecord<String, String>> records = pollAll(c2, 6);
            long last = -1;
            for (ConsumerRecord<String, String> r : records) {
                p2.send(new ProducerRecord<>(output.topic(), 0, r.key(), "entry:" + r.value()));
                last = r.offset();
            }
            Map<TopicPartition, OffsetAndMetadata> next = Map.of(input, new OffsetAndMetadata(last + 1));
            if (txn) {
                p2.sendOffsetsToTransaction(next, c2.groupMetadata());   // the bookmark rides in the transaction
                p2.commitTransaction();
            } else {
                p2.flush();
                c2.commitSync(next);
            }
            System.out.println("instance 2: wrote entries for pay-0 .. pay-5, committed offset " + (last + 1));
        }

        for (String isolation : List.of("read_uncommitted", "read_committed")) {
            List<String> values = readAll(output, isolation);
            Map<String, Integer> counts = new TreeMap<>();
            for (String v : values) counts.merge(v.replace("entry:", ""), 1, Integer::sum);
            System.out.printf("%-16s reader sees %2d entries: %s%n", isolation, values.size(), counts);
        }
    }

    /** Polls until n records have arrived: a first poll on a fresh broker can come back empty. */
    static List<ConsumerRecord<String, String>> pollAll(KafkaConsumer<String, String> c, int n) {
        List<ConsumerRecord<String, String>> records = new ArrayList<>();
        while (records.size() < n) c.poll(Duration.ofSeconds(1)).forEach(records::add);
        return records;
    }

    static KafkaProducer<String, String> producer(String txnId) {
        Map<String, Object> config = new HashMap<>(Map.of("bootstrap.servers", BOOTSTRAP,
                "key.serializer", StringSerializer.class, "value.serializer", StringSerializer.class));
        if (txnId != null) config.put("transactional.id", txnId);
        return new KafkaProducer<>(config);
    }

    static KafkaConsumer<String, String> consumer(TopicPartition input) {
        var c = new KafkaConsumer<String, String>(Map.of("bootstrap.servers", BOOTSTRAP, "group.id", group,
                "enable.auto.commit", false, "auto.offset.reset", "earliest", "isolation.level", "read_committed",
                "key.deserializer", StringDeserializer.class, "value.deserializer", StringDeserializer.class));
        c.assign(List.of(input));
        return c;
    }

    static List<String> readAll(TopicPartition tp, String isolation) {
        long end;   // the log end; a read_committed reader gets there once no transaction is open
        try (var c = new KafkaConsumer<String, String>(Map.of("bootstrap.servers", BOOTSTRAP,
                "key.deserializer", StringDeserializer.class, "value.deserializer", StringDeserializer.class))) {
            end = c.endOffsets(List.of(tp)).get(tp);
        }
        try (var c = new KafkaConsumer<String, String>(Map.of("bootstrap.servers", BOOTSTRAP, "isolation.level", isolation,
                "key.deserializer", StringDeserializer.class, "value.deserializer", StringDeserializer.class))) {
            c.assign(List.of(tp));
            c.seekToBeginning(List.of(tp));
            List<String> values = new ArrayList<>();
            long deadline = System.nanoTime() + 10_000_000_000L;
            while (c.position(tp) < end && System.nanoTime() < deadline)
                c.poll(Duration.ofMillis(200)).forEach(r -> values.add(r.value()));
            return values;
        }
    }
}
