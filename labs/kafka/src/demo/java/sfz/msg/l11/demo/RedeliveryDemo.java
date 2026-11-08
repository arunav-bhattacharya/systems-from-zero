package sfz.msg.l11.demo;

import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.AlterConfigOp;
import org.apache.kafka.clients.admin.ConfigEntry;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.AcknowledgeType;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.KafkaShareConsumer;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.config.ConfigResource;
import org.apache.kafka.common.header.Header;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * One share group, six notifications, explicit acknowledgement. Without an argument, consumer c1 releases offset 0
 * every time (a transient failure), rejects offset 3 (a permanent one) and accepts the rest; then the demo reads
 * the group's dead-letter queue. With "lock", c1 takes two records and freezes, and c2 waits for their locks.
 */
public class RedeliveryDemo {
    static final String BOOTSTRAP = "localhost:9092";
    static final long START = System.nanoTime();

    public static void main(String[] args) throws Exception {
        long run = System.currentTimeMillis() % 100_000;
        String topic = "notifications-" + run, dlq = "dlq.notifications-" + run, group = "notify-" + run;
        try (var admin = Admin.create(Map.<String, Object>of("bootstrap.servers", BOOTSTRAP))) {
            admin.createTopics(List.of(new NewTopic(topic, 1, (short) 1),
                    // a DLQ topic must be named dlq.* (the broker's default prefix) and allow share groups to write to it
                    new NewTopic(dlq, 1, (short) 1).configs(Map.of("errors.deadletterqueue.group.enable", "true")))).all().get();
            List<AlterConfigOp> groupConfig = List.of(
                    set("share.auto.offset.reset", "earliest"),
                    set("share.record.lock.duration.ms", "15000"),   // the lowest a group may set; the default is 30000
                    set("errors.deadletterqueue.topic.name", dlq));
            admin.incrementalAlterConfigs(Map.of(new ConfigResource(ConfigResource.Type.GROUP, group), groupConfig)).all().get();
        }
        try (var p = new KafkaProducer<>(Map.<String, Object>of("bootstrap.servers", BOOTSTRAP), new StringSerializer(), new StringSerializer())) {
            for (int i = 0; i < 6; i++) p.send(new ProducerRecord<>(topic, 0, "acct-" + i, "notify-" + i)).get();
        }
        if (args.length > 0 && args[0].equals("lock")) lockExpiry(topic, group);
        else redelivery(topic, group, dlq);
    }

    static void redelivery(String topic, String group, String dlq) {
        try (var c1 = shareConsumer(group, "c1")) {
            c1.subscribe(List.of(topic));
            int finished = 0;
            while (finished < 6) {
                for (ConsumerRecord<String, String> r : c1.poll(Duration.ofMillis(500))) {
                    int delivery = r.deliveryCount().orElseThrow();
                    AcknowledgeType ack = r.offset() == 0 ? AcknowledgeType.RELEASE      // the SMS provider timed out
                            : r.offset() == 3 ? AcknowledgeType.REJECT                     // not a valid phone number
                            : AcknowledgeType.ACCEPT;
                    c1.acknowledge(r, ack);
                    if (ack != AcknowledgeType.RELEASE || delivery == 5) finished++;
                    System.out.println("c1 got offset " + r.offset() + ", delivery " + delivery + " -> " + ack
                            + (r.offset() == 0 && delivery == 5 ? ": the last delivery, so the broker archives it" : ""));
                }
                c1.commitSync();                            // send the acknowledgements now
            }
        }
        try (var c = new KafkaConsumer<>(Map.<String, Object>of("bootstrap.servers", BOOTSTRAP), new StringDeserializer(), new StringDeserializer())) {
            TopicPartition tp = new TopicPartition(dlq, 0);
            c.assign(List.of(tp));
            c.seekToBeginning(List.of(tp));
            List<ConsumerRecord<String, String>> got = new ArrayList<>();
            long deadline = System.nanoTime() + 20_000_000_000L;
            while (got.size() < 2 && System.nanoTime() < deadline) c.poll(Duration.ofMillis(500)).forEach(got::add);
            for (ConsumerRecord<String, String> r : got)
                System.out.println("DLQ: offset " + header(r, "__dlq.errors.offset") + " of " + header(r, "__dlq.errors.topic")
                        + ", delivery count " + header(r, "__dlq.errors.delivery.count") + ": " + header(r, "__dlq.errors.message")
                        + " (value " + r.value() + ")");
        }
    }

    static void lockExpiry(String topic, String group) {
        var c1 = shareConsumer(group, "c1", "max.poll.records", 2, "share.acquire.mode", "record_limit");
        c1.subscribe(List.of(topic));
        List<Long> held = new ArrayList<>();
        while (held.isEmpty()) c1.poll(Duration.ofMillis(500)).forEach(r -> held.add(r.offset()));
        System.out.printf("%5.1fs c1 holds offsets %s and freezes (no acknowledgement, no poll)%n", seconds(), held);
        try (var c2 = shareConsumer(group, "c2")) {
            c2.subscribe(List.of(topic));
            int seen = 0;
            while (seen < 6) {
                for (ConsumerRecord<String, String> r : c2.poll(Duration.ofMillis(500))) {
                    c2.acknowledge(r, AcknowledgeType.ACCEPT);
                    seen++;
                    System.out.printf("%5.1fs c2 got offset %d, delivery %d%n", seconds(), r.offset(), r.deliveryCount().orElseThrow());
                }
                c2.commitSync();
            }
        }
        c1.close(Duration.ofSeconds(5));
    }

    static KafkaShareConsumer<String, String> shareConsumer(String group, String name, Object... extra) {
        Map<String, Object> config = new java.util.HashMap<>(Map.of("bootstrap.servers", BOOTSTRAP, "group.id", group, "client.id", name,
                "share.acknowledgement.mode", "explicit"));     // every record gets its own acknowledgement
        for (int i = 0; i < extra.length; i += 2) config.put((String) extra[i], extra[i + 1]);
        return new KafkaShareConsumer<>(config, new StringDeserializer(), new StringDeserializer());
    }

    static AlterConfigOp set(String name, String value) {
        return new AlterConfigOp(new ConfigEntry(name, value), AlterConfigOp.OpType.SET);
    }

    static String header(ConsumerRecord<String, String> r, String key) {
        Header h = r.headers().lastHeader(key);
        return h == null ? null : new String(h.value());
    }

    static double seconds() {
        return (System.nanoTime() - START) / 1e9;
    }
}
