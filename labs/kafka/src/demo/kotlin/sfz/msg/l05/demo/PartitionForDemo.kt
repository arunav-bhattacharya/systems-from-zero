package sfz.msg.l05.demo

import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.serialization.StringSerializer
import org.apache.kafka.common.utils.Utils

/**
 * For each key: the murmur2 hash, the hash made positive, the partition that arithmetic gives,
 * and the partition the real producer chose when it sent a record with that key to the topic "accounts".
 */
fun main(args: Array<String>) {
    val keys = args.toList().ifEmpty { listOf("acct-17", "acct-42", "acct-99", "card-1") }
    val config = mapOf<String, Any>(
        "bootstrap.servers" to "localhost:9092", // env/kafka.yml
        "key.serializer" to StringSerializer::class.java,
        "value.serializer" to StringSerializer::class.java,
    )
    KafkaProducer<String, String>(config).use { producer ->
        val n = producer.partitionsFor("accounts").size
        println("topic accounts has $n partitions")
        println("%-9s %12s %11s %5s   %s".format("key", "murmur2", "positive", "% $n", "producer chose"))
        for (key in keys) {
            val hash = Utils.murmur2(key.toByteArray(Charsets.UTF_8)) // the bytes StringSerializer sends
            val positive = Utils.toPositive(hash)                     // hash and 0x7fffffff
            val chosen = producer.send(ProducerRecord("accounts", key, "auth 10.00 EUR")).get().partition()
            println("%-9s %12d %11d %5d   partition %d".format(key, hash, positive, positive % n, chosen))
        }
    }
}
