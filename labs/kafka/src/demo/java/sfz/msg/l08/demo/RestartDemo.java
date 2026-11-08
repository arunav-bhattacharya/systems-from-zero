package sfz.msg.l08.demo;

import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerRebalanceListener;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.serialization.StringDeserializer;

import java.time.Duration;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Two consumers share the 2-partition topic "ledger-restart" in a new group, on the new protocol. Then c1 is
 * restarted, as in a deploy: closed, and a new consumer started 3 s later. Does c2 notice?
 * Argument: "dynamic" (the default) or "static" (each member has a group.instance.id).
 */
public class RestartDemo {
    static long began = System.nanoTime();
    static boolean isStatic;
    static String group;

    static void note(String msg) {
        System.out.printf("%5.1fs  %s%n", (System.nanoTime() - began) / 1e9, msg);
    }

    public static void main(String[] args) throws Exception {
        isStatic = args.length > 0 && args[0].equals("static");
        String topic = "ledger-restart";
        try (var admin = Admin.create(Map.<String, Object>of("bootstrap.servers", "localhost:9092"))) {
            if (!admin.listTopics().names().get().contains(topic))
                admin.createTopics(List.of(new NewTopic(topic, 2, (short) 1))).all().get();
        }
        group = "restart-" + System.currentTimeMillis();

        System.out.println(isStatic ? "static members: group.instance.id ledger-c1 and ledger-c2" : "dynamic members");
        began = System.nanoTime();   // the clock starts when the members start
        var c1 = start("c1", topic);
        var c2 = start("c2", topic);
        long deadline = System.nanoTime() + 30_000_000_000L;
        while (!(c1.assignment().size() == 1 && c2.assignment().size() == 1) && System.nanoTime() < deadline) pollFor(100, c1, c2);
        pollFor(1_000, c1, c2);

        note("c1 shuts down for a deploy");
        c1.close();
        pollFor(3_000, c2);
        note("c1 starts again");
        c1 = start("c1", topic);
        pollFor(4_000, c1, c2);
        note("now c1 owns " + numbers(c1.assignment()) + ", c2 owns " + numbers(c2.assignment()));
        c1.close();
        c2.close();
    }

    static KafkaConsumer<String, String> start(String name, String topic) {
        Map<String, Object> config = new HashMap<>(Map.of(
                "bootstrap.servers", "localhost:9092", "group.id", group, "group.protocol", "consumer", "client.id", name,
                "key.deserializer", StringDeserializer.class, "value.deserializer", StringDeserializer.class));
        if (isStatic) config.put("group.instance.id", "ledger-" + name);   // a fixed identity per instance
        var c = new KafkaConsumer<String, String>(config);
        c.subscribe(List.of(topic), new ConsumerRebalanceListener() {
            @Override
            public void onPartitionsRevoked(Collection<TopicPartition> partitions) {
                if (!partitions.isEmpty()) note(name + " revoked  " + numbers(partitions));
            }

            @Override
            public void onPartitionsAssigned(Collection<TopicPartition> partitions) {
                if (!partitions.isEmpty()) note(name + " assigned " + numbers(partitions));
            }
        });
        return c;
    }

    @SafeVarargs
    static void pollFor(long ms, KafkaConsumer<String, String>... cs) {
        long end = System.nanoTime() + ms * 1_000_000;
        while (System.nanoTime() < end) for (var c : cs) c.poll(Duration.ofMillis(50));
    }

    static List<Integer> numbers(Collection<TopicPartition> tps) {
        return tps.stream().map(TopicPartition::partition).sorted().toList();
    }
}
