package sfz.kafka.l12.demo;

import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.AlterConfigOp;
import org.apache.kafka.clients.admin.ConfigEntry;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.KafkaShareConsumer;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.config.ConfigResource;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

import java.time.Duration;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Twelve notifications in a topic with ONE partition, read by three members of a consumer group and, at the same
 * time, by three members of a share group. Each member takes 100 ms per record, as if it called an SMS provider.
 */
public class ShareGroupDemo {
    static final String BOOTSTRAP = "localhost:9092";
    static final AtomicBoolean running = new AtomicBoolean(true);

    public static void main(String[] args) throws Exception {
        long run = System.currentTimeMillis() % 100_000;
        String topic = "notifications-" + run, consumerGroup = "notify-cg-" + run, shareGroup = "notify-sg-" + run;
        try (var admin = Admin.create(Map.<String, Object>of("bootstrap.servers", BOOTSTRAP))) {
            admin.createTopics(List.of(new NewTopic(topic, 1, (short) 1))).all().get();
            // a share group reads its settings from group configs; start at the beginning instead of the default, latest
            var reset = new AlterConfigOp(new ConfigEntry("share.auto.offset.reset", "earliest"), AlterConfigOp.OpType.SET);
            admin.incrementalAlterConfigs(Map.of(new ConfigResource(ConfigResource.Type.GROUP, shareGroup), List.of(reset))).all().get();

            Map<String, List<Long>> got = new ConcurrentHashMap<>();
            AtomicInteger cgCount = new AtomicInteger(), sgCount = new AtomicInteger();
            List<Thread> members = new ArrayList<>();
            for (int i = 1; i <= 3; i++) {
                String c = "c" + i, s = "s" + i;
                got.put(c, Collections.synchronizedList(new ArrayList<>()));
                got.put(s, Collections.synchronizedList(new ArrayList<>()));
                members.add(Thread.ofPlatform().start(() -> groupMember(topic, consumerGroup, c, got.get(c), cgCount)));
                members.add(Thread.ofPlatform().start(() -> shareMember(topic, shareGroup, s, got.get(s), sgCount)));
            }
            awaitMembers(admin, consumerGroup, shareGroup);
            try (var p = new KafkaProducer<>(Map.<String, Object>of("bootstrap.servers", BOOTSTRAP), new StringSerializer(), new StringSerializer())) {
                for (int i = 0; i < 12; i++) p.send(new ProducerRecord<>(topic, 0, "acct-" + i, "notify-" + i)).get();
            }
            long deadline = System.nanoTime() + 60_000_000_000L;
            while ((cgCount.get() < 12 || sgCount.get() < 12) && System.nanoTime() < deadline) Thread.sleep(100);
            running.set(false);
            for (Thread t : members) t.join();
            System.out.println("consumer group: c1 got " + got.get("c1") + ", c2 got " + got.get("c2") + ", c3 got " + got.get("c3"));
            System.out.println("share group:    s1 got " + got.get("s1") + ", s2 got " + got.get("s2") + ", s3 got " + got.get("s3"));
        }
    }

    static void groupMember(String topic, String group, String name, List<Long> got, AtomicInteger total) {
        try (var c = new KafkaConsumer<>(Map.<String, Object>of("bootstrap.servers", BOOTSTRAP, "group.id", group,
                "group.protocol", "consumer", "auto.offset.reset", "earliest", "client.id", name),
                new StringDeserializer(), new StringDeserializer())) {
            c.subscribe(List.of(topic));
            while (running.get()) handle(c.poll(Duration.ofMillis(200)), got, total);
        }
    }

    static void shareMember(String topic, String group, String name, List<Long> got, AtomicInteger total) {
        try (var c = new KafkaShareConsumer<>(Map.<String, Object>of("bootstrap.servers", BOOTSTRAP, "group.id", group,
                "client.id", name, "max.poll.records", 2, "share.acquire.mode", "record_limit"),
                new StringDeserializer(), new StringDeserializer())) {
            c.subscribe(List.of(topic));
            while (running.get()) handle(c.poll(Duration.ofMillis(200)), got, total);   // implicit mode: the next poll accepts
        }
    }

    static void handle(ConsumerRecords<String, String> records, List<Long> got, AtomicInteger total) {
        for (ConsumerRecord<String, String> r : records) {
            sleep(100);                                    // send the SMS
            got.add(r.offset());
            total.incrementAndGet();
        }
    }

    /** Waits until both groups have their three members, so that no member starts with a head start. */
    static void awaitMembers(Admin admin, String consumerGroup, String shareGroup) throws Exception {
        long deadline = System.nanoTime() + 60_000_000_000L;
        while (System.nanoTime() < deadline) {
            try {
                int cg = admin.describeConsumerGroups(List.of(consumerGroup)).all().get().get(consumerGroup).members().size();
                int sg = admin.describeShareGroups(List.of(shareGroup)).all().get().get(shareGroup).members().size();
                if (cg == 3 && sg == 3) return;
            } catch (Exception e) {
                // the groups don't exist yet
            }
            Thread.sleep(200);
        }
    }

    static void sleep(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
