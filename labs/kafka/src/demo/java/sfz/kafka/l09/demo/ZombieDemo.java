package sfz.kafka.l09.demo;

import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.admin.ProducerState;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Instance A of a ledger service has the transactional.id "ledger-0". It commits one transaction, opens another,
 * and then freezes, the way a long GC pause or a network partition freezes a process. Instance B starts with the
 * same transactional.id. Then A wakes up and carries on as if nothing happened.
 */
public class ZombieDemo {
    static final String BOOTSTRAP = "localhost:9092";

    public static void main(String[] args) throws Exception {
        TopicPartition tp = new TopicPartition("zombie-demo-" + System.currentTimeMillis() % 100_000, 0);
        var admin = Admin.create(Map.<String, Object>of("bootstrap.servers", BOOTSTRAP));
        admin.createTopics(List.of(new NewTopic(tp.topic(), 1, (short) 1))).all().get();
        Map<String, Object> config = Map.of("bootstrap.servers", BOOTSTRAP, "transactional.id", "ledger-0",
                "key.serializer", StringSerializer.class, "value.serializer", StringSerializer.class);

        var a = new KafkaProducer<String, String>(config);
        a.initTransactions();
        a.beginTransaction(); a.send(new ProducerRecord<>(tp.topic(), 0, "acct-1", "A: entry pay-1")); a.commitTransaction();
        System.out.println("A committed pay-1                              (partition 0 has seen " + epoch(admin, tp) + ")");
        a.beginTransaction(); a.send(new ProducerRecord<>(tp.topic(), 0, "acct-2", "A: entry pay-2")).get();
        System.out.println("A wrote pay-2 in a new transaction, and freezes");

        var b = new KafkaProducer<String, String>(config);
        b.initTransactions();   // aborts A's open transaction and bumps the epoch: A is now a zombie
        b.beginTransaction(); b.send(new ProducerRecord<>(tp.topic(), 0, "acct-2", "B: entry pay-2")); b.commitTransaction();
        System.out.println("B started with the same id, redid pay-2, committed (partition 0 has seen " + epoch(admin, tp) + ")");

        System.out.println("A wakes up:");
        try {
            a.send(new ProducerRecord<>(tp.topic(), 0, "acct-3", "A: entry pay-3")).get();
        } catch (Exception e) {
            System.out.println("  send:   " + e.getCause().getClass().getSimpleName() + ": " + e.getCause().getMessage());
        }
        try {
            a.commitTransaction();
        } catch (Exception e) {
            System.out.println("  commit: " + e.getClass().getSimpleName() + ": " + e.getMessage());
        }
        try {
            a.abortTransaction();
        } catch (Exception e) {
            System.out.println("  abort:  " + e.getClass().getSimpleName() + ": " + e.getMessage());
        }
        a.close(Duration.ZERO);   // fenced: the only thing left to do
        b.close();
        admin.close();

        try (var c = new KafkaConsumer<String, String>(Map.of("bootstrap.servers", BOOTSTRAP, "isolation.level", "read_committed",
                "key.deserializer", StringDeserializer.class, "value.deserializer", StringDeserializer.class))) {
            c.assign(List.of(tp));
            c.seekToBeginning(List.of(tp));
            List<String> seen = new ArrayList<>();
            long deadline = System.nanoTime() + 5_000_000_000L;
            while (seen.size() < 2 && System.nanoTime() < deadline) c.poll(Duration.ofMillis(200)).forEach(r -> seen.add(r.value()));
            System.out.println("a read_committed reader sees: " + seen);
        }
    }

    static String epoch(Admin admin, TopicPartition tp) throws Exception {
        List<ProducerState> producers = admin.describeProducers(List.of(tp)).partitionResult(tp).get().activeProducers();
        return producers.stream().map(p -> "producer id " + p.producerId() + " epoch " + p.producerEpoch()).collect(Collectors.joining(", "));
    }
}
