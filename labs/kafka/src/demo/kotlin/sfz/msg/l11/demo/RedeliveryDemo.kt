package sfz.msg.l11.demo

import org.apache.kafka.clients.admin.Admin
import org.apache.kafka.clients.admin.AlterConfigOp
import org.apache.kafka.clients.admin.ConfigEntry
import org.apache.kafka.clients.admin.NewTopic
import org.apache.kafka.clients.consumer.AcknowledgeType
import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.consumer.KafkaShareConsumer
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.config.ConfigResource
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import java.time.Duration

private const val BOOTSTRAP = "localhost:9092"
private val start = System.nanoTime()

/**
 * One share group, six notifications, explicit acknowledgement. Without an argument, consumer c1 releases offset 0
 * every time (a transient failure), rejects offset 3 (a permanent one) and accepts the rest; then the demo reads
 * the group's dead-letter queue. With "lock", c1 takes two records and freezes, and c2 waits for their locks.
 */
fun main(args: Array<String>) {
    val run = System.currentTimeMillis() % 100_000
    val topic = "notifications-$run"
    val dlq = "dlq.notifications-$run"
    val group = "notify-$run"
    Admin.create(mapOf<String, Any>("bootstrap.servers" to BOOTSTRAP)).use { admin ->
        admin.createTopics(listOf(NewTopic(topic, 1, 1.toShort()),
            // a DLQ topic must be named dlq.* (the broker's default prefix) and allow share groups to write to it
            NewTopic(dlq, 1, 1.toShort()).configs(mapOf("errors.deadletterqueue.group.enable" to "true")))).all().get()
        val groupConfig = listOf(
            set("share.auto.offset.reset", "earliest"),
            set("share.record.lock.duration.ms", "15000"), // the lowest a group may set; the default is 30000
            set("errors.deadletterqueue.topic.name", dlq),
        )
        admin.incrementalAlterConfigs(mapOf(ConfigResource(ConfigResource.Type.GROUP, group) to groupConfig)).all().get()
    }
    KafkaProducer(mapOf<String, Any>("bootstrap.servers" to BOOTSTRAP), StringSerializer(), StringSerializer()).use { p ->
        repeat(6) { p.send(ProducerRecord(topic, 0, "acct-$it", "notify-$it")).get() }
    }
    if (args.firstOrNull() == "lock") lockExpiry(topic, group) else redelivery(topic, group, dlq)
}

private fun redelivery(topic: String, group: String, dlq: String) {
    shareConsumer(group, "c1").use { c1 ->
        c1.subscribe(listOf(topic))
        var finished = 0
        while (finished < 6) {
            for (r in c1.poll(Duration.ofMillis(500))) {
                val delivery = r.deliveryCount().get().toInt()
                val ack = when (r.offset()) {
                    0L -> AcknowledgeType.RELEASE // the SMS provider timed out
                    3L -> AcknowledgeType.REJECT  // not a valid phone number
                    else -> AcknowledgeType.ACCEPT
                }
                c1.acknowledge(r, ack)
                if (ack != AcknowledgeType.RELEASE || delivery == 5) finished++
                println("c1 got offset ${r.offset()}, delivery $delivery -> $ack" +
                    if (r.offset() == 0L && delivery == 5) ": the last delivery, so the broker archives it" else "")
            }
            c1.commitSync() // send the acknowledgements now
        }
    }
    KafkaConsumer(mapOf<String, Any>("bootstrap.servers" to BOOTSTRAP), StringDeserializer(), StringDeserializer()).use { c ->
        val tp = TopicPartition(dlq, 0)
        c.assign(listOf(tp))
        c.seekToBeginning(listOf(tp))
        val got = mutableListOf<ConsumerRecord<String, String>>()
        val deadline = System.nanoTime() + 20_000_000_000L
        while (got.size < 2 && System.nanoTime() < deadline) got += c.poll(Duration.ofMillis(500))
        for (r in got) println("DLQ: offset ${r.header("__dlq.errors.offset")} of ${r.header("__dlq.errors.topic")}, " +
            "delivery count ${r.header("__dlq.errors.delivery.count")}: ${r.header("__dlq.errors.message")} (value ${r.value()})")
    }
}

private fun lockExpiry(topic: String, group: String) {
    val c1 = shareConsumer(group, "c1", "max.poll.records" to 2, "share.acquire.mode" to "record_limit")
    c1.subscribe(listOf(topic))
    val held = mutableListOf<Long>()
    while (held.isEmpty()) c1.poll(Duration.ofMillis(500)).forEach { held += it.offset() }
    println("%5.1fs c1 holds offsets %s and freezes (no acknowledgement, no poll)".format(seconds(), held))
    shareConsumer(group, "c2").use { c2 ->
        c2.subscribe(listOf(topic))
        var seen = 0
        while (seen < 6) {
            for (r in c2.poll(Duration.ofMillis(500))) {
                c2.acknowledge(r, AcknowledgeType.ACCEPT)
                seen++
                println("%5.1fs c2 got offset %d, delivery %d".format(seconds(), r.offset(), r.deliveryCount().get()))
            }
            c2.commitSync()
        }
    }
    c1.close(Duration.ofSeconds(5))
}

private fun shareConsumer(group: String, name: String, vararg extra: Pair<String, Any>) = KafkaShareConsumer(
    mapOf<String, Any>("bootstrap.servers" to BOOTSTRAP, "group.id" to group, "client.id" to name,
        "share.acknowledgement.mode" to "explicit") + extra, // every record gets its own acknowledgement
    StringDeserializer(), StringDeserializer(),
)

private fun set(name: String, value: String) = AlterConfigOp(ConfigEntry(name, value), AlterConfigOp.OpType.SET)

private fun ConsumerRecord<String, String>.header(key: String) = headers().lastHeader(key)?.value()?.let { String(it) }

private fun seconds() = (System.nanoTime() - start) / 1e9
