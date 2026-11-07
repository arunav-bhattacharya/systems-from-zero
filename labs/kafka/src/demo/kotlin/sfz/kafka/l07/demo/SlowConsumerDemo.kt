package sfz.kafka.l07.demo

import org.apache.kafka.clients.admin.Admin
import org.apache.kafka.clients.admin.NewTopic
import org.apache.kafka.clients.consumer.ConsumerRebalanceListener
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.consumer.OffsetAndMetadata
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.KafkaException
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import java.time.Duration
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.concurrent.thread

private var t0 = System.nanoTime()
private fun say(msg: String) = println("%5.1fs  %s".format((System.nanoTime() - t0) / 1e9, msg))

/**
 * Two consumers share a new 2-partition topic "ledger-slow-<n>" in a new group, on the new protocol. c1 has
 * max.poll.interval.ms=4000, and pay-2 takes it 8 seconds: a card-issuer call that hangs. Watch the group give
 * c1's partition to c2, and what c1 finds when it comes back.
 */
fun main() {
    val topic = "ledger-slow-${System.currentTimeMillis() % 100_000}" // a new topic every run
    Admin.create(mapOf<String, Any>("bootstrap.servers" to "localhost:9092")).use { admin ->
        admin.createTopics(listOf(NewTopic(topic, 2, 1.toShort()))).all().get()
    }
    val config = mapOf<String, Any>(
        "bootstrap.servers" to "localhost:9092",
        "group.id" to "slow-${System.currentTimeMillis()}",
        "group.protocol" to "consumer",
        "key.deserializer" to StringDeserializer::class.java,
        "value.deserializer" to StringDeserializer::class.java,
        "enable.auto.commit" to false,
        "auto.offset.reset" to "earliest",
        "max.poll.records" to 5,
    )
    val owned = ConcurrentHashMap<String, Int>()
    val stop = AtomicBoolean(false)
    t0 = System.nanoTime() // the clock starts when the members start
    val c1 = thread { member("c1", config + ("max.poll.interval.ms" to 4000), topic, owned, stop) }
    val c2 = thread { member("c2", config, topic, owned, stop) }
    while (!(owned["c1"] == 1 && owned["c2"] == 1)) Thread.sleep(50)

    say("both members own one partition; writing pay-0 .. pay-9 to each")
    KafkaProducer<String, String>(
        mapOf("bootstrap.servers" to "localhost:9092", "key.serializer" to StringSerializer::class.java, "value.serializer" to StringSerializer::class.java),
    ).use { p -> for (part in 0 until 2) repeat(10) { p.send(ProducerRecord(topic, part, "acct-$part", "pay-$it")) } }

    Thread.sleep(16_000)
    stop.set(true)
    c1.join(); c2.join()
}

private fun member(name: String, config: Map<String, Any>, topic: String, owned: MutableMap<String, Int>, stop: AtomicBoolean) {
    try {
        memberLoop(name, config, topic, owned, stop)
    } catch (e: KafkaException) {
        if (!stop.get()) throw e // closing while the group still moves partitions is harmless at the end of a demo
    }
}

private fun memberLoop(name: String, config: Map<String, Any>, topic: String, owned: MutableMap<String, Int>, stop: AtomicBoolean) {
    KafkaConsumer<String, String>(config + ("client.id" to name)).use { c ->
        c.subscribe(listOf(topic), object : ConsumerRebalanceListener {
            override fun onPartitionsRevoked(partitions: Collection<TopicPartition>) {
                if (partitions.isNotEmpty() && !stop.get()) say("$name revoked  ${partitions.map { it.partition() }}")
                owned[name] = c.assignment().size - partitions.size
            }
            override fun onPartitionsAssigned(partitions: Collection<TopicPartition>) {
                owned[name] = c.assignment().size
                if (partitions.isNotEmpty()) say("$name assigned ${partitions.map { it.partition() }}, starts at offset ${partitions.map { c.position(it) }}")
            }
            override fun onPartitionsLost(partitions: Collection<TopicPartition>) {
                say("$name LOST     ${partitions.map { it.partition() }}: the group gave them away while $name was busy")
                owned[name] = 0
            }
        })
        while (!stop.get()) {
            val records = c.poll(Duration.ofMillis(100))
            if (records.isEmpty) continue
            for (r in records) {
                if (name == "c1" && r.value() == "pay-2") {
                    say("$name partition ${r.partition()}: pay-2 calls the card issuer, which hangs for 8 s")
                    Thread.sleep(8_000)
                }
            }
            say("$name partition ${records.partitions().map { it.partition() }}: processed ${records.map { it.value() }}")
            try {
                c.commitSync(records.partitions().associateWith { OffsetAndMetadata(records.records(it).last().offset() + 1) })
            } catch (e: Exception) {
                say("$name commit failed: ${e.javaClass.simpleName}: ${e.message}")
            }
        }
    }
}
