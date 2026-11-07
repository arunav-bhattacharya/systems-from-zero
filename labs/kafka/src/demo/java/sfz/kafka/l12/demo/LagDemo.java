package sfz.kafka.l12.demo;

import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.admin.OffsetSpec;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.OffsetAndMetadata;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.stream.Collectors;

/**
 * Consumer lag, computed the way a monitoring tool computes it: for each partition, the log end offset minus the
 * group's committed offset. A settlement group reads 1,000 of 3,000 payments in a 3-partition topic and commits.
 */
public class LagDemo {
    static final String BOOTSTRAP = "localhost:9092";

    public static void main(String[] args) throws Exception {
        long run = System.currentTimeMillis() % 100_000;
        String topic = "payments-" + run, group = "settlement-" + run;
        try (var admin = Admin.create(Map.<String, Object>of("bootstrap.servers", BOOTSTRAP))) {
            admin.createTopics(List.of(new NewTopic(topic, 3, (short) 1))).all().get();
            try (var p = new KafkaProducer<>(Map.<String, Object>of("bootstrap.servers", BOOTSTRAP), new StringSerializer(), new StringSerializer())) {
                for (int i = 0; i < 3000; i++) p.send(new ProducerRecord<>(topic, "acct-" + i % 30, "pay-" + i));
            }
            try (var c = new KafkaConsumer<>(Map.<String, Object>of("bootstrap.servers", BOOTSTRAP, "group.id", group,
                    "group.protocol", "consumer", "auto.offset.reset", "earliest", "enable.auto.commit", false, "max.poll.records", 100),
                    new StringDeserializer(), new StringDeserializer())) {
                c.subscribe(List.of(topic));
                int read = 0;
                while (read < 1000) read += c.poll(Duration.ofMillis(500)).count();
                c.commitSync();                                    // the group's bookmarks: where each partition got to
                System.out.println("the settlement group read " + read + " payments and committed");
            }
            // what a lag exporter does: two admin calls, then a subtraction per partition
            Map<TopicPartition, OffsetAndMetadata> committed = admin.listConsumerGroupOffsets(group).partitionsToOffsetAndMetadata().get();
            var ends = admin.listOffsets(committed.keySet().stream().collect(Collectors.toMap(tp -> tp, tp -> OffsetSpec.latest()))).all().get();
            long total = 0;
            for (var e : new TreeMap<TopicPartition, OffsetAndMetadata>((a, b) -> a.partition() - b.partition()) {{ putAll(committed); }}.entrySet()) {
                long end = ends.get(e.getKey()).offset(), lag = end - e.getValue().offset();
                total += lag;
                System.out.printf("partition %d: log end %4d, committed %4d, lag %4d%n", e.getKey().partition(), end, e.getValue().offset(), lag);
            }
            System.out.println("total lag " + total + " records");
            System.out.println("now try: kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group " + group);
        }
    }
}
