package sfz.kafka.l04.demo;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

import java.time.Duration;
import java.util.*;
import java.util.concurrent.Future;

/**
 * Sends 1,000 payments for acct-1 .. acct-10 in turn to the topic "accounts", then reads them back with one consumer.
 * Each value starts with its send order (seq). Pass a mode: keys (the default), no-keys or ignore-keys.
 */
public class KeyOrderDemo {
    static final String TOPIC = "accounts";

    public static void main(String[] args) throws Exception {
        String mode = args.length > 0 ? args[0] : "keys";
        Map<String, Object> common = Map.of("bootstrap.servers", "localhost:9092",
                "key.deserializer", StringDeserializer.class, "value.deserializer", StringDeserializer.class);
        Map<String, Object> producerConfig = new HashMap<>(Map.of("bootstrap.servers", "localhost:9092",
                "key.serializer", StringSerializer.class, "value.serializer", StringSerializer.class));
        if (mode.equals("ignore-keys")) producerConfig.put("partitioner.ignore.keys", true);

        // 1. note where every partition ends now, so we read back only this run's records
        Map<TopicPartition, Long> start;
        try (var consumer = new KafkaConsumer<String, String>(common)) {
            List<TopicPartition> tps = consumer.partitionsFor(TOPIC).stream()
                    .map(p -> new TopicPartition(TOPIC, p.partition())).toList();
            start = consumer.endOffsets(tps);
        }

        // 2. send seq 0..999; the key cycles through the 10 accounts (or is null)
        List<Integer> sentTo = new ArrayList<>();
        try (var producer = new KafkaProducer<String, String>(producerConfig)) {
            List<Future<RecordMetadata>> acks = new ArrayList<>();
            for (int seq = 0; seq < 1000; seq++) {
                String key = mode.equals("no-keys") ? null : "acct-" + (seq % 10 + 1);
                acks.add(producer.send(new ProducerRecord<>(TOPIC, key, seq + "," + "x".repeat(80))));
            }
            for (Future<RecordMetadata> ack : acks) sentTo.add(ack.get().partition());
        }
        System.out.printf("mode %s: 1000 records to %s (%d partitions)%n", mode, TOPIC, start.size());
        System.out.println("in send order: " + runs(sentTo));

        // 3. read them back from where this run started, in the order the consumer hands them out
        List<ConsumerRecord<String, String>> seen = new ArrayList<>();
        try (var consumer = new KafkaConsumer<String, String>(common)) {
            consumer.assign(start.keySet());
            start.forEach(consumer::seek);
            long deadline = System.nanoTime() + Duration.ofSeconds(15).toNanos();
            while (seen.size() < 1000 && System.nanoTime() < deadline) {
                consumer.poll(Duration.ofMillis(500)).forEach(seen::add);
            }
        }

        // 4. per key: which partitions, and did the consumer see that key's records in send order?
        Map<String, SortedSet<Integer>> partitions = new TreeMap<>(Comparator.comparingInt(k -> Integer.parseInt(k.substring(5))));
        Map<String, Integer> lastSeq = new HashMap<>();
        Set<String> outOfOrder = new HashSet<>();
        for (var r : seen) {
            if (r.key() == null) continue;
            partitions.computeIfAbsent(r.key(), k -> new TreeSet<>()).add(r.partition());
            int seq = seq(r);
            Integer prev = lastSeq.put(r.key(), seq);
            if (prev != null && seq < prev) outOfOrder.add(r.key());
        }
        partitions.forEach((key, ps) -> System.out.printf("  %-8s partitions %-14s in send order: %s%n",
                key, ps, outOfOrder.contains(key) ? "no" : "yes"));

        // 5. and the stream as a whole?
        for (int i = 1; i < seen.size(); i++) {
            if (seq(seen.get(i)) < seq(seen.get(i - 1))) {
                System.out.printf("whole stream: out of send order at read #%d (seq %d came right after seq %d)%n",
                        i, seq(seen.get(i)), seq(seen.get(i - 1)));
                return;
            }
        }
        System.out.println("whole stream: in send order");
    }

    static int seq(ConsumerRecord<String, String> r) {
        return Integer.parseInt(r.value().substring(0, r.value().indexOf(',')));
    }

    /** "p3 x153, p0 x152, ..." : how many records in a row went to the same partition. */
    static String runs(List<Integer> partitions) {
        List<String> out = new ArrayList<>();
        int count = 1;
        for (int i = 1; i <= partitions.size(); i++) {
            if (i < partitions.size() && partitions.get(i).equals(partitions.get(i - 1))) {
                count++;
            } else {
                out.add("p" + partitions.get(i - 1) + " x" + count);
                count = 1;
            }
        }
        String shown = String.join(", ", out.subList(0, Math.min(8, out.size())));
        return shown + (out.size() > 8 ? ", ..." : "") + " (" + out.size() + " runs)";
    }
}
