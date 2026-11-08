package sfz.stream.l02.demo;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.header.Header;
import org.apache.kafka.common.serialization.StringDeserializer;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * The transactional outbox, end to end. The payment service writes a payment row and its event row in ONE
 * PostgreSQL transaction; Debezium reads the committed rows from the write-ahead log, and its outbox event router
 * turns each outbox row into a record on outbox.event.payment. A second payment's transaction rolls back.
 * Needs: docker compose -f env/kafka.yml --profile cdc up -d --wait
 */
public class OutboxDemo {
    static final String CONNECT = "http://localhost:8083";

    public static void main(String[] args) throws Exception {
        registerConnector();
        String run = String.valueOf(System.currentTimeMillis() % 100_000);
        try (Connection db = DriverManager.getConnection("jdbc:postgresql://localhost:5433/payments", "sfz", "sfz")) {
            db.setAutoCommit(false);
            authorize(db, "pay-" + run + "-1", "acct-17", 4000);
            db.commit();                                   // the payment and its event become durable together
            System.out.println("committed pay-" + run + "-1 and its outbox row in one transaction");
            authorize(db, "pay-" + run + "-2", "acct-42", 1250);
            db.rollback();                                 // as if the service crashed before COMMIT: neither row exists
            System.out.println("rolled back pay-" + run + "-2 and its outbox row");
        }

        try (var consumer = new KafkaConsumer<>(Map.<String, Object>of("bootstrap.servers", "localhost:9092"),
                new StringDeserializer(), new StringDeserializer())) {
            var tp = new TopicPartition("outbox.event.payment", 0);
            consumer.assign(List.of(tp));
            consumer.seekToBeginning(List.of(tp));
            long deadline = System.nanoTime() + 30_000_000_000L;
            int seen = 0;
            while (System.nanoTime() < deadline) {
                for (ConsumerRecord<String, String> r : consumer.poll(Duration.ofMillis(500))) {
                    if (!r.value().contains("pay-" + run)) continue;     // events from earlier runs
                    seen++;
                    System.out.println("outbox.event.payment offset " + r.offset() + ": key=" + r.key() + " value=" + r.value());
                    System.out.println("  headers id=" + header(r, "id") + " eventType=" + header(r, "eventType"));
                }
                if (seen > 0 && System.nanoTime() > deadline - 25_000_000_000L) break;   // 5 more seconds for anything else
            }
            System.out.println(seen + " event(s) for this run");
        }
    }

    /** The service's write: a payment and the event that announces it, in the caller's transaction. */
    static void authorize(Connection db, String paymentId, String account, long cents) throws Exception {
        try (PreparedStatement payment = db.prepareStatement("INSERT INTO payment (id, account, amount, status) VALUES (?, ?, ?, 'AUTHORIZED')");
             PreparedStatement event = db.prepareStatement(
                     "INSERT INTO outbox (id, aggregatetype, aggregateid, type, payload) VALUES (?, 'payment', ?, 'PaymentAuthorized', ?::jsonb)")) {
            payment.setString(1, paymentId);
            payment.setString(2, account);
            payment.setLong(3, cents);
            payment.executeUpdate();
            event.setObject(1, UUID.randomUUID());                     // the event id: consumers dedupe on it
            event.setString(2, account);                                // becomes the record key: per-account order
            event.setString(3, "{\"paymentId\": \"" + paymentId + "\", \"amount\": " + cents + "}");
            event.executeUpdate();
        }
    }

    /** Creates the Debezium connector from env/kafka/outbox-connector.json, unless it exists already. */
    static void registerConnector() throws Exception {
        var http = HttpClient.newHttpClient();
        var status = http.send(HttpRequest.newBuilder(URI.create(CONNECT + "/connectors/payments-outbox/status")).build(),
                HttpResponse.BodyHandlers.ofString());
        if (status.statusCode() == 404) {
            var create = HttpRequest.newBuilder(URI.create(CONNECT + "/connectors")).header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofFile(Path.of("../env/kafka/outbox-connector.json"))).build();
            System.out.println("created connector payments-outbox: HTTP " + http.send(create, HttpResponse.BodyHandlers.ofString()).statusCode());
            Thread.sleep(5000);                                         // let it take its snapshot and start streaming
        } else {
            System.out.println("connector payments-outbox exists: " + status.body().replaceAll(".*\"connector\":\\{\"state\":\"(\\w+)\".*", "$1"));
        }
    }

    static String header(ConsumerRecord<String, String> r, String key) {
        Header h = r.headers().lastHeader(key);
        return h == null ? null : new String(h.value());
    }
}
