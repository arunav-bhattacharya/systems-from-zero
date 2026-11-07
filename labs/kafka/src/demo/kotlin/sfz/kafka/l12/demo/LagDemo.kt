package sfz.kafka.l12.demo

import org.apache.kafka.clients.admin.Admin
import org.apache.kafka.clients.admin.NewTopic
import org.apache.kafka.clients.admin.OffsetSpec
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import java.time.Duration

/**
 * Consumer lag, computed the way a monitoring tool computes it: for each partition, the log end offset minus the
 * group's committed offset. A settlement group reads 1,000 of 3,000 payments in a 3-partition topic and commits.
 */
fun main() {
    val bootstrap = "localhost:9092"
    val run = System.currentTimeMillis() % 100_000
    val topic = "payments-$run"
    val group = "settlement-$run"
    Admin.create(mapOf<String, Any>("bootstrap.servers" to bootstrap)).use { admin ->
        admin.createTopics(listOf(NewTopic(topic, 3, 1.toShort()))).all().get()
        KafkaProducer(mapOf<String, Any>("bootstrap.servers" to bootstrap), StringSerializer(), StringSerializer()).use { p ->
            for (i in 0 until 3000) p.send(ProducerRecord(topic, "acct-${i % 30}", "pay-$i"))
        }
        KafkaConsumer(mapOf<String, Any>("bootstrap.servers" to bootstrap, "group.id" to group, "group.protocol" to "consumer",
            "auto.offset.reset" to "earliest", "enable.auto.commit" to false, "max.poll.records" to 100),
            StringDeserializer(), StringDeserializer()).use { c ->
            c.subscribe(listOf(topic))
            var read = 0
            while (read < 1000) read += c.poll(Duration.ofMillis(500)).count()
            c.commitSync() // the group's bookmarks: where each partition got to
            println("the settlement group read $read payments and committed")
        }
        // what a lag exporter does: two admin calls, then a subtraction per partition
        val committed = admin.listConsumerGroupOffsets(group).partitionsToOffsetAndMetadata().get()
        val ends = admin.listOffsets(committed.keys.associateWith { OffsetSpec.latest() }).all().get()
        var total = 0L
        for ((tp, offset) in committed.toSortedMap(compareBy { it.partition() })) {
            val end = ends.getValue(tp).offset()
            val lag = end - offset.offset()
            total += lag
            println("partition %d: log end %4d, committed %4d, lag %4d".format(tp.partition(), end, offset.offset(), lag))
        }
        println("total lag $total records")
        println("now try: kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group $group")
    }
}
