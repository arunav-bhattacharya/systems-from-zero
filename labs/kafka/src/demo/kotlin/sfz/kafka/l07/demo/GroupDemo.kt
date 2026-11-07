package sfz.kafka.l07.demo

import org.apache.kafka.clients.admin.Admin
import org.apache.kafka.clients.admin.NewTopic
import org.apache.kafka.clients.consumer.ConsumerRebalanceListener
import org.apache.kafka.clients.consumer.CooperativeStickyAssignor
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.consumer.OffsetAndMetadata
import org.apache.kafka.clients.consumer.RangeAssignor
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.KafkaException
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import java.time.Duration
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicLong
import kotlin.concurrent.thread

private var start = System.nanoTime()
private fun log(msg: String) = println("%5.1fs  %s".format((System.nanoTime() - start) / 1e9, msg))

/**
 * Three consumers join a new group on the 6-partition topic "ledger-rebalance", one after the other. Each prints what
 * the group gives it and takes away. Before a partition leaves, its listener commits how far it got: the handover.
 * Arguments: "consumer" (the new protocol, the default), "cooperative" (classic, CooperativeStickyAssignor)
 * or "eager" (classic, RangeAssignor); then "nohandover" to skip the commit when a partition leaves.
 */
fun main(args: Array<String>) {
    val mode = args.firstOrNull() ?: "consumer"
    val handover = args.getOrNull(1) != "nohandover"
    val topic = "ledger-rebalance"
    Admin.create(mapOf<String, Any>("bootstrap.servers" to "localhost:9092")).use { admin ->
        if (topic !in admin.listTopics().names().get()) admin.createTopics(listOf(NewTopic(topic, 6, 1.toShort()))).all().get()
    }
    KafkaProducer<String, String>(
        mapOf("bootstrap.servers" to "localhost:9092", "key.serializer" to StringSerializer::class.java, "value.serializer" to StringSerializer::class.java),
    ).use { p -> for (part in 0 until 6) repeat(10) { p.send(ProducerRecord(topic, part, "acct-$part", "pay-$it")) } }
    val total = KafkaConsumer<String, String>(
        mapOf("bootstrap.servers" to "localhost:9092", "key.deserializer" to StringDeserializer::class.java, "value.deserializer" to StringDeserializer::class.java),
    ).use { c -> c.endOffsets((0 until 6).map { TopicPartition(topic, it) }).values.sum() } // every record so far

    val config = mapOf<String, Any>(
        "bootstrap.servers" to "localhost:9092",
        "group.id" to "ledger-$mode-${System.currentTimeMillis()}", // a new group every run
        "key.deserializer" to StringDeserializer::class.java,
        "value.deserializer" to StringDeserializer::class.java,
        "enable.auto.commit" to false,
        "auto.offset.reset" to "earliest",
    ) + when (mode) {
        "eager" -> mapOf("partition.assignment.strategy" to RangeAssignor::class.java.name)
        "cooperative" -> mapOf("partition.assignment.strategy" to CooperativeStickyAssignor::class.java.name)
        else -> mapOf("group.protocol" to "consumer")
    }
    println("mode $mode, group ${config["group.id"]}" + if (handover) "" else ", no handover commits")

    val owned = ConcurrentHashMap<String, Set<Int>>()   // what each member owns now
    val revoked = ConcurrentHashMap<String, Int>()      // how many partitions each member has handed back
    val stop = AtomicBoolean(false)
    val processed = AtomicLong()                        // records processed by the whole group
    val members = mutableListOf<Thread>()
    start = System.nanoTime() // the clock starts when c1 joins
    for (name in listOf("c1", "c2", "c3")) {
        log("$name joins")
        members += thread { runMember(name, config + ("client.id" to name), topic, handover, owned, revoked, processed, stop) }
        val n = members.size
        val deadline = System.nanoTime() + 30_000_000_000L
        // wait until the group is balanced again, and has read every record
        while (!(owned.size == n && owned.values.all { it.size == 6 / n } && processed.get() >= total) && System.nanoTime() < deadline) Thread.sleep(50)
    }
    Thread.sleep(1_000) // let the last heartbeats settle before everyone leaves
    stop.set(true)
    members.forEach { it.join() }
    println("partitions handed back: $revoked, ${revoked.values.sum()} in all")
    println("records processed: ${processed.get()}, records in the topic: $total")
}

private fun runMember(
    name: String, config: Map<String, Any>, topic: String, handover: Boolean,
    owned: MutableMap<String, Set<Int>>, revoked: MutableMap<String, Int>, processed: AtomicLong, stop: AtomicBoolean,
) {
    try {
        memberLoop(name, config, topic, handover, owned, revoked, processed, stop)
    } catch (e: KafkaException) {
        if (!stop.get()) throw e // closing while the group still moves partitions is harmless at the end of a demo
    }
}

private fun memberLoop(
    name: String, config: Map<String, Any>, topic: String, handover: Boolean,
    owned: MutableMap<String, Set<Int>>, revoked: MutableMap<String, Int>, processed: AtomicLong, stop: AtomicBoolean,
) {
    KafkaConsumer<String, String>(config).use { c ->
        c.subscribe(listOf(topic), object : ConsumerRebalanceListener {
            override fun onPartitionsRevoked(partitions: Collection<TopicPartition>) {
                if (partitions.isEmpty()) return
                // the loop below processes every record it polls, so the position is how far this member got
                if (handover) c.commitSync(partitions.associateWith { OffsetAndMetadata(c.position(it)) })
                if (!stop.get()) {                       // closing at the end: commit, but stay quiet
                    revoked.merge(name, partitions.size, Int::plus)
                    log("$name revoked  ${partitions.map { it.partition() }.sorted()}" +
                        if (handover) ", committed ${partitions.sortedBy { it.partition() }.map { c.position(it) }}" else ", committed nothing")
                }
                owned[name] = owned[name].orEmpty() - partitions.map { it.partition() }.toSet()
            }

            override fun onPartitionsAssigned(partitions: Collection<TopicPartition>) {
                val now = c.assignment().map { it.partition() }.toSet()
                if (partitions.isNotEmpty()) {
                    val from = partitions.sortedBy { it.partition() }.map { c.position(it) } // the committed offsets
                    log("$name assigned ${partitions.map { it.partition() }.sorted()}, starts at $from, owns ${now.sorted()}")
                }
                owned[name] = now
            }
        })
        while (!stop.get()) processed.addAndGet(c.poll(Duration.ofMillis(100)).count().toLong()) // "processing" is free here
    }
}
