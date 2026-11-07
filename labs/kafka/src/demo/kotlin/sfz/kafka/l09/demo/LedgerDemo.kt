package sfz.kafka.l09.demo

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

private const val BOOTSTRAP = "localhost:9092"

/**
 * A ledger service reads six payments from a new topic and writes one ledger entry per payment to another. Instance 1
 * crashes after writing four entries, before it commits; instance 2 takes over from the committed offset.
 * Argument: "plain" (the default: a normal producer, then commitSync) or "txn" (entries and offsets in one transaction).
 */
fun main(args: Array<String>) {
    val txn = args.firstOrNull() == "txn"
    val run = System.currentTimeMillis() % 100_000
    val input = TopicPartition("payments-$run", 0)
    val output = TopicPartition("ledger-entries-$run", 0)
    Admin.create(mapOf<String, Any>("bootstrap.servers" to BOOTSTRAP)).use { admin ->
        admin.createTopics(listOf(NewTopic(input.topic(), 1, 1.toShort()), NewTopic(output.topic(), 1, 1.toShort()))).all().get()
    }
    producer(null).use { p -> repeat(6) { p.send(ProducerRecord(input.topic(), 0, "acct-$it", "pay-$it")).get() } }

    val group = "ledger-$run"
    val txnId = "ledger-$run-0" // one transactional.id per input partition this instance owns
    fun consumer() = KafkaConsumer<String, String>(
        mapOf<String, Any>("bootstrap.servers" to BOOTSTRAP, "group.id" to group, "enable.auto.commit" to false,
            "auto.offset.reset" to "earliest", "isolation.level" to "read_committed",
            "key.deserializer" to StringDeserializer::class.java, "value.deserializer" to StringDeserializer::class.java),
    ).also { it.assign(listOf(input)) }

    // instance 1: four entries reach the broker, then the process dies: no commit, no abort, no close
    val c1 = consumer()
    val p1 = producer(if (txn) txnId else null)
    if (txn) { p1.initTransactions(); p1.beginTransaction() }
    for (r in pollAll(c1, 6).take(4)) p1.send(ProducerRecord(output.topic(), 0, r.key(), "entry:${r.value()}")).get()
    println("instance 1: wrote entries for pay-0 .. pay-3" + (if (txn) " inside a transaction" else "") + ", then crashed before committing")

    // instance 2: same group (and, for txn, the same transactional.id), starts from the committed offset
    consumer().use { c2 ->
        producer(if (txn) txnId else null).use { p2 ->
            if (txn) {
                p2.initTransactions() // aborts what instance 1 left open, and fences instance 1
                println("instance 2: initTransactions() aborted instance 1's open transaction")
                p2.beginTransaction()
            }
            println("instance 2: starts at offset ${c2.position(input)}")
            val records = pollAll(c2, 6)
            for (r in records) p2.send(ProducerRecord(output.topic(), 0, r.key(), "entry:${r.value()}"))
            val next = mapOf(input to OffsetAndMetadata(records.last().offset() + 1))
            if (txn) {
                p2.sendOffsetsToTransaction(next, c2.groupMetadata()) // the bookmark rides in the transaction
                p2.commitTransaction()
            } else {
                p2.flush()
                c2.commitSync(next)
            }
            println("instance 2: wrote entries for pay-0 .. pay-5, committed offset ${records.last().offset() + 1}")
        }
    }

    for (isolation in listOf("read_uncommitted", "read_committed")) {
        val values = readAll(output, isolation)
        val counts = values.groupingBy { it.removePrefix("entry:") }.eachCount().toSortedMap()
        println("%-16s reader sees %2d entries: %s".format(isolation, values.size, counts))
    }
}

/** Polls until [n] records have arrived: a first poll on a fresh broker can come back empty. */
private fun pollAll(c: KafkaConsumer<String, String>, n: Int): List<ConsumerRecord<String, String>> {
    val records = mutableListOf<ConsumerRecord<String, String>>()
    while (records.size < n) records += c.poll(Duration.ofSeconds(1))
    return records
}

private fun producer(txnId: String?) = KafkaProducer<String, String>(
    mapOf<String, Any>("bootstrap.servers" to BOOTSTRAP, "key.serializer" to StringSerializer::class.java, "value.serializer" to StringSerializer::class.java) +
        (if (txnId != null) mapOf("transactional.id" to txnId) else emptyMap()),
)

private fun readAll(tp: TopicPartition, isolation: String): List<String> =
    KafkaConsumer<String, String>(
        mapOf("bootstrap.servers" to BOOTSTRAP, "isolation.level" to isolation,
            "key.deserializer" to StringDeserializer::class.java, "value.deserializer" to StringDeserializer::class.java),
    ).use { c ->
        c.assign(listOf(tp))
        c.seekToBeginning(listOf(tp))
        val end = endOffset(tp) // the log end; a read_committed reader gets there once no transaction is open
        val values = mutableListOf<String>()
        val deadline = System.nanoTime() + 10_000_000_000L
        while (c.position(tp) < end && System.nanoTime() < deadline) c.poll(Duration.ofMillis(200)).forEach { values += it.value() }
        values
    }

private fun endOffset(tp: TopicPartition): Long =
    KafkaConsumer<String, String>(
        mapOf("bootstrap.servers" to BOOTSTRAP, "key.deserializer" to StringDeserializer::class.java, "value.deserializer" to StringDeserializer::class.java),
    ).use { it.endOffsets(listOf(tp)).getValue(tp) }
