package sfz.kafka.l06.demo;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
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
 * Writes pay-00 .. pay-09 (10.00 EUR each, for acct-1) to partition 0 of "payments". Consumer 1 crashes while
 * applying pay-07; consumer 2, in the same group, carries on from the group's committed offset.
 * Arguments: "after" (commit after processing, the default) or "before", then "dedupe" (the default) or "nodedupe".
 */
public class CrashDemo {
    static final TopicPartition P0 = new TopicPartition("payments", 0);
    static final Set<String> appliedKeys = new HashSet<>();   // the ledger's idempotency keys
    static long balanceCents = 0;                             // acct-1's balance
    static long start;                                        // the offset of pay-00

    public static void main(String[] args) throws Exception {
        boolean commitFirst = args.length > 0 && args[0].equals("before");
        boolean dedupe = !(args.length > 1 && args[1].equals("nodedupe"));
        String group = "crash-demo-" + System.currentTimeMillis();   // a new group every run
        Map<String, Object> config = Map.of("bootstrap.servers", "localhost:9092", "group.id", group,
                "key.deserializer", StringDeserializer.class, "value.deserializer", StringDeserializer.class,
                "enable.auto.commit", false, "max.poll.records", 5);

        try (var producer = new KafkaProducer<String, String>(Map.of("bootstrap.servers", "localhost:9092",
                "key.serializer", StringSerializer.class, "value.serializer", StringSerializer.class))) {
            start = producer.send(new ProducerRecord<>("payments", 0, "acct-1", "pay-00")).get().offset();
            for (int i = 1; i < 10; i++) producer.send(new ProducerRecord<>("payments", 0, "acct-1", "pay-0" + i));
        }

        // consumer 1: the group's bookmark starts at pay-00; it dies while applying pay-07
        try (var c1 = new KafkaConsumer<String, String>(config)) {
            c1.assign(List.of(P0));                                         // the group.id is where commits go
            c1.commitSync(Map.of(P0, new OffsetAndMetadata(start)));
            outer:
            while (true) {
                ConsumerRecords<String, String> batch = c1.poll(Duration.ofMillis(500));
                if (commitFirst) commit(c1, batch);
                for (ConsumerRecord<String, String> r : batch) {
                    if (r.value().equals("pay-07")) {
                        System.out.println("consumer 1: CRASH while applying pay-07");
                        break outer;                                        // no commit, no clean-up: gone
                    }
                    applyPayment(r.value(), dedupe, "consumer 1");
                }
                if (!commitFirst) commit(c1, batch);
            }
        }

        // consumer 2, same group: it starts at the committed offset and reads to the end
        try (var c2 = new KafkaConsumer<String, String>(config)) {
            c2.assign(List.of(P0));
            System.out.printf("consumer 2: starts at offset %d (pay-%02d)%n", c2.position(P0), c2.position(P0) - start);
            while (c2.position(P0) < start + 10) {
                ConsumerRecords<String, String> batch = c2.poll(Duration.ofMillis(500));
                for (ConsumerRecord<String, String> r : batch) applyPayment(r.value(), dedupe, "consumer 2");
                commit(c2, batch);
            }
        }
        System.out.printf("ledger: %d of 10 payments applied, acct-1 balance %.2f EUR (should be 100.00)%n",
                appliedKeys.size(), balanceCents / 100.0);
    }

    static void applyPayment(String key, boolean dedupe, String who) {
        if (dedupe && appliedKeys.contains(key)) {
            System.out.printf("%s: %s already applied, skipped%n", who, key);
            return;
        }
        appliedKeys.add(key);       // in a database: the key's row and the balance update, in one transaction
        balanceCents += 1000;
        System.out.printf("%s: applied %s%n", who, key);
    }

    static void commit(KafkaConsumer<String, String> c, ConsumerRecords<String, String> batch) {
        if (batch.isEmpty()) return;
        List<ConsumerRecord<String, String>> records = batch.records(P0);
        long next = records.get(records.size() - 1).offset() + 1;   // the next record to read
        c.commitSync(Map.of(P0, new OffsetAndMetadata(next)));
        System.out.printf("            committed offset %d (pay-%02d is next)%n", next, next - start);
    }
}
