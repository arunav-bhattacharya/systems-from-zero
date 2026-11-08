package sfz.msg.l11.demo

import org.apache.kafka.clients.admin.Admin
import org.apache.kafka.clients.admin.AlterConfigOp
import org.apache.kafka.clients.admin.ConfigEntry
import org.apache.kafka.clients.admin.NewTopic
import org.apache.kafka.clients.consumer.ConsumerRecords
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.consumer.KafkaShareConsumer
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.config.ConfigResource
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import java.time.Duration
import java.util.Collections
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import kotlin.concurrent.thread

private const val BOOTSTRAP = "localhost:9092"
private val running = AtomicBoolean(true)

/**
 * Twelve notifications in a topic with ONE partition, read by three members of a consumer group and, at the same
 * time, by three members of a share group. Each member takes 100 ms per record, as if it called an SMS provider.
 */
fun main() {
    val run = System.currentTimeMillis() % 100_000
    val topic = "notifications-$run"
    val consumerGroup = "notify-cg-$run"
    val shareGroup = "notify-sg-$run"
    Admin.create(mapOf<String, Any>("bootstrap.servers" to BOOTSTRAP)).use { admin ->
        admin.createTopics(listOf(NewTopic(topic, 1, 1.toShort()))).all().get()
        // a share group reads its settings from group configs; start at the beginning instead of the default, latest
        val reset = AlterConfigOp(ConfigEntry("share.auto.offset.reset", "earliest"), AlterConfigOp.OpType.SET)
        admin.incrementalAlterConfigs(mapOf(ConfigResource(ConfigResource.Type.GROUP, shareGroup) to listOf(reset))).all().get()

        val got = (1..3).flatMap { listOf("c$it", "s$it") }.associateWith { Collections.synchronizedList(mutableListOf<Long>()) }
        val cgCount = AtomicInteger()
        val sgCount = AtomicInteger()
        val members = (1..3).flatMap { i ->
            listOf(
                thread { groupMember(topic, consumerGroup, "c$i", got.getValue("c$i"), cgCount) },
                thread { shareMember(topic, shareGroup, "s$i", got.getValue("s$i"), sgCount) },
            )
        }
        awaitMembers(admin, consumerGroup, shareGroup)
        KafkaProducer(mapOf<String, Any>("bootstrap.servers" to BOOTSTRAP), StringSerializer(), StringSerializer()).use { p ->
            repeat(12) { p.send(ProducerRecord(topic, 0, "acct-$it", "notify-$it")).get() }
        }
        val deadline = System.nanoTime() + 60_000_000_000L
        while ((cgCount.get() < 12 || sgCount.get() < 12) && System.nanoTime() < deadline) Thread.sleep(100)
        running.set(false)
        members.forEach { it.join() }
        println("consumer group: c1 got ${got["c1"]}, c2 got ${got["c2"]}, c3 got ${got["c3"]}")
        println("share group:    s1 got ${got["s1"]}, s2 got ${got["s2"]}, s3 got ${got["s3"]}")
    }
}

private fun groupMember(topic: String, group: String, name: String, got: MutableList<Long>, total: AtomicInteger) =
    KafkaConsumer(mapOf<String, Any>("bootstrap.servers" to BOOTSTRAP, "group.id" to group, "group.protocol" to "consumer",
        "auto.offset.reset" to "earliest", "client.id" to name), StringDeserializer(), StringDeserializer()).use { c ->
        c.subscribe(listOf(topic))
        while (running.get()) handle(c.poll(Duration.ofMillis(200)), got, total)
    }

private fun shareMember(topic: String, group: String, name: String, got: MutableList<Long>, total: AtomicInteger) =
    KafkaShareConsumer(mapOf<String, Any>("bootstrap.servers" to BOOTSTRAP, "group.id" to group, "client.id" to name,
        "max.poll.records" to 2, "share.acquire.mode" to "record_limit"), StringDeserializer(), StringDeserializer()).use { c ->
        c.subscribe(listOf(topic))
        while (running.get()) handle(c.poll(Duration.ofMillis(200)), got, total) // implicit mode: the next poll accepts
    }

private fun handle(records: ConsumerRecords<String, String>, got: MutableList<Long>, total: AtomicInteger) {
    for (r in records) {
        Thread.sleep(100) // send the SMS
        got += r.offset()
        total.incrementAndGet()
    }
}

/** Waits until both groups have their three members, so that no member starts with a head start. */
private fun awaitMembers(admin: Admin, consumerGroup: String, shareGroup: String) {
    val deadline = System.nanoTime() + 60_000_000_000L
    while (System.nanoTime() < deadline) {
        try {
            val cg = admin.describeConsumerGroups(listOf(consumerGroup)).all().get().getValue(consumerGroup).members().size
            val sg = admin.describeShareGroups(listOf(shareGroup)).all().get().getValue(shareGroup).members().size
            if (cg == 3 && sg == 3) return
        } catch (e: Exception) {
            // the groups don't exist yet
        }
        Thread.sleep(200)
    }
}
