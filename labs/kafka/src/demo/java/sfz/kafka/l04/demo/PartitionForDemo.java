package sfz.kafka.l04.demo;

import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;
import org.apache.kafka.common.utils.Utils;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

/**
 * For each key: the murmur2 hash, the hash made positive, the partition that arithmetic gives,
 * and the partition the real producer chose when it sent a record with that key to the topic "accounts".
 */
public class PartitionForDemo {
    public static void main(String[] args) throws Exception {
        List<String> keys = args.length > 0 ? List.of(args) : List.of("acct-17", "acct-42", "acct-99", "card-1");
        Map<String, Object> config = Map.of(
                "bootstrap.servers", "localhost:9092",   // env/kafka.yml
                "key.serializer", StringSerializer.class,
                "value.serializer", StringSerializer.class);
        try (var producer = new KafkaProducer<String, String>(config)) {
            int n = producer.partitionsFor("accounts").size();
            System.out.printf("topic accounts has %d partitions%n", n);
            System.out.printf("%-9s %12s %11s %5s   %s%n", "key", "murmur2", "positive", "% " + n, "producer chose");
            for (String key : keys) {
                int hash = Utils.murmur2(key.getBytes(StandardCharsets.UTF_8)); // the bytes StringSerializer sends
                int positive = Utils.toPositive(hash);                          // hash & 0x7fffffff
                int chosen = producer.send(new ProducerRecord<>("accounts", key, "auth 10.00 EUR")).get().partition();
                System.out.printf("%-9s %12d %11d %5d   partition %d%n", key, hash, positive, positive % n, chosen);
            }
        }
    }
}
