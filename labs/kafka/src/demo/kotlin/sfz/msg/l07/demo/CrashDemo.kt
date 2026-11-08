package sfz.msg.l07.demo

import org.apache.kafka.clients.consumer.ConsumerRecords
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.consumer.OffsetAndMetadata
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import java.time.Duration

private val P0 = TopicPartition("payments", 0)
private val appliedKeys = mutableSetOf<String>() // the ledger's idempotency keys
private var balanceCents = 0L                    // acct-1's balance
private var start = 0L                           // the offset of pay-00

/**
 * Writes pay-00 .. pay-09 (10.00 EUR each, for acct-1) to partition 0 of "payments". Consumer 1 crashes while
 * applying pay-07; consumer 2, in the same group, carries on from the group's committed offset.
 * Arguments: "after" (commit after processing, the default) or "before", then "dedupe" (the default) or "nodedupe".
 */
fun main(args: Array<String>) {
    val commitFirst = args.getOrNull(0) == "before"
    val dedupe = args.getOrNull(1) != "nodedupe"
    val config = mapOf<String, Any>(
        "bootstrap.servers" to "localhost:9092",
        "group.id" to "crash-demo-${System.currentTimeMillis()}", // a new group every run
        "key.deserializer" to StringDeserializer::class.java,
        "value.deserializer" to StringDeserializer::class.java,
        "enable.auto.commit" to false,
        "max.poll.records" to 5,
    )

    KafkaProducer<String, String>(
        mapOf(
            "bootstrap.servers" to "localhost:9092",
            "key.serializer" to StringSerializer::class.java,
            "value.serializer" to StringSerializer::class.java,
        ),
    ).use { producer ->
        start = producer.send(ProducerRecord("payments", 0, "acct-1", "pay-00")).get().offset()
        for (i in 1 until 10) producer.send(ProducerRecord("payments", 0, "acct-1", "pay-0$i"))
    }

    // consumer 1: the group's bookmark starts at pay-00; it dies while applying pay-07
    KafkaConsumer<String, String>(config).use { c1 ->
        c1.assign(listOf(P0))                                  // the group.id is where commits go
        c1.commitSync(mapOf(P0 to OffsetAndMetadata(start)))
        crash@ while (true) {
            val batch = c1.poll(Duration.ofMillis(500))
            if (commitFirst) commit(c1, batch)
            for (r in batch) {
                if (r.value() == "pay-07") {
                    println("consumer 1: CRASH while applying pay-07")
                    break@crash                                // no commit, no clean-up: gone
                }
                applyPayment(r.value(), dedupe, "consumer 1")
            }
            if (!commitFirst) commit(c1, batch)
        }
    }

    // consumer 2, same group: it starts at the committed offset and reads to the end
    KafkaConsumer<String, String>(config).use { c2 ->
        c2.assign(listOf(P0))
        println("consumer 2: starts at offset %d (pay-%02d)".format(c2.position(P0), c2.position(P0) - start))
        while (c2.position(P0) < start + 10) {
            val batch = c2.poll(Duration.ofMillis(500))
            for (r in batch) applyPayment(r.value(), dedupe, "consumer 2")
            commit(c2, batch)
        }
    }
    println("ledger: %d of 10 payments applied, acct-1 balance %.2f EUR (should be 100.00)".format(appliedKeys.size, balanceCents / 100.0))
}

private fun applyPayment(key: String, dedupe: Boolean, who: String) {
    if (dedupe && key in appliedKeys) {
        println("$who: $key already applied, skipped")
        return
    }
    appliedKeys += key // in a database: the key's row and the balance update, in one transaction
    balanceCents += 1000
    println("$who: applied $key")
}

private fun commit(c: KafkaConsumer<String, String>, batch: ConsumerRecords<String, String>) {
    if (batch.isEmpty) return
    val next = batch.records(P0).last().offset() + 1 // the next record to read
    c.commitSync(mapOf(P0 to OffsetAndMetadata(next)))
    println("            committed offset %d (pay-%02d is next)".format(next, next - start))
}
