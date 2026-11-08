package sfz.msg.l07.demo;

import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.errors.WakeupException;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * Writes 30 payments to "payments", then runs a poll loop in the group "ledger" for 4 seconds.
 * After each poll it prints the position of every partition; after each commit, the committed offsets.
 * Another thread stops the loop with wakeup().
 */
public class PollLoopDemo {
    public static void main(String[] args) throws Exception {
        try (var producer = new KafkaProducer<String, String>(Map.of("bootstrap.servers", "localhost:9092",
                "key.serializer", StringSerializer.class, "value.serializer", StringSerializer.class))) {
            for (int i = 0; i < 30; i++) {
                producer.send(new ProducerRecord<>("payments", "acct-" + i % 10, "pay-" + i));
            }
        }

        var consumer = new KafkaConsumer<String, String>(Map.of(
                "bootstrap.servers", "localhost:9092",
                "key.deserializer", StringDeserializer.class,
                "value.deserializer", StringDeserializer.class,
                "group.id", "ledger",
                "enable.auto.commit", false,       // we commit ourselves, after processing
                "auto.offset.reset", "earliest",   // a group with no committed offset starts at the beginning
                "max.poll.records", 10));
        var stopper = Executors.newSingleThreadScheduledExecutor();
        stopper.schedule(consumer::wakeup, 4, TimeUnit.SECONDS);  // the only call that is safe from another thread

        try (consumer) {
            consumer.subscribe(List.of("payments"));
            for (int n = 1; ; n++) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
                Map<Integer, Long> positions = new TreeMap<>();
                for (TopicPartition tp : consumer.assignment()) positions.put(tp.partition(), consumer.position(tp));
                System.out.printf("poll %d: %2d records   positions %s%n", n, records.count(), positions);
                if (records.isEmpty()) continue;

                records.forEach(r -> { /* apply the payment here */ });

                consumer.commitSync();             // commits the positions: the next offset of every partition
                Map<Integer, Long> committed = new TreeMap<>();
                consumer.committed(consumer.assignment())
                        .forEach((tp, om) -> committed.put(tp.partition(), om == null ? null : om.offset()));
                System.out.printf("        committed %s%n", committed);
            }
        } catch (WakeupException e) {
            System.out.println("wakeup(): the loop stops and the consumer closes");
        } finally {
            stopper.shutdown();
        }
    }
}
