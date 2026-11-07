package sfz.kafka.l12

import kotlinx.coroutines.asCoroutineDispatcher
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.channelFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.apache.kafka.clients.consumer.Consumer
import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.common.errors.WakeupException
import java.time.Duration
import java.util.concurrent.Executors

/** The name of the thread that owns the consumer. */
const val POLL_THREAD = "kafka-poll"

/**
 * The blocking poll loop as a cold Kotlin [Flow]: collect it, and records arrive one by one in poll order.
 *
 * A `KafkaConsumer` is not thread-safe, and `poll` blocks its thread for up to [pollTimeout]. So:
 *
 * 1. Every call on this consumer (`poll`, then `close`) runs on one dedicated thread named [POLL_THREAD], made for
 *    this collection (a single-thread executor). The collector runs wherever it runs, and records cross over
 *    through the flow's channel, which also slows polling down when the collector is slow.
 * 2. When the collection ends (the collector cancels, or takes what it wanted), the flow calls `wakeup()`: the one
 *    method another thread may call. A `poll` that is blocked at that moment throws `WakeupException` at once, and
 *    the loop ends.
 * 3. Then the consumer is closed, on the poll thread, and the executor is shut down.
 * 4. If `poll` throws anything else, the collector gets that exception, and the consumer is still closed.
 *
 * Commits are not done here: in a real service, commit on the poll thread too (lesson 6), never from the collector.
 */
fun <K, V> Consumer<K, V>.records(pollTimeout: Duration = Duration.ofMillis(100)): Flow<ConsumerRecord<K, V>> =
    TODO("channelFlow: launch the poll loop on a single-thread dispatcher named POLL_THREAD, send each record, " +
        "close the consumer in finally; awaitClose { wakeup() }")
