package sfz.msg.l05.demo

import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import java.time.Duration

private const val TOPIC = "accounts"

/**
 * Sends 1,000 payments for acct-1 .. acct-10 in turn to the topic "accounts", then reads them back with one consumer.
 * Each value starts with its send order (seq). Pass a mode: keys (the default), no-keys or ignore-keys.
 */
fun main(args: Array<String>) {
    val mode = args.firstOrNull() ?: "keys"
    val common = mapOf<String, Any>(
        "bootstrap.servers" to "localhost:9092",
        "key.deserializer" to StringDeserializer::class.java,
        "value.deserializer" to StringDeserializer::class.java,
    )
    val producerConfig = mutableMapOf<String, Any>(
        "bootstrap.servers" to "localhost:9092",
        "key.serializer" to StringSerializer::class.java,
        "value.serializer" to StringSerializer::class.java,
    )
    if (mode == "ignore-keys") producerConfig["partitioner.ignore.keys"] = true

    // 1. note where every partition ends now, so we read back only this run's records
    val start = KafkaConsumer<String, String>(common).use { c ->
        c.endOffsets(c.partitionsFor(TOPIC).map { TopicPartition(TOPIC, it.partition()) })
    }

    // 2. send seq 0..999; the key cycles through the 10 accounts (or is null)
    val sentTo = KafkaProducer<String, String>(producerConfig).use { p ->
        (0 until 1000).map { seq ->
            val key = if (mode == "no-keys") null else "acct-${seq % 10 + 1}"
            p.send(ProducerRecord(TOPIC, key, "$seq," + "x".repeat(80)))
        }.map { it.get().partition() }
    }
    println("mode $mode: 1000 records to $TOPIC (${start.size} partitions)")
    println("in send order: ${runs(sentTo)}")

    // 3. read them back from where this run started, in the order the consumer hands them out
    val seen = mutableListOf<ConsumerRecord<String, String>>()
    KafkaConsumer<String, String>(common).use { c ->
        c.assign(start.keys)
        start.forEach(c::seek)
        val deadline = System.nanoTime() + Duration.ofSeconds(15).toNanos()
        while (seen.size < 1000 && System.nanoTime() < deadline) seen += c.poll(Duration.ofMillis(500))
    }

    // 4. per key: which partitions, and did the consumer see that key's records in send order?
    seen.filter { it.key() != null }.groupBy { it.key() }.toSortedMap(compareBy { it.removePrefix("acct-").toInt() })
        .forEach { (key, records) ->
            val inOrder = records.zipWithNext().all { (a, b) -> seq(a) < seq(b) }
            println("  %-8s partitions %-14s in send order: %s".format(key, records.map { it.partition() }.toSortedSet(), if (inOrder) "yes" else "no"))
        }

    // 5. and the stream as a whole?
    val i = (1 until seen.size).firstOrNull { seq(seen[it]) < seq(seen[it - 1]) }
    if (i == null) println("whole stream: in send order")
    else println("whole stream: out of send order at read #$i (seq ${seq(seen[i])} came right after seq ${seq(seen[i - 1])})")
}

private fun seq(r: ConsumerRecord<String, String>) = r.value().substringBefore(',').toInt()

/** "p3 x153, p0 x152, ..." : how many records in a row went to the same partition. */
private fun runs(partitions: List<Int>): String {
    val out = mutableListOf<String>()
    var count = 1
    for (i in 1..partitions.size) {
        if (i < partitions.size && partitions[i] == partitions[i - 1]) count++
        else { out += "p${partitions[i - 1]} x$count"; count = 1 }
    }
    return out.take(8).joinToString(", ") + (if (out.size > 8) ", ..." else "") + " (${out.size} runs)"
}
