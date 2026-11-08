package sfz.msg.l11

import org.apache.kafka.clients.consumer.AcknowledgeType
import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.KafkaShareConsumer
import org.apache.kafka.clients.admin.NewTopic
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import sfz.kafka.support.KafkaSupport
import java.time.Duration
import java.util.UUID

/**
 * A Kafka 4.4 broker's share groups next to your model: the same steps on both, the same outcome. The broker
 * also writes the archived record to the group's dead-letter queue (share.version 2, new in 4.4).
 */
class ShareGroupOnBrokerTest {
    companion object {
        @JvmStatic
        @BeforeAll
        fun startBroker() = KafkaSupport.start()
    }

    private fun id() = UUID.randomUUID().toString().take(8)

    private fun notifications(n: Int): String {
        val topic = KafkaSupport.newTopic("notifications", 1)
        KafkaSupport.producer().use { p -> for (i in 0 until n) p.send(ProducerRecord(topic, 0, "acct-$i", "notify-$i")).get() }
        return topic
    }

    private fun explicit(group: String, maxRecords: Int) = KafkaSupport.shareConsumer(group, mapOf(
        "share.acknowledgement.mode" to "explicit",   // every record gets an ACCEPT, RELEASE, REJECT or RENEW
        "share.acquire.mode" to "record_limit",       // the broker locks at most max.poll.records per fetch
        "max.poll.records" to maxRecords,
    ))

    private fun pollUntil(c: KafkaShareConsumer<String, String>, done: (List<ConsumerRecord<String, String>>) -> Boolean): List<ConsumerRecord<String, String>> {
        val got = mutableListOf<ConsumerRecord<String, String>>()
        val deadline = System.nanoTime() + Duration.ofSeconds(40).toNanos()
        while (!done(got) && System.nanoTime() < deadline) got += c.poll(Duration.ofMillis(500))
        return got
    }

    @Test
    fun `two share consumers read one partition at the same time, like the model says`() {
        val topic = notifications(9)
        val group = "notify-${id()}"
        KafkaSupport.setGroupConfig(group, mapOf("share.auto.offset.reset" to "earliest"))

        val model = SharePartition(5, 30_000, 2000).also { it.append(9) }
        val modelA = model.acquire("a", 2, 0).map { it.offset() }
        val modelB = model.acquire("b", 500, 0).map { it.offset() }

        explicit(group, 2).use { a ->
            a.subscribe(listOf(topic))
            val heldByA = pollUntil(a) { it.isNotEmpty() }        // a holds these and doesn't acknowledge yet
            KafkaSupport.shareConsumer(group).use { b ->          // implicit mode: the next poll accepts
                b.subscribe(listOf(topic))
                val gotByB = pollUntil(b) { it.size >= 7 }
                assertThat(heldByA.map { it.offset() }).isEqualTo(modelA)            // [0, 1]
                assertThat(gotByB.map { it.offset() }.sorted()).isEqualTo(modelB)   // [2 .. 8]: same partition
                b.commitSync()
            }
            heldByA.forEach { a.acknowledge(it, AcknowledgeType.ACCEPT) }
            a.commitSync()
        }
    }

    @Test
    fun `a record released every time is delivered five times, then archived to the DLQ, like the model says`() {
        val topic = notifications(3)
        val group = "notify-${id()}"
        val dlq = "dlq.$topic"   // the broker's default rule: DLQ topic names start with dlq.
        KafkaSupport.admin().use {
            it.createTopics(listOf(NewTopic(dlq, 1, 1.toShort()).configs(mapOf("errors.deadletterqueue.group.enable" to "true")))).all().get()
        }
        KafkaSupport.awaitLeaders(dlq, 1)
        KafkaSupport.setGroupConfig(group, mapOf("share.auto.offset.reset" to "earliest", "errors.deadletterqueue.topic.name" to dlq))

        // the model: release offset 0 every time, accept the others
        val model = SharePartition(5, 30_000, 2000).also { it.append(3) }
        val modelCounts = mutableListOf<Int>()
        for (t in 0L until 10L) for (d in model.acquire("c", 500, t)) {
            if (d.offset() == 0L) modelCounts += d.deliveryCount()
            model.acknowledge("c", d.offset(), if (d.offset() == 0L) AcknowledgeType.RELEASE else AcknowledgeType.ACCEPT, t)
        }
        assertThat(model.state(0)).isEqualTo(SharePartition.State.ARCHIVED)

        // the broker: the same
        val brokerCounts = mutableListOf<Int>()
        explicit(group, 500).use { c ->
            c.subscribe(listOf(topic))
            var others = 0
            val deadline = System.nanoTime() + Duration.ofSeconds(40).toNanos()
            while ((brokerCounts.size < 5 || others < 2) && System.nanoTime() < deadline) {
                val batch = c.poll(Duration.ofMillis(500))
                for (r in batch) {
                    if (r.offset() == 0L) brokerCounts += r.deliveryCount().get().toInt() else others++
                    c.acknowledge(r, if (r.offset() == 0L) AcknowledgeType.RELEASE else AcknowledgeType.ACCEPT)
                }
                if (!batch.isEmpty) c.commitSync()
            }
            for (i in 0 until 4) for (r in c.poll(Duration.ofMillis(500))) brokerCounts += -1 // offset 0 must not come back
        }
        assertThat(brokerCounts).isEqualTo(modelCounts).containsExactly(1, 2, 3, 4, 5)

        // and the broker wrote a DLQ record that says where the record came from and how often it was tried
        KafkaSupport.consumer().use { c ->
            val tp = TopicPartition(dlq, 0)
            c.assign(listOf(tp))
            val got = mutableListOf<ConsumerRecord<String, String>>()
            val deadline = System.nanoTime() + Duration.ofSeconds(20).toNanos()
            while (got.isEmpty() && System.nanoTime() < deadline) got += c.poll(Duration.ofMillis(500))
            val headers = got.single().headers().associate { it.key() to String(it.value()) }
            assertThat(headers).containsEntry("__dlq.errors.topic", topic).containsEntry("__dlq.errors.offset", "0")
                .containsEntry("__dlq.errors.delivery.count", "5").containsEntry("__dlq.errors.group", group)
        }
    }
}
