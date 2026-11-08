package sfz.msg.l10.demo

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
 * Writes to a new one-partition topic with a transactional producer and a plain one, and after each step prints the
 * partition as a read_uncommitted reader and a read_committed reader see it: offsets, values, and where each stops.
 */
fun main() {
    val tp = TopicPartition("txn-demo-${System.currentTimeMillis() % 100_000}", 0)
    val bootstrap = "localhost:9092"
    Admin.create(mapOf<String, Any>("bootstrap.servers" to bootstrap)).use { it.createTopics(listOf(NewTopic(tp.topic(), 1, 1.toShort()))).all().get() }
    val ser = mapOf("bootstrap.servers" to bootstrap, "key.serializer" to StringSerializer::class.java, "value.serializer" to StringSerializer::class.java)
    val txn = KafkaProducer<String, String>(ser + ("transactional.id" to "txn-demo"))
    val plain = KafkaProducer<String, String>(ser)
    fun send(p: KafkaProducer<String, String>, v: String) = p.send(ProducerRecord(tp.topic(), 0, "acct-1", v)).get()

    fun show(step: String) {
        println(step)
        for (isolation in listOf("read_uncommitted", "read_committed")) {
            KafkaConsumer<String, String>(
                mapOf("bootstrap.servers" to bootstrap, "isolation.level" to isolation,
                    "key.deserializer" to StringDeserializer::class.java, "value.deserializer" to StringDeserializer::class.java),
            ).use { c ->
                c.assign(listOf(tp))
                c.seekToBeginning(listOf(tp))
                val end = c.endOffsets(listOf(tp)).getValue(tp) // read_committed: the last stable offset
                val seen = mutableListOf<String>()
                while (c.position(tp) < end) c.poll(Duration.ofMillis(200)).forEach { seen += "${it.offset()}=${it.value()}" }
                println("  %-16s stops at %2d, sees %s".format(isolation, end, seen))
            }
        }
    }

    txn.initTransactions()
    txn.beginTransaction(); send(txn, "a"); send(txn, "b"); txn.commitTransaction()
    Thread.sleep(200) // the coordinator writes the markers just after the commit returns
    show("1. transaction commits a, b")
    txn.beginTransaction(); send(txn, "c"); txn.abortTransaction()
    Thread.sleep(200)
    show("2. transaction writes c, then aborts")
    send(plain, "d")
    show("3. plain producer writes d")
    txn.beginTransaction(); send(txn, "e")
    send(plain, "f")
    show("4. transaction writes e and stays open; plain producer writes f")
    txn.commitTransaction()
    Thread.sleep(200)
    show("5. transaction commits e")
    txn.close(); plain.close()
}
