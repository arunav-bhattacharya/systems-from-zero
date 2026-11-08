package sfz.msg.l04.demo;

import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.kafka.common.serialization.StringSerializer;

import java.util.Map;
import java.util.concurrent.ExecutionException;

/**
 * Sends one payment to the three-node cluster (env/kafka-cluster.yml) with the acks you pass: all (default) or 1.
 * Prints where it landed, or why the broker refused it.
 */
public class AcksDemo {
    public static void main(String[] args) throws InterruptedException {
        String acks = args.length > 0 ? args[0] : "all";
        Map<String, Object> config = Map.of(
                "bootstrap.servers", "localhost:29092,localhost:39092,localhost:49092",
                "key.serializer", StringSerializer.class,
                "value.serializer", StringSerializer.class,
                "acks", acks,
                // give up after 10 s instead of the default 2 minutes, so a refusal shows up quickly
                "delivery.timeout.ms", 10_000,
                "request.timeout.ms", 5_000);
        try (var producer = new KafkaProducer<String, String>(config)) {
            RecordMetadata md = producer.send(new ProducerRecord<>("payments", "acct-17", "auth 40.00 EUR")).get();
            System.out.printf("acks=%s: written to partition %d at offset %d%n", acks, md.partition(), md.offset());
        } catch (ExecutionException e) {
            Throwable cause = e.getCause();
            System.out.printf("acks=%s: refused with %s%n  %s%n", acks, cause.getClass().getSimpleName(), cause.getMessage());
        }
    }
}
