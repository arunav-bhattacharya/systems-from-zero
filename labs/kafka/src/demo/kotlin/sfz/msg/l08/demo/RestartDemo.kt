package sfz.msg.l08.demo

import org.apache.kafka.clients.admin.Admin
import org.apache.kafka.clients.admin.NewTopic
import org.apache.kafka.clients.consumer.ConsumerRebalanceListener
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.serialization.StringDeserializer
import java.time.Duration

private var began = System.nanoTime()
private fun note(msg: String) = println("%5.1fs  %s".format((System.nanoTime() - began) / 1e9, msg))

/**
 * Two consumers share the 2-partition topic "ledger-restart" in a new group, on the new protocol. Then c1 is
 * restarted, as in a deploy: closed, and a new consumer started 3 s later. Does c2 notice?
 * Argument: "dynamic" (the default) or "static" (each member has a group.instance.id).
 */
fun main(args: Array<String>) {
    val static = args.firstOrNull() == "static"
    val topic = "ledger-restart"
    Admin.create(mapOf<String, Any>("bootstrap.servers" to "localhost:9092")).use { admin ->
        if (topic !in admin.listTopics().names().get()) admin.createTopics(listOf(NewTopic(topic, 2, 1.toShort()))).all().get()
    }
    val group = "restart-${System.currentTimeMillis()}"
    fun start(name: String): KafkaConsumer<String, String> {
        val c = KafkaConsumer<String, String>(
            mapOf<String, Any>(
                "bootstrap.servers" to "localhost:9092", "group.id" to group, "group.protocol" to "consumer", "client.id" to name,
                "key.deserializer" to StringDeserializer::class.java, "value.deserializer" to StringDeserializer::class.java,
            ) + if (static) mapOf("group.instance.id" to "ledger-$name") else emptyMap(), // a fixed identity per instance
        )
        c.subscribe(listOf(topic), object : ConsumerRebalanceListener {
            override fun onPartitionsRevoked(partitions: Collection<TopicPartition>) {
                if (partitions.isNotEmpty()) note("$name revoked  ${partitions.map { it.partition() }.sorted()}")
            }
            override fun onPartitionsAssigned(partitions: Collection<TopicPartition>) {
                if (partitions.isNotEmpty()) note("$name assigned ${partitions.map { it.partition() }.sorted()}")
            }
        })
        return c
    }
    fun pollFor(ms: Long, vararg cs: KafkaConsumer<String, String>) {
        val end = System.nanoTime() + ms * 1_000_000
        while (System.nanoTime() < end) cs.forEach { it.poll(Duration.ofMillis(50)) }
    }

    println(if (static) "static members: group.instance.id ledger-c1 and ledger-c2" else "dynamic members")
    began = System.nanoTime() // the clock starts when the members start
    var c1 = start("c1")
    val c2 = start("c2")
    val deadline = System.nanoTime() + 30_000_000_000L
    while (!(c1.assignment().size == 1 && c2.assignment().size == 1) && System.nanoTime() < deadline) pollFor(100, c1, c2)
    pollFor(1_000, c1, c2)

    note("c1 shuts down for a deploy")
    c1.close()
    pollFor(3_000, c2)
    note("c1 starts again")
    c1 = start("c1")
    pollFor(4_000, c1, c2)
    note("now c1 owns ${c1.assignment().map { it.partition() }.sorted()}, c2 owns ${c2.assignment().map { it.partition() }.sorted()}")
    c1.close()
    c2.close()
}
