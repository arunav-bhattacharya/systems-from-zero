package sfz.msg.l06.demo

import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.serialization.StringSerializer

/**
 * Sends 500 small payment events to "ledger-events" at about 1,000 a second, once per setting,
 * and prints what the producer's own metrics say about its batches.
 */
fun main() {
    println("linger.ms  compression  records/request  bytes/batch  compressed/raw  batch waited (ms)")
    run(0, "none")
    run(5, "none")
    run(50, "none")
    run(50, "lz4")
}

private fun run(lingerMs: Int, compression: String) {
    val config = mapOf<String, Any>(
        "bootstrap.servers" to "localhost:9092",
        "key.serializer" to StringSerializer::class.java,
        "value.serializer" to StringSerializer::class.java,
        "linger.ms" to lingerMs,
        "compression.type" to compression,
    )
    KafkaProducer<String, String>(config).use { producer ->
        val acks = (0 until 500).map { i ->
            val event = """{"id":"pay-$i","account":"acct-${i % 50}","amount":4000,"currency":"EUR"}"""
            producer.send(ProducerRecord("ledger-events", "acct-${i % 50}", event)).also {
                Thread.sleep(1) // about 1,000 records a second
            }
        }
        acks.forEach { it.get() }
        println("%9d  %-11s  %15.1f  %11.0f  %14.2f  %17.1f".format(lingerMs, compression,
            producer.metric("records-per-request-avg"), producer.metric("batch-size-avg"),
            producer.metric("compression-rate-avg"), producer.metric("record-queue-time-avg")))
    }
}

/** One value from the producer's "producer-metrics" group. */
private fun KafkaProducer<String, String>.metric(name: String): Double =
    metrics().entries.first { it.key.group() == "producer-metrics" && it.key.name() == name }.value.metricValue() as Double
