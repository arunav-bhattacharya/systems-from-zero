package sfz.kafka.l08.demo

import org.apache.kafka.clients.admin.Admin
import org.apache.kafka.clients.admin.NewTopic
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.consumer.OffsetAndMetadata
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.errors.RecordDeserializationException
import org.apache.kafka.common.serialization.Deserializer
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import java.time.Duration

/** Reads a payment amount in cents, "4000", from a record value. Throws on anything else. */
class AmountDeserializer : Deserializer<Long> {
    override fun deserialize(topic: String, data: ByteArray): Long = String(data).toLong()
}

/**
 * Writes six payment amounts to a new one-partition topic; the third, "12x50", is not a number. Then a consumer that
 * restarts after every failure tries to get past it, three times.
 * Argument: "process" (the default: the handler parses the value and throws) or "deserialize" (the value
 * deserializer throws, inside poll; on the last try the consumer seeks past the bad record).
 */
fun main(args: Array<String>) {
    val inDeserializer = args.firstOrNull() == "deserialize"
    val topic = "poison-${System.currentTimeMillis() % 100_000}" // a new topic every run
    val tp = TopicPartition(topic, 0)
    Admin.create(mapOf<String, Any>("bootstrap.servers" to "localhost:9092")).use {
        it.createTopics(listOf(NewTopic(topic, 1, 1.toShort()))).all().get()
    }
    KafkaProducer<String, String>(
        mapOf("bootstrap.servers" to "localhost:9092", "key.serializer" to StringSerializer::class.java, "value.serializer" to StringSerializer::class.java),
    ).use { p -> listOf("1000", "2500", "12x50", "4000", "990", "7000").forEach { p.send(ProducerRecord(topic, 0, "acct-7", it)).get() } }

    val config = mapOf<String, Any>(
        "bootstrap.servers" to "localhost:9092", "group.id" to "ledger-$topic",
        "enable.auto.commit" to false, "auto.offset.reset" to "earliest",
    )
    for (attempt in 1..3) {
        // every attempt is a fresh consumer, as after a crash and a restart: it starts at the committed offset
        if (inDeserializer) {
            KafkaConsumer(config, StringDeserializer(), AmountDeserializer()).use { c ->
                c.assign(listOf(tp))
                while (c.position(tp) < 6) {
                    try {
                        val records = c.poll(Duration.ofSeconds(1))
                        records.forEach { println("try $attempt: offset ${it.offset()} applied ${it.value()} cents") }
                        if (!records.isEmpty) c.commitSync(mapOf(tp to OffsetAndMetadata(c.position(tp))))
                    } catch (e: RecordDeserializationException) {
                        println("try $attempt: poll threw ${e.javaClass.simpleName} at offset ${e.offset()} (${e.cause}); position stays ${c.position(tp)}")
                        if (attempt < 3) break             // crash: the next try starts at the committed offset
                        c.seek(tp, e.offset() + 1)         // the only way past it: skip the record
                        c.commitSync(mapOf(tp to OffsetAndMetadata(e.offset() + 1)))
                        println("try $attempt: seek to ${e.offset() + 1}: offset ${e.offset()} is skipped, and nobody will see it again")
                    }
                }
            }
        } else {
            KafkaConsumer(config, StringDeserializer(), StringDeserializer()).use { c ->
                c.assign(listOf(tp))
                try {
                    while (c.position(tp) < 6) {
                        val records = c.poll(Duration.ofSeconds(1))
                        for (r in records) {
                            val cents = r.value().toLong() // the handler: throws NumberFormatException on 12x50
                            println("try $attempt: offset ${r.offset()} applied $cents cents")
                        }
                        if (!records.isEmpty) c.commitSync(mapOf(tp to OffsetAndMetadata(c.position(tp)))) // after the whole batch
                    }
                } catch (e: NumberFormatException) {
                    println("try $attempt: crashed: $e; no commit")
                }
            }
        }
    }
    val committed = KafkaConsumer(config, StringDeserializer(), StringDeserializer()).use { it.committed(setOf(tp))[tp]?.offset() ?: 0 }
    println("committed offset $committed of 6: lag ${6 - committed}")
}
