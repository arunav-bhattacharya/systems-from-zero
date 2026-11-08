package sfz.msg.l09.demo;

import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.OffsetAndMetadata;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

import java.time.Duration;
import java.util.*;

/**
 * Writes eight payments to partition 0 of "ledger-payments". The card issuer times out twice on pay-2, and pay-3,
 * acct-7's capture, is a poison pill: its amount is "12x50". The consumer retries a timeout up to 3 times, sends a
 * record that still fails to "ledger-payments.DLT" with headers that say where it came from, and moves on.
 * Argument: "skip" (the default: acct-7's later payments are processed) or "park" (they follow the failed one to
 * the DLT, so no payment of acct-7 overtakes it).
 */
public class DeadLetterDemo {
    /** The card issuer did not answer in time. Worth another try. */
    static class IssuerTimeout extends RuntimeException {
        IssuerTimeout() {
            super("card issuer timed out");
        }
    }

    static int issuerTimeouts = 2;

    static void handle(ConsumerRecord<String, String> r) {
        String[] f = r.value().split(",");
        if (f[0].equals("pay-2") && issuerTimeouts-- > 0) throw new IssuerTimeout();
        Long.parseLong(f[2]);   // throws NumberFormatException for 12x50: bad data, never worth a retry
    }

    public static void main(String[] args) throws Exception {
        boolean park = args.length > 0 && args[0].equals("park");
        String topic = "ledger-payments";
        String dlt = topic + ".DLT";
        TopicPartition tp = new TopicPartition(topic, 0);
        try (var admin = Admin.create(Map.<String, Object>of("bootstrap.servers", "localhost:9092"))) {
            List<String> missing = new ArrayList<>(List.of(topic, dlt));
            missing.removeAll(admin.listTopics().names().get());
            if (!missing.isEmpty()) admin.createTopics(missing.stream().map(t -> new NewTopic(t, 1, (short) 1)).toList()).all().get();
        }
        var producer = new KafkaProducer<String, String>(Map.of("bootstrap.servers", "localhost:9092",
                "key.serializer", StringSerializer.class, "value.serializer", StringSerializer.class));
        String[][] payments = {
                {"acct-1", "pay-0,authorize,1000"}, {"acct-7", "pay-1,authorize,2500"}, {"acct-3", "pay-2,authorize,4000"},
                {"acct-7", "pay-3,capture,12x50"}, {"acct-1", "pay-4,capture,1000"}, {"acct-7", "pay-5,refund,1250"},
                {"acct-3", "pay-6,capture,4000"}, {"acct-7", "pay-7,authorize,3000"}};
        long start = -1;
        for (String[] p : payments) {
            long offset = producer.send(new ProducerRecord<>(topic, 0, p[0], p[1])).get().offset();
            if (start < 0) start = offset;
        }

        Map<String, Long> parked = new HashMap<>();   // key -> offset of the failed record it waits behind
        try (var c = new KafkaConsumer<String, String>(Map.of("bootstrap.servers", "localhost:9092",
                "group.id", "ledger-dlt-demo", "enable.auto.commit", false,
                "key.deserializer", StringDeserializer.class, "value.deserializer", StringDeserializer.class))) {
            c.assign(List.of(tp));
            c.seek(tp, start);   // this run's eight payments
            List<ConsumerRecord<String, String>> records = new ArrayList<>();
            while (records.size() < payments.length) records.addAll(c.poll(Duration.ofSeconds(1)).records(tp));
            for (ConsumerRecord<String, String> r : records) {
                String at = "offset " + r.offset() + " " + r.key() + " " + r.value() + ":";
                Long behind = parked.get(r.key());
                if (behind != null) {
                    deadLetter(producer, dlt, r, "parked behind offset " + behind, "sfz.ParkedKey");
                    System.out.println(at + " parked behind offset " + behind + " -> " + dlt);
                    continue;
                }
                for (int attempt = 1; attempt <= 3; attempt++) {
                    try {
                        handle(r);
                        System.out.println(at + " applied" + (attempt > 1 ? " on attempt " + attempt : ""));
                        break;
                    } catch (IssuerTimeout e) {
                        if (attempt == 3) {
                            deadLetter(producer, dlt, r, e.getMessage(), e.getClass().getName());
                            System.out.println(at + " gave up after 3 attempts -> " + dlt);
                            if (park) parked.put(r.key(), r.offset());
                            break;
                        }
                        long wait = 100L << (attempt - 1);   // 100 ms, then 200 ms
                        System.out.println(at + " attempt " + attempt + " failed (" + e.getMessage() + "), retry in " + wait + " ms");
                        Thread.sleep(wait);
                    } catch (NumberFormatException e) {
                        deadLetter(producer, dlt, r, e.getMessage() == null ? "" : e.getMessage(), e.getClass().getName());
                        System.out.println(at + " " + e.getClass().getSimpleName() + ", no retry -> " + dlt);
                        if (park) parked.put(r.key(), r.offset());
                        break;
                    }
                }
            }
            long next = records.get(records.size() - 1).offset() + 1;
            c.commitSync(Map.of(tp, new OffsetAndMetadata(next)));   // after every dead letter is acked
            System.out.println("committed offset " + next + ": the partition is not stuck");
        }
        producer.close();
    }

    static void deadLetter(KafkaProducer<String, String> p, String dlt, ConsumerRecord<String, String> r, String why, String cls) throws Exception {
        var record = new ProducerRecord<>(dlt, r.key(), r.value());
        record.headers()
                .add("dlt.original.topic", r.topic().getBytes())
                .add("dlt.original.partition", Integer.toString(r.partition()).getBytes())
                .add("dlt.original.offset", Long.toString(r.offset()).getBytes())
                .add("dlt.exception.class", cls.getBytes())
                .add("dlt.exception.message", why.getBytes());
        p.send(record).get();   // wait for the broker's ack before the offset may be committed
    }
}
