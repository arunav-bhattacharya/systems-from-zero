package sfz.msg.l08.demo;

import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerRebalanceListener;
import org.apache.kafka.clients.consumer.CooperativeStickyAssignor;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.OffsetAndMetadata;
import org.apache.kafka.clients.consumer.RangeAssignor;
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
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/**
 * Three consumers join a new group on the 6-partition topic "ledger-rebalance", one after the other. Each prints what
 * the group gives it and takes away. Before a partition leaves, its listener commits how far it got: the handover.
 * Arguments: "consumer" (the new protocol, the default), "cooperative" (classic, CooperativeStickyAssignor)
 * or "eager" (classic, RangeAssignor); then "nohandover" to skip the commit when a partition leaves.
 */
public class GroupDemo {
    static long start = System.nanoTime();
    static final Map<String, Set<Integer>> owned = new ConcurrentHashMap<>();   // what each member owns now
    static final Map<String, Integer> revoked = new ConcurrentHashMap<>();      // partitions each member handed back
    static final AtomicBoolean stop = new AtomicBoolean(false);
    static boolean handover = true;
    static final AtomicLong processed = new AtomicLong();                        // records processed by the group

    static void log(String msg) {
        System.out.printf("%5.1fs  %s%n", (System.nanoTime() - start) / 1e9, msg);
    }

    public static void main(String[] args) throws Exception {
        String mode = args.length > 0 ? args[0] : "consumer";
        handover = !(args.length > 1 && args[1].equals("nohandover"));
        String topic = "ledger-rebalance";
        try (var admin = Admin.create(Map.<String, Object>of("bootstrap.servers", "localhost:9092"))) {
            if (!admin.listTopics().names().get().contains(topic))
                admin.createTopics(List.of(new NewTopic(topic, 6, (short) 1))).all().get();
        }
        try (var p = new KafkaProducer<String, String>(Map.of("bootstrap.servers", "localhost:9092",
                "key.serializer", StringSerializer.class, "value.serializer", StringSerializer.class))) {
            for (int part = 0; part < 6; part++)
                for (int i = 0; i < 10; i++) p.send(new ProducerRecord<>(topic, part, "acct-" + part, "pay-" + i));
        }
        long total;                                                                  // every record so far
        try (var c = new KafkaConsumer<String, String>(Map.of("bootstrap.servers", "localhost:9092",
                "key.deserializer", StringDeserializer.class, "value.deserializer", StringDeserializer.class))) {
            List<TopicPartition> tps = new ArrayList<>();
            for (int part = 0; part < 6; part++) tps.add(new TopicPartition(topic, part));
            total = c.endOffsets(tps).values().stream().mapToLong(Long::longValue).sum();
        }

        Map<String, Object> config = new HashMap<>(Map.of(
                "bootstrap.servers", "localhost:9092",
                "group.id", "ledger-" + mode + "-" + System.currentTimeMillis(),   // a new group every run
                "key.deserializer", StringDeserializer.class,
                "value.deserializer", StringDeserializer.class,
                "enable.auto.commit", false,
                "auto.offset.reset", "earliest"));
        switch (mode) {
            case "eager" -> config.put("partition.assignment.strategy", RangeAssignor.class.getName());
            case "cooperative" -> config.put("partition.assignment.strategy", CooperativeStickyAssignor.class.getName());
            default -> config.put("group.protocol", "consumer");
        }
        System.out.println("mode " + mode + ", group " + config.get("group.id") + (handover ? "" : ", no handover commits"));

        List<Thread> members = new ArrayList<>();
        start = System.nanoTime(); // the clock starts when c1 joins
        for (String name : List.of("c1", "c2", "c3")) {
            log(name + " joins");
            Map<String, Object> memberConfig = new HashMap<>(config);
            memberConfig.put("client.id", name);
            Thread t = new Thread(() -> runMember(name, memberConfig, topic));
            t.start();
            members.add(t);
            int n = members.size();
            long deadline = System.nanoTime() + 30_000_000_000L;
            // wait until the group is balanced again, and has read every record
            while (!(owned.size() == n && owned.values().stream().allMatch(s -> s.size() == 6 / n) && processed.get() >= total)
                    && System.nanoTime() < deadline)
                Thread.sleep(50);
        }
        Thread.sleep(1_000);   // let the last heartbeats settle before everyone leaves
        stop.set(true);
        for (Thread t : members) t.join();
        System.out.println("partitions handed back: " + revoked + ", " + revoked.values().stream().mapToInt(i -> i).sum() + " in all");
        System.out.println("records processed: " + processed.get() + ", records in the topic: " + total);
    }

    static void runMember(String name, Map<String, Object> config, String topic) {
        try {
            memberLoop(name, config, topic);
        } catch (KafkaException e) {
            if (!stop.get()) throw e;   // closing while the group still moves partitions is harmless at the end of a demo
        }
    }

    static void memberLoop(String name, Map<String, Object> config, String topic) {
        try (var c = new KafkaConsumer<String, String>(config)) {
            c.subscribe(List.of(topic), new ConsumerRebalanceListener() {
                @Override
                public void onPartitionsRevoked(Collection<TopicPartition> partitions) {
                    if (partitions.isEmpty()) return;
                    // the loop below processes every record it polls, so the position is how far this member got
                    Map<TopicPartition, OffsetAndMetadata> offsets = new HashMap<>();
                    for (TopicPartition tp : partitions) offsets.put(tp, new OffsetAndMetadata(c.position(tp)));
                    if (handover) c.commitSync(offsets);
                    if (!stop.get()) {                            // closing at the end: commit, but stay quiet
                        revoked.merge(name, partitions.size(), Integer::sum);
                        log(name + " revoked  " + numbers(partitions)
                                + (handover ? ", committed " + positions(c, partitions) : ", committed nothing"));
                    }
                    Set<Integer> left = new TreeSet<>(owned.getOrDefault(name, Set.of()));
                    left.removeAll(numbers(partitions));
                    owned.put(name, left);
                }

                @Override
                public void onPartitionsAssigned(Collection<TopicPartition> partitions) {
                    Set<Integer> now = numbers(c.assignment());
                    if (!partitions.isEmpty())                     // the positions start at the committed offsets
                        log(name + " assigned " + numbers(partitions) + ", starts at " + positions(c, partitions) + ", owns " + now);
                    owned.put(name, now);
                }
            });
            while (!stop.get()) processed.addAndGet(c.poll(Duration.ofMillis(100)).count()); // "processing" is free here
        }
    }

    static Set<Integer> numbers(Collection<TopicPartition> tps) {
        return tps.stream().map(TopicPartition::partition).collect(Collectors.toCollection(TreeSet::new));
    }

    static List<Long> positions(KafkaConsumer<String, String> c, Collection<TopicPartition> tps) {
        return tps.stream().sorted(Comparator.comparingInt(TopicPartition::partition)).map(c::position).toList();
    }
}
