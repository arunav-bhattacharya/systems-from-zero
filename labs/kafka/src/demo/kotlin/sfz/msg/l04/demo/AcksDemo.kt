package sfz.msg.l04.demo

import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.serialization.StringSerializer
import java.util.concurrent.ExecutionException

/**
 * Sends one payment to the three-node cluster (env/kafka-cluster.yml) with the acks you pass: all (default) or 1.
 * Prints where it landed, or why the broker refused it.
 */
fun main(args: Array<String>) {
    val acks = args.firstOrNull() ?: "all"
    val config = mapOf<String, Any>(
        "bootstrap.servers" to "localhost:29092,localhost:39092,localhost:49092",
        "key.serializer" to StringSerializer::class.java,
        "value.serializer" to StringSerializer::class.java,
        "acks" to acks,
        // give up after 10 s instead of the default 2 minutes, so a refusal shows up quickly
        "delivery.timeout.ms" to 10_000,
        "request.timeout.ms" to 5_000,
    )
    KafkaProducer<String, String>(config).use { producer ->
        try {
            val md = producer.send(ProducerRecord("payments", "acct-17", "auth 40.00 EUR")).get()
            println("acks=$acks: written to partition ${md.partition()} at offset ${md.offset()}")
        } catch (e: ExecutionException) {
            val cause = e.cause!!
            println("acks=$acks: refused with ${cause::class.simpleName}\n  ${cause.message}")
        }
    }
}
