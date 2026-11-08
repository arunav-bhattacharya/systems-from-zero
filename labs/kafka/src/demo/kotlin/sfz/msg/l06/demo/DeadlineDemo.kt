package sfz.msg.l06.demo

import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import java.time.Duration

/**
 * Sends one payment every 500 ms for 15 seconds to "ledger-events" and prints how long each took to be
 * acknowledged, or why it failed. Pause the broker for a few seconds while it runs.
 * Arguments: "idempotent" (the default) or "plain" (idempotence off), then delivery.timeout.ms (default 10000).
 */
fun main(args: Array<String>) {
    val idempotent = args.firstOrNull() != "plain"
    val deadlineMs = args.getOrNull(1)?.toInt() ?: 10_000
    val tp = TopicPartition("ledger-events", 0)
    val consumerConfig = mapOf<String, Any>(
        "bootstrap.servers" to "localhost:9092",
        "key.deserializer" to StringDeserializer::class.java,
        "value.deserializer" to StringDeserializer::class.java,
    )
    val start = KafkaConsumer<String, String>(consumerConfig).use { it.endOffsets(listOf(tp)).getValue(tp) } // this run starts here

    val config = mapOf<String, Any>(
        "bootstrap.servers" to "localhost:9092",
        "key.serializer" to StringSerializer::class.java,
        "value.serializer" to StringSerializer::class.java,
        "enable.idempotence" to idempotent,
        "request.timeout.ms" to 2_000,      // give up on one request after 2 s, then retry
        "delivery.timeout.ms" to deadlineMs, // give up on the record this long after send()
    )
    println("idempotence ${if (idempotent) "on" else "off"}, delivery.timeout.ms $deadlineMs, request.timeout.ms 2000")
    KafkaProducer<String, String>(config).use { producer ->
        repeat(30) { i ->
            val id = "pay-%02d".format(i)
            val sentAt = System.nanoTime()
            producer.send(ProducerRecord("ledger-events", "acct-1", id)) { md, e ->
                val ms = (System.nanoTime() - sentAt) / 1_000_000
                if (e == null) println("%s acked after %5d ms at offset %d".format(id, ms, md.offset()))
                else println("%s FAILED after %4d ms: %s".format(id, ms, e::class.simpleName))
            }
            Thread.sleep(500)
        }
    }

    // what did the log get?
    val written = mutableListOf<String>()
    KafkaConsumer<String, String>(consumerConfig).use { c ->
        c.assign(listOf(tp))
        c.seek(tp, start)
        val end = c.endOffsets(listOf(tp)).getValue(tp)
        while (c.position(tp) < end) c.poll(Duration.ofMillis(500)).forEach { written += it.value() }
    }
    val distinct = written.toSet().size
    println("the log got ${written.size} records for $distinct different payments: ${written.size - distinct} duplicates")
}
