package sfz.kafka.l06.demo

import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.errors.WakeupException
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import java.time.Duration
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * Writes 30 payments to "payments", then runs a poll loop in the group "ledger" for 4 seconds.
 * After each poll it prints the position of every partition; after each commit, the committed offsets.
 * Another thread stops the loop with wakeup().
 */
fun main() {
    KafkaProducer<String, String>(
        mapOf(
            "bootstrap.servers" to "localhost:9092",
            "key.serializer" to StringSerializer::class.java,
            "value.serializer" to StringSerializer::class.java,
        ),
    ).use { producer -> repeat(30) { i -> producer.send(ProducerRecord("payments", "acct-${i % 10}", "pay-$i")) } }

    val consumer = KafkaConsumer<String, String>(
        mapOf(
            "bootstrap.servers" to "localhost:9092",
            "key.deserializer" to StringDeserializer::class.java,
            "value.deserializer" to StringDeserializer::class.java,
            "group.id" to "ledger",
            "enable.auto.commit" to false,      // we commit ourselves, after processing
            "auto.offset.reset" to "earliest",  // a group with no committed offset starts at the beginning
            "max.poll.records" to 10,
        ),
    )
    val stopper = Executors.newSingleThreadScheduledExecutor()
    stopper.schedule(consumer::wakeup, 4, TimeUnit.SECONDS) // the only call that is safe from another thread

    try {
        consumer.use { c ->
            c.subscribe(listOf("payments"))
            var n = 0
            while (true) {
                n++
                val records = c.poll(Duration.ofMillis(500))
                val positions = c.assignment().associate { it.partition() to c.position(it) }.toSortedMap()
                println("poll %d: %2d records   positions %s".format(n, records.count(), positions))
                if (records.isEmpty) continue

                records.forEach { /* apply the payment here */ }

                c.commitSync() // commits the positions: the next offset of every partition
                val committed = c.committed(c.assignment()).entries.associate { (tp, om) -> tp.partition() to om?.offset() }
                println("        committed ${committed.toSortedMap()}")
            }
        }
    } catch (e: WakeupException) {
        println("wakeup(): the loop stops and the consumer closes")
    } finally {
        stopper.shutdown()
    }
}
