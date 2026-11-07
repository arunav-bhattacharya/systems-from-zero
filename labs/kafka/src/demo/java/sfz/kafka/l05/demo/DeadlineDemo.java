package sfz.kafka.l05.demo;

import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;

/**
 * Sends one payment every 500 ms for 15 seconds to "ledger-events" and prints how long each took to be
 * acknowledged, or why it failed. Pause the broker for a few seconds while it runs.
 * Arguments: "idempotent" (the default) or "plain" (idempotence off), then delivery.timeout.ms (default 10000).
 */
public class DeadlineDemo {
    public static void main(String[] args) throws Exception {
        boolean idempotent = !(args.length > 0 && args[0].equals("plain"));
        int deadlineMs = args.length > 1 ? Integer.parseInt(args[1]) : 10_000;
        TopicPartition tp = new TopicPartition("ledger-events", 0);
        Map<String, Object> consumerConfig = Map.of("bootstrap.servers", "localhost:9092",
                "key.deserializer", StringDeserializer.class, "value.deserializer", StringDeserializer.class);
        long start;
        try (var consumer = new KafkaConsumer<String, String>(consumerConfig)) {
            start = consumer.endOffsets(List.of(tp)).get(tp);             // where this run's records will begin
        }

        Map<String, Object> config = Map.of(
                "bootstrap.servers", "localhost:9092",
                "key.serializer", StringSerializer.class,
                "value.serializer", StringSerializer.class,
                "enable.idempotence", idempotent,
                "request.timeout.ms", 2_000,     // give up on one request after 2 s, then retry
                "delivery.timeout.ms", deadlineMs); // give up on the record this long after send()
        System.out.printf("idempotence %s, delivery.timeout.ms %d, request.timeout.ms 2000%n", idempotent ? "on" : "off", deadlineMs);
        try (var producer = new KafkaProducer<String, String>(config)) {
            for (int i = 0; i < 30; i++) {
                String id = String.format("pay-%02d", i);
                long sentAt = System.nanoTime();
                producer.send(new ProducerRecord<>("ledger-events", "acct-1", id), (md, e) -> {
                    long ms = (System.nanoTime() - sentAt) / 1_000_000;
                    if (e == null) System.out.printf("%s acked after %5d ms at offset %d%n", id, ms, md.offset());
                    else System.out.printf("%s FAILED after %4d ms: %s%n", id, ms, e.getClass().getSimpleName());
                });
                Thread.sleep(500);
            }
        }

        // what did the log get?
        List<String> written = new ArrayList<>();
        try (var consumer = new KafkaConsumer<String, String>(consumerConfig)) {
            consumer.assign(List.of(tp));
            consumer.seek(tp, start);
            long end = consumer.endOffsets(List.of(tp)).get(tp);
            while (consumer.position(tp) < end) consumer.poll(Duration.ofMillis(500)).forEach(r -> written.add(r.value()));
        }
        int distinct = new HashSet<>(written).size();
        System.out.printf("the log got %d records for %d different payments: %d duplicates%n",
                written.size(), distinct, written.size() - distinct);
    }
}
