package sfz.kafka.l01.demo;

import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.errors.TopicExistsException;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

import java.time.Duration;
import java.time.LocalTime;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;

/** Appends 100 payments to a one-partition topic, then reads 5 of them back starting at offset 50. */
public class ReadFromOffsetDemo {
    static final String TOPIC = "payment-events";
    static final String BOOTSTRAP = "localhost:9092"; // env/kafka.yml

    public static void main(String[] args) throws Exception {
        // 1. make sure the topic exists: one partition, so one log
        try (Admin admin = Admin.create(Map.of("bootstrap.servers", BOOTSTRAP))) {
            admin.createTopics(List.of(new NewTopic(TOPIC, 1, (short) 1))).all().get();
        } catch (ExecutionException e) {
            if (!(e.getCause() instanceof TopicExistsException)) throw e;
        }

        // 2. append 100 records; the broker answers each one with the offset it got
        String sentAt = LocalTime.now().truncatedTo(ChronoUnit.SECONDS).toString();
        try (var producer = new KafkaProducer<String, String>(Map.of(
                "bootstrap.servers", BOOTSTRAP,
                "key.serializer", StringSerializer.class,
                "value.serializer", StringSerializer.class))) {
            List<Future<RecordMetadata>> acks = new ArrayList<>();
            for (int i = 0; i < 100; i++) {
                acks.add(producer.send(new ProducerRecord<>(TOPIC, "acct-" + (i % 7), "payment-" + i + " sent at " + sentAt)));
            }
            long first = acks.get(0).get().offset();
            long last = acks.get(99).get().offset();
            System.out.printf("appended 100 records at offsets %d..%d%n", first, last);
        }

        // 3. read 5 records starting at offset 50: no group, just assign and seek
        TopicPartition tp = new TopicPartition(TOPIC, 0);
        try (var consumer = new KafkaConsumer<String, String>(Map.of(
                "bootstrap.servers", BOOTSTRAP,
                "key.deserializer", StringDeserializer.class,
                "value.deserializer", StringDeserializer.class))) {
            consumer.assign(List.of(tp));
            consumer.seek(tp, 50);
            System.out.println("reading from offset 50:");
            List<ConsumerRecord<String, String>> got = new ArrayList<>();
            while (got.size() < 5) {
                for (ConsumerRecord<String, String> r : consumer.poll(Duration.ofMillis(500))) {
                    if (got.size() < 5) got.add(r);
                }
            }
            for (ConsumerRecord<String, String> r : got) {
                System.out.printf("  offset %d  key %s  value %s%n", r.offset(), r.key(), r.value());
            }
            System.out.printf("end offset of the partition: %d%n", consumer.endOffsets(List.of(tp)).get(tp));
        }
    }
}
