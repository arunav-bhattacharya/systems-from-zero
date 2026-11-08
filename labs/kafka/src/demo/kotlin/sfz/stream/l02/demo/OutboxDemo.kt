package sfz.stream.l02.demo

import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.serialization.StringDeserializer
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.nio.file.Path
import java.sql.Connection
import java.sql.DriverManager
import java.time.Duration
import java.util.UUID

private const val CONNECT = "http://localhost:8083"

/**
 * The transactional outbox, end to end. The payment service writes a payment row and its event row in ONE
 * PostgreSQL transaction; Debezium reads the committed rows from the write-ahead log, and its outbox event router
 * turns each outbox row into a record on outbox.event.payment. A second payment's transaction rolls back.
 * Needs: docker compose -f env/kafka.yml --profile cdc up -d --wait
 */
fun main() {
    registerConnector()
    val run = (System.currentTimeMillis() % 100_000).toString()
    DriverManager.getConnection("jdbc:postgresql://localhost:5433/payments", "sfz", "sfz").use { db ->
        db.autoCommit = false
        authorize(db, "pay-$run-1", "acct-17", 4000)
        db.commit()                                    // the payment and its event become durable together
        println("committed pay-$run-1 and its outbox row in one transaction")
        authorize(db, "pay-$run-2", "acct-42", 1250)
        db.rollback()                                  // as if the service crashed before COMMIT: neither row exists
        println("rolled back pay-$run-2 and its outbox row")
    }

    KafkaConsumer(mapOf<String, Any>("bootstrap.servers" to "localhost:9092"), StringDeserializer(), StringDeserializer()).use { consumer ->
        val tp = TopicPartition("outbox.event.payment", 0)
        consumer.assign(listOf(tp))
        consumer.seekToBeginning(listOf(tp))
        val deadline = System.nanoTime() + 30_000_000_000L
        var seen = 0
        while (System.nanoTime() < deadline) {
            for (r in consumer.poll(Duration.ofMillis(500))) {
                if ("pay-$run" !in r.value()) continue // events from earlier runs
                seen++
                println("outbox.event.payment offset ${r.offset()}: key=${r.key()} value=${r.value()}")
                println("  headers id=${header(r, "id")} eventType=${header(r, "eventType")}")
            }
            if (seen > 0 && System.nanoTime() > deadline - 25_000_000_000L) break // 5 more seconds for anything else
        }
        println("$seen event(s) for this run")
    }
}

/** The service's write: a payment and the event that announces it, in the caller's transaction. */
private fun authorize(db: Connection, paymentId: String, account: String, cents: Long) {
    db.prepareStatement("INSERT INTO payment (id, account, amount, status) VALUES (?, ?, ?, 'AUTHORIZED')").use {
        it.setString(1, paymentId); it.setString(2, account); it.setLong(3, cents); it.executeUpdate()
    }
    db.prepareStatement("INSERT INTO outbox (id, aggregatetype, aggregateid, type, payload) VALUES (?, 'payment', ?, 'PaymentAuthorized', ?::jsonb)").use {
        it.setObject(1, UUID.randomUUID())                          // the event id: consumers dedupe on it
        it.setString(2, account)                                    // becomes the record key: per-account order
        it.setString(3, """{"paymentId": "$paymentId", "amount": $cents}""")
        it.executeUpdate()
    }
}

/** Creates the Debezium connector from env/kafka/outbox-connector.json, unless it exists already. */
private fun registerConnector() {
    val http = HttpClient.newHttpClient()
    val status = http.send(HttpRequest.newBuilder(URI.create("$CONNECT/connectors/payments-outbox/status")).build(), HttpResponse.BodyHandlers.ofString())
    if (status.statusCode() == 404) {
        val create = HttpRequest.newBuilder(URI.create("$CONNECT/connectors")).header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofFile(Path.of("../env/kafka/outbox-connector.json"))).build()
        println("created connector payments-outbox: HTTP ${http.send(create, HttpResponse.BodyHandlers.ofString()).statusCode()}")
        Thread.sleep(5000)                                         // let it take its snapshot and start streaming
    } else {
        println("connector payments-outbox exists: " + status.body().replace(Regex(".*\"connector\":\\{\"state\":\"(\\w+)\".*"), "$1"))
    }
}

private fun header(r: ConsumerRecord<String, String>, key: String) = r.headers().lastHeader(key)?.value()?.let { String(it) }
