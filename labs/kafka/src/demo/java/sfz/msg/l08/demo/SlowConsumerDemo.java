package sfz.msg.l08.demo;

import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerRebalanceListener;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.OffsetAndMetadata;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.KafkaException;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

import java.time.Duration;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Two consumers share a new 2-partition topic "ledger-slow-<n>" in a new group, on the new protocol. c1 has
 * max.poll.interval.ms=4000, and pay-2 takes it 8 seconds: a card-issuer call that hangs. Watch the group give
 * c1's partition to c2, and what c1 finds when it comes back.
 */
public class SlowConsumerDemo {
    static long t0 = System.nanoTime();
    static final Map<String, Integer> owned = new ConcurrentHashMap<>();
    static final AtomicBoolean stop = new AtomicBoolean(false);

    static void say(String msg) {
        System.out.printf("%5.1fs  %s%n", (System.nanoTime() - t0) / 1e9, msg);
    }

    public static void main(String[] args) throws Exception {
        String topic = "ledger-slow-" + System.currentTimeMillis() % 100_000;   // a new topic every run
        try (var admin = Admin.create(Map.<String, Object>of("bootstrap.servers", "localhost:9092"))) {
            admin.createTopics(List.of(new NewTopic(topic, 2, (short) 1))).all().get();
        }
        Map<String, Object> config = Map.of(
                "bootstrap.servers", "localhost:9092",
                "group.id", "slow-" + System.currentTimeMillis(),
                "group.protocol", "consumer",
                "key.deserializer", StringDeserializer.class,
                "value.deserializer", StringDeserializer.class,
                "enable.auto.commit", false,
                "auto.offset.reset", "earliest",
                "max.poll.records", 5);
        Map<String, Object> slowConfig = new HashMap<>(config);
        slowConfig.put("max.poll.interval.ms", 4000);
        t0 = System.nanoTime();   // the clock starts when the members start
        Thread c1 = new Thread(() -> member("c1", slowConfig, topic));
        Thread c2 = new Thread(() -> member("c2", config, topic));
        c1.start();
        c2.start();
        while (!(Objects.equals(owned.get("c1"), 1) && Objects.equals(owned.get("c2"), 1))) Thread.sleep(50);

        say("both members own one partition; writing pay-0 .. pay-9 to each");
        try (var p = new KafkaProducer<String, String>(Map.of("bootstrap.servers", "localhost:9092",
                "key.serializer", StringSerializer.class, "value.serializer", StringSerializer.class))) {
            for (int part = 0; part < 2; part++)
                for (int i = 0; i < 10; i++) p.send(new ProducerRecord<>(topic, part, "acct-" + part, "pay-" + i));
        }

        Thread.sleep(16_000);
        stop.set(true);
        c1.join();
        c2.join();
    }

    static void member(String name, Map<String, Object> config, String topic) {
        try {
            memberLoop(name, config, topic);
        } catch (KafkaException e) {
            if (!stop.get()) throw e;   // closing while the group still moves partitions is harmless at the end of a demo
        }
    }

    static void memberLoop(String name, Map<String, Object> config, String topic) {
        Map<String, Object> withId = new HashMap<>(config);
        withId.put("client.id", name);
        try (var c = new KafkaConsumer<String, String>(withId)) {
            c.subscribe(List.of(topic), new ConsumerRebalanceListener() {
                @Override
                public void onPartitionsRevoked(Collection<TopicPartition> partitions) {
                    if (!partitions.isEmpty() && !stop.get()) say(name + " revoked  " + numbers(partitions));
                    owned.put(name, c.assignment().size() - partitions.size());
                }

                @Override
                public void onPartitionsAssigned(Collection<TopicPartition> partitions) {
                    owned.put(name, c.assignment().size());
                    if (!partitions.isEmpty())
                        say(name + " assigned " + numbers(partitions) + ", starts at offset " + partitions.stream().map(c::position).toList());
                }

                @Override
                public void onPartitionsLost(Collection<TopicPartition> partitions) {
                    say(name + " LOST     " + numbers(partitions) + ": the group gave them away while " + name + " was busy");
                    owned.put(name, 0);
                }
            });
            while (!stop.get()) {
                ConsumerRecords<String, String> records = c.poll(Duration.ofMillis(100));
                if (records.isEmpty()) continue;
                List<String> values = new ArrayList<>();
                for (ConsumerRecord<String, String> r : records) {
                    if (name.equals("c1") && r.value().equals("pay-2")) {
                        say(name + " partition " + r.partition() + ": pay-2 calls the card issuer, which hangs for 8 s");
                        sleep(8_000);
                    }
                    values.add(r.value());
                }
                say(name + " partition " + numbers(records.partitions()) + ": processed " + values);
                Map<TopicPartition, OffsetAndMetadata> next = new HashMap<>();
                for (TopicPartition tp : records.partitions()) {
                    List<ConsumerRecord<String, String>> rs = records.records(tp);
                    next.put(tp, new OffsetAndMetadata(rs.get(rs.size() - 1).offset() + 1));
                }
                try {
                    c.commitSync(next);
                } catch (Exception e) {
                    say(name + " commit failed: " + e.getClass().getSimpleName() + ": " + e.getMessage());
                }
            }
        }
    }

    static List<Integer> numbers(Collection<TopicPartition> tps) {
        return tps.stream().map(TopicPartition::partition).toList();
    }

    static void sleep(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
