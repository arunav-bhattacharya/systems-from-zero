package sfz.kafka.l01.demo

import org.apache.kafka.clients.admin.Admin
import org.apache.kafka.clients.admin.NewTopic
import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.errors.TopicExistsException
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import java.time.Duration
import java.time.LocalTime
import java.time.temporal.ChronoUnit
import java.util.concurrent.ExecutionException

private const val TOPIC = "payment-events"
private const val BOOTSTRAP = "localhost:9092" // env/kafka.yml

/** Appends 100 payments to a one-partition topic, then reads 5 of them back starting at offset 50. */
fun main() {
    // 1. make sure the topic exists: one partition, so one log
    Admin.create(mapOf<String, Any>("bootstrap.servers" to BOOTSTRAP)).use { admin ->
        try {
            admin.createTopics(listOf(NewTopic(TOPIC, 1, 1.toShort()))).all().get()
        } catch (e: ExecutionException) {
            if (e.cause !is TopicExistsException) throw e
        }
    }

    // 2. append 100 records; the broker answers each one with the offset it got
    val sentAt = LocalTime.now().truncatedTo(ChronoUnit.SECONDS)
    KafkaProducer<String, String>(
        mapOf(
            "bootstrap.servers" to BOOTSTRAP,
            "key.serializer" to StringSerializer::class.java,
            "value.serializer" to StringSerializer::class.java,
        ),
    ).use { producer ->
        val acks = (0 until 100).map { i ->
            producer.send(ProducerRecord(TOPIC, "acct-${i % 7}", "payment-$i sent at $sentAt"))
        }
        println("appended 100 records at offsets ${acks.first().get().offset()}..${acks.last().get().offset()}")
    }

    // 3. read 5 records starting at offset 50: no group, just assign and seek
    val tp = TopicPartition(TOPIC, 0)
    KafkaConsumer<String, String>(
        mapOf(
            "bootstrap.servers" to BOOTSTRAP,
            "key.deserializer" to StringDeserializer::class.java,
            "value.deserializer" to StringDeserializer::class.java,
        ),
    ).use { consumer ->
        consumer.assign(listOf(tp))
        consumer.seek(tp, 50)
        println("reading from offset 50:")
        val got = mutableListOf<ConsumerRecord<String, String>>()
        while (got.size < 5) {
            consumer.poll(Duration.ofMillis(500)).forEach { if (got.size < 5) got += it }
        }
        got.forEach { println("  offset ${it.offset()}  key ${it.key()}  value ${it.value()}") }
        println("end offset of the partition: ${consumer.endOffsets(listOf(tp))[tp]}")
    }
}
