package sfz.kafka.l08.demo

import org.apache.kafka.clients.admin.Admin
import org.apache.kafka.clients.admin.NewTopic
import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.consumer.OffsetAndMetadata
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import java.time.Duration

/** The card issuer did not answer in time. Worth another try. */
class IssuerTimeout : RuntimeException("card issuer timed out")

/**
 * Writes eight payments to partition 0 of "ledger-payments". The card issuer times out twice on pay-2, and pay-3,
 * acct-7's capture, is a poison pill: its amount is "12x50". The consumer retries a timeout up to 3 times, sends a
 * record that still fails to "ledger-payments.DLT" with headers that say where it came from, and moves on.
 * Argument: "skip" (the default: acct-7's later payments are processed) or "park" (they follow the failed one to
 * the DLT, so no payment of acct-7 overtakes it).
 */
fun main(args: Array<String>) {
    val park = args.firstOrNull() == "park"
    val topic = "ledger-payments"
    val dlt = "$topic.DLT"
    val tp = TopicPartition(topic, 0)
    Admin.create(mapOf<String, Any>("bootstrap.servers" to "localhost:9092")).use { admin ->
        val missing = listOf(topic, dlt) - admin.listTopics().names().get()
        if (missing.isNotEmpty()) admin.createTopics(missing.map { NewTopic(it, 1, 1.toShort()) }).all().get()
    }
    val producer = KafkaProducer<String, String>(
        mapOf("bootstrap.servers" to "localhost:9092", "key.serializer" to StringSerializer::class.java, "value.serializer" to StringSerializer::class.java),
    )
    val payments = listOf(
        "acct-1" to "pay-0,authorize,1000", "acct-7" to "pay-1,authorize,2500", "acct-3" to "pay-2,authorize,4000",
        "acct-7" to "pay-3,capture,12x50", "acct-1" to "pay-4,capture,1000", "acct-7" to "pay-5,refund,1250",
        "acct-3" to "pay-6,capture,4000", "acct-7" to "pay-7,authorize,3000",
    )
    val start = payments.map { (k, v) -> producer.send(ProducerRecord(topic, 0, k, v)).get().offset() }.first()

    var issuerTimeouts = 2
    fun handle(r: ConsumerRecord<String, String>) {
        val (id, _, amount) = r.value().split(",")
        if (id == "pay-2" && issuerTimeouts-- > 0) throw IssuerTimeout()
        amount.toLong() // throws NumberFormatException for 12x50: bad data, never worth a retry
    }

    val parked = mutableMapOf<String, Long>() // key -> offset of the failed record it waits behind
    KafkaConsumer<String, String>(
        mapOf("bootstrap.servers" to "localhost:9092", "group.id" to "ledger-dlt-demo", "enable.auto.commit" to false,
            "key.deserializer" to StringDeserializer::class.java, "value.deserializer" to StringDeserializer::class.java),
    ).use { c ->
        c.assign(listOf(tp))
        c.seek(tp, start) // this run's eight payments
        val records = mutableListOf<ConsumerRecord<String, String>>()
        while (records.size < payments.size) records += c.poll(Duration.ofSeconds(1)).records(tp)
        for (r in records) {
            val at = "offset ${r.offset()} ${r.key()} ${r.value()}:"
            val behind = parked[r.key()]
            if (behind != null) {
                deadLetter(producer, dlt, r, "parked behind offset $behind", "sfz.ParkedKey")
                println("$at parked behind offset $behind -> $dlt")
                continue
            }
            for (attempt in 1..3) {
                try {
                    handle(r)
                    println("$at applied" + if (attempt > 1) " on attempt $attempt" else "")
                    break
                } catch (e: IssuerTimeout) {
                    if (attempt == 3) {
                        deadLetter(producer, dlt, r, e.message!!, e.javaClass.name)
                        println("$at gave up after 3 attempts -> $dlt")
                        if (park) parked[r.key()] = r.offset()
                        break
                    }
                    val wait = 100L shl (attempt - 1) // 100 ms, then 200 ms
                    println("$at attempt $attempt failed (${e.message}), retry in $wait ms")
                    Thread.sleep(wait)
                } catch (e: NumberFormatException) {
                    deadLetter(producer, dlt, r, e.message ?: "", e.javaClass.name)
                    println("$at ${e.javaClass.simpleName}, no retry -> $dlt")
                    if (park) parked[r.key()] = r.offset()
                    break
                }
            }
        }
        c.commitSync(mapOf(tp to OffsetAndMetadata(records.last().offset() + 1))) // after every dead letter is acked
        println("committed offset ${records.last().offset() + 1}: the partition is not stuck")
    }
    producer.close()
}

private fun deadLetter(p: KafkaProducer<String, String>, dlt: String, r: ConsumerRecord<String, String>, why: String, cls: String) {
    val record = ProducerRecord(dlt, r.key(), r.value())
    record.headers()
        .add("dlt.original.topic", r.topic().toByteArray())
        .add("dlt.original.partition", r.partition().toString().toByteArray())
        .add("dlt.original.offset", r.offset().toString().toByteArray())
        .add("dlt.exception.class", cls.toByteArray())
        .add("dlt.exception.message", why.toByteArray())
    p.send(record).get() // wait for the broker's ack before the offset may be committed
}
