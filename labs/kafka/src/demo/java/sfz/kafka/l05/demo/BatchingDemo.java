package sfz.kafka.l05.demo;

import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.kafka.common.serialization.StringSerializer;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Future;

/**
 * Sends 500 small payment events to "ledger-events" at about 1,000 a second, once per setting,
 * and prints what the producer's own metrics say about its batches.
 */
public class BatchingDemo {
    public static void main(String[] args) throws Exception {
        System.out.println("linger.ms  compression  records/request  bytes/batch  compressed/raw  batch waited (ms)");
        run(0, "none");
        run(5, "none");
        run(50, "none");
        run(50, "lz4");
    }

    static void run(int lingerMs, String compression) throws Exception {
        Map<String, Object> config = Map.of(
                "bootstrap.servers", "localhost:9092",
                "key.serializer", StringSerializer.class,
                "value.serializer", StringSerializer.class,
                "linger.ms", lingerMs,
                "compression.type", compression);
        try (var producer = new KafkaProducer<String, String>(config)) {
            List<Future<RecordMetadata>> acks = new ArrayList<>();
            for (int i = 0; i < 500; i++) {
                String event = "{\"id\":\"pay-" + i + "\",\"account\":\"acct-" + i % 50 + "\",\"amount\":4000,\"currency\":\"EUR\"}";
                acks.add(producer.send(new ProducerRecord<>("ledger-events", "acct-" + i % 50, event)));
                Thread.sleep(1); // about 1,000 records a second
            }
            for (var ack : acks) ack.get();
            System.out.printf("%9d  %-11s  %15.1f  %11.0f  %14.2f  %17.1f%n", lingerMs, compression,
                    metric(producer, "records-per-request-avg"), metric(producer, "batch-size-avg"),
                    metric(producer, "compression-rate-avg"), metric(producer, "record-queue-time-avg"));
        }
    }

    /** One value from the producer's "producer-metrics" group. */
    static double metric(KafkaProducer<String, String> producer, String name) {
        return producer.metrics().entrySet().stream()
                .filter(e -> e.getKey().group().equals("producer-metrics") && e.getKey().name().equals(name))
                .mapToDouble(e -> (Double) e.getValue().metricValue())
                .findFirst().orElseThrow();
    }
}
