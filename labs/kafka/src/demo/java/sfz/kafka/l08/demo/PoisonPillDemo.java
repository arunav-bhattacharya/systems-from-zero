package sfz.kafka.l08.demo;

import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.OffsetAndMetadata;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.errors.RecordDeserializationException;
import org.apache.kafka.common.serialization.Deserializer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Writes six payment amounts to a new one-partition topic; the third, "12x50", is not a number. Then a consumer that
 * restarts after every failure tries to get past it, three times.
 * Argument: "process" (the default: the handler parses the value and throws) or "deserialize" (the value
 * deserializer throws, inside poll; on the last try the consumer seeks past the bad record).
 */
public class PoisonPillDemo {
    /** Reads a payment amount in cents, "4000", from a record value. Throws on anything else. */
    public static class AmountDeserializer implements Deserializer<Long> {
        @Override
        public Long deserialize(String topic, byte[] data) {
            return Long.parseLong(new String(data));
        }
    }

    public static void main(String[] args) throws Exception {
        boolean inDeserializer = args.length > 0 && args[0].equals("deserialize");
        String topic = "poison-" + System.currentTimeMillis() % 100_000;   // a new topic every run
        TopicPartition tp = new TopicPartition(topic, 0);
        try (var admin = Admin.create(Map.<String, Object>of("bootstrap.servers", "localhost:9092"))) {
            admin.createTopics(List.of(new NewTopic(topic, 1, (short) 1))).all().get();
        }
        try (var p = new KafkaProducer<String, String>(Map.of("bootstrap.servers", "localhost:9092",
                "key.serializer", StringSerializer.class, "value.serializer", StringSerializer.class))) {
            for (String v : List.of("1000", "2500", "12x50", "4000", "990", "7000")) p.send(new ProducerRecord<>(topic, 0, "acct-7", v)).get();
        }

        Map<String, Object> config = Map.of(
                "bootstrap.servers", "localhost:9092", "group.id", "ledger-" + topic,
                "enable.auto.commit", false, "auto.offset.reset", "earliest");
        for (int attempt = 1; attempt <= 3; attempt++) {
            // every attempt is a fresh consumer, as after a crash and a restart: it starts at the committed offset
            if (inDeserializer) {
                try (var c = new KafkaConsumer<>(config, new StringDeserializer(), new AmountDeserializer())) {
                    c.assign(List.of(tp));
                    while (c.position(tp) < 6) {
                        try {
                            ConsumerRecords<String, Long> records = c.poll(Duration.ofSeconds(1));
                            for (ConsumerRecord<String, Long> r : records)
                                System.out.println("try " + attempt + ": offset " + r.offset() + " applied " + r.value() + " cents");
                            if (!records.isEmpty()) c.commitSync(Map.of(tp, new OffsetAndMetadata(c.position(tp))));
                        } catch (RecordDeserializationException e) {
                            System.out.println("try " + attempt + ": poll threw " + e.getClass().getSimpleName() + " at offset " + e.offset()
                                    + " (" + e.getCause() + "); position stays " + c.position(tp));
                            if (attempt < 3) break;              // crash: the next try starts at the committed offset
                            c.seek(tp, e.offset() + 1);          // the only way past it: skip the record
                            c.commitSync(Map.of(tp, new OffsetAndMetadata(e.offset() + 1)));
                            System.out.println("try " + attempt + ": seek to " + (e.offset() + 1) + ": offset " + e.offset()
                                    + " is skipped, and nobody will see it again");
                        }
                    }
                }
            } else {
                try (var c = new KafkaConsumer<>(config, new StringDeserializer(), new StringDeserializer())) {
                    c.assign(List.of(tp));
                    try {
                        while (c.position(tp) < 6) {
                            ConsumerRecords<String, String> records = c.poll(Duration.ofSeconds(1));
                            for (ConsumerRecord<String, String> r : records) {
                                long cents = Long.parseLong(r.value());   // the handler: throws NumberFormatException on 12x50
                                System.out.println("try " + attempt + ": offset " + r.offset() + " applied " + cents + " cents");
                            }
                            if (!records.isEmpty()) c.commitSync(Map.of(tp, new OffsetAndMetadata(c.position(tp))));   // after the whole batch
                        }
                    } catch (NumberFormatException e) {
                        System.out.println("try " + attempt + ": crashed: " + e + "; no commit");
                    }
                }
            }
        }
        long committed;
        try (var c = new KafkaConsumer<>(config, new StringDeserializer(), new StringDeserializer())) {
            OffsetAndMetadata om = c.committed(Set.of(tp)).get(tp);
            committed = om == null ? 0 : om.offset();
        }
        System.out.println("committed offset " + committed + " of 6: lag " + (6 - committed));
    }
}
