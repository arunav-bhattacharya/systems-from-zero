package sfz.kafka.l09.demo

import org.apache.kafka.clients.admin.Admin
import org.apache.kafka.clients.admin.NewTopic
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import java.time.Duration

/**
 * Instance A of a ledger service has the transactional.id "ledger-0". It commits one transaction, opens another,
 * and then freezes, the way a long GC pause or a network partition freezes a process. Instance B starts with the
 * same transactional.id. Then A wakes up and carries on as if nothing happened.
 */
fun main() {
    val bootstrap = "localhost:9092"
    val tp = TopicPartition("zombie-demo-${System.currentTimeMillis() % 100_000}", 0)
    val admin = Admin.create(mapOf<String, Any>("bootstrap.servers" to bootstrap))
    admin.createTopics(listOf(NewTopic(tp.topic(), 1, 1.toShort()))).all().get()
    val config = mapOf<String, Any>("bootstrap.servers" to bootstrap, "transactional.id" to "ledger-0",
        "key.serializer" to StringSerializer::class.java, "value.serializer" to StringSerializer::class.java)
    fun epoch() = admin.describeProducers(listOf(tp)).partitionResult(tp).get().activeProducers()
        .joinToString { "producer id ${it.producerId()} epoch ${it.producerEpoch()}" }

    val a = KafkaProducer<String, String>(config)
    a.initTransactions()
    a.beginTransaction(); a.send(ProducerRecord(tp.topic(), 0, "acct-1", "A: entry pay-1")); a.commitTransaction()
    println("A committed pay-1                              (partition 0 has seen ${epoch()})")
    a.beginTransaction(); a.send(ProducerRecord(tp.topic(), 0, "acct-2", "A: entry pay-2")).get()
    println("A wrote pay-2 in a new transaction, and freezes")

    val b = KafkaProducer<String, String>(config)
    b.initTransactions() // aborts A's open transaction and bumps the epoch: A is now a zombie
    b.beginTransaction(); b.send(ProducerRecord(tp.topic(), 0, "acct-2", "B: entry pay-2")); b.commitTransaction()
    println("B started with the same id, redid pay-2, committed (partition 0 has seen ${epoch()})")

    println("A wakes up:")
    try { a.send(ProducerRecord(tp.topic(), 0, "acct-3", "A: entry pay-3")).get() } catch (e: Exception) { println("  send:   ${e.cause?.javaClass?.simpleName}: ${e.cause?.message}") }
    try { a.commitTransaction() } catch (e: Exception) { println("  commit: ${e.javaClass.simpleName}: ${e.message}") }
    try { a.abortTransaction() } catch (e: Exception) { println("  abort:  ${e.javaClass.simpleName}: ${e.message}") }
    a.close(Duration.ZERO) // fenced: the only thing left to do
    b.close()
    admin.close()

    KafkaConsumer<String, String>(
        mapOf("bootstrap.servers" to bootstrap, "isolation.level" to "read_committed",
            "key.deserializer" to StringDeserializer::class.java, "value.deserializer" to StringDeserializer::class.java),
    ).use { c ->
        c.assign(listOf(tp))
        c.seekToBeginning(listOf(tp))
        val seen = mutableListOf<String>()
        val deadline = System.nanoTime() + 5_000_000_000L
        while (seen.size < 2 && System.nanoTime() < deadline) c.poll(Duration.ofMillis(200)).forEach { seen += it.value() }
        println("a read_committed reader sees: $seen")
    }
}
