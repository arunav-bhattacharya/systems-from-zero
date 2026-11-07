package sfz.kafka.l12.demo

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.asCoroutineDispatcher
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.channelFlow
import kotlinx.coroutines.flow.take
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withContext
import org.apache.kafka.clients.admin.Admin
import org.apache.kafka.clients.admin.NewTopic
import org.apache.kafka.clients.consumer.Consumer
import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.errors.WakeupException
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import java.time.Duration
import java.util.concurrent.Executors

/**
 * A real KafkaConsumer behind a Kotlin Flow: poll runs on its own thread, the collector on Dispatchers.Default,
 * and when the collector has had enough, wakeup() ends a poll that would otherwise block for 10 seconds.
 */
fun main() = runBlocking {
    val bootstrap = "localhost:9092"
    val tp = TopicPartition("notifications-${System.currentTimeMillis() % 100_000}", 0)
    Admin.create(mapOf<String, Any>("bootstrap.servers" to bootstrap)).use { it.createTopics(listOf(NewTopic(tp.topic(), 1, 1.toShort()))).all().get() }
    KafkaProducer(mapOf<String, Any>("bootstrap.servers" to bootstrap), StringSerializer(), StringSerializer()).use { p ->
        repeat(5) { p.send(ProducerRecord(tp.topic(), 0, "acct-$it", "notify-$it")).get() }
    }
    val consumer = KafkaConsumer(mapOf<String, Any>("bootstrap.servers" to bootstrap), StringDeserializer(), StringDeserializer())
    consumer.assign(listOf(tp))
    consumer.seekToBeginning(listOf(tp))

    var lastRecordAt = 0L
    withContext(Dispatchers.Default) {                 // the collector runs on a pool thread, not on kafka-poll
        consumer.records(Duration.ofSeconds(10))
            .take(5)
            .collect { r ->
                println("collector got offset ${r.offset()} on ${thread()}")
                lastRecordAt = System.nanoTime()
            }
    }
    println("the flow ended %.0f ms after the fifth record, although poll's timeout is 10 s".format((System.nanoTime() - lastRecordAt) / 1e6))
}

/** The lab's wrapper, in short: one thread owns the consumer; wakeup() unblocks it when the collector goes away. */
fun <K, V> Consumer<K, V>.records(pollTimeout: Duration): Flow<ConsumerRecord<K, V>> = channelFlow {
    val executor = Executors.newSingleThreadExecutor { Thread(it, "kafka-poll") }
    val consumer = this@records
    launch(executor.asCoroutineDispatcher()) {
        try {
            while (isActive) {
                val batch = consumer.poll(pollTimeout)
                if (!batch.isEmpty) println("poll returned ${batch.count()} records on ${thread()}")
                for (r in batch) send(r)
            }
        } catch (e: WakeupException) {
            println("poll on ${thread()} threw WakeupException: the collector is done")
        } finally {
            withContext(NonCancellable) { consumer.close() }
            println("consumer closed on ${thread()}")
        }
    }.invokeOnCompletion { executor.shutdown() }
    awaitClose { consumer.wakeup() }
}

private fun thread() = Thread.currentThread().name.substringBefore(" @")
