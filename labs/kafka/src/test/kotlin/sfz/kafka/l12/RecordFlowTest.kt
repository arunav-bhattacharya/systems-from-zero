package sfz.kafka.l12

import kotlinx.coroutines.flow.take
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.ConsumerRecords
import org.apache.kafka.clients.consumer.MockConsumer
import org.apache.kafka.common.KafkaException
import org.apache.kafka.common.TopicPartition
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import java.time.Duration
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Your Flow wrapper around a consumer: here a MockConsumer whose poll blocks like a real one until wakeup(). */
class RecordFlowTest {
    private val tp = TopicPartition("notifications", 0)

    /** Remembers which threads called it; an empty poll waits for the whole timeout, unless wakeup() comes first. */
    private class WatchedConsumer : MockConsumer<String, String>("earliest") {
        // in tests, kotlinx.coroutines adds " @coroutine#3" to thread names while a coroutine runs: drop it
        private fun thread() = Thread.currentThread().name.substringBefore(" @")

        val threads: MutableSet<String> = ConcurrentHashMap.newKeySet()
        @Volatile var wakeups = 0
        @Volatile var closedOn: String? = null
        private val woken = CountDownLatch(1)

        override fun poll(timeout: Duration): ConsumerRecords<String, String> {
            threads += thread()
            val batch = super.poll(timeout)
            if (!batch.isEmpty) return batch
            woken.await(timeout.toMillis(), TimeUnit.MILLISECONDS) // a real poll blocks here
            return super.poll(Duration.ZERO)                       // throws WakeupException after wakeup()
        }

        override fun wakeup() {
            wakeups++
            super.wakeup()
            woken.countDown()
        }

        override fun close() {
            closedOn = thread()
            super.close()
        }
    }

    private fun consumer(records: Int) = WatchedConsumer().apply {
        assign(listOf(tp))
        updateBeginningOffsets(mapOf(tp to 0L))
        for (i in 0 until records) addRecord(ConsumerRecord(tp.topic(), 0, i.toLong(), "acct-$i", "notify-$i"))
    }

    @Test
    fun `records come out in poll order`() = runBlocking<Unit> {
        val c = consumer(5)
        val got = withTimeout(10_000) { c.records(Duration.ofMillis(50)).take(5).toList() }
        assertThat(got.map { it.offset() }).containsExactly(0L, 1L, 2L, 3L, 4L)
    }

    @Test
    fun `every call on the consumer runs on the kafka-poll thread`() = runBlocking<Unit> {
        val c = consumer(3)
        withTimeout(10_000) { c.records(Duration.ofMillis(50)).take(3).toList() }
        assertThat(c.threads).containsExactly(POLL_THREAD)
        assertThat(c.closedOn).isEqualTo(POLL_THREAD)
    }

    @Test
    fun `stopping the collection wakes a blocked poll and closes the consumer at once`() = runBlocking<Unit> {
        val c = consumer(3)
        val start = System.nanoTime()
        // a 30-second poll timeout: without wakeup() the flow could not end for 30 seconds
        val got = withTimeout(10_000) { c.records(Duration.ofSeconds(30)).take(3).toList() }
        assertThat(got).hasSize(3)
        assertThat(Duration.ofNanos(System.nanoTime() - start)).isLessThan(Duration.ofSeconds(5))
        assertThat(c.wakeups).isGreaterThanOrEqualTo(1)
        assertThat(c.closed()).isTrue()
    }

    @Test
    fun `cancelling the collecting coroutine stops the loop too`() = runBlocking<Unit> {
        val c = consumer(1)
        val first = CountDownLatch(1)
        val job = launch { c.records(Duration.ofSeconds(30)).collect { first.countDown() } }
        withTimeout(10_000) { while (first.count > 0) kotlinx.coroutines.delay(10) }
        job.cancel()
        withTimeout(5_000) { job.join() }
        assertThat(c.wakeups).isGreaterThanOrEqualTo(1)
        assertThat(c.closed()).isTrue()
    }

    @Test
    fun `an error from poll reaches the collector, and the consumer is still closed`() {
        val c = consumer(0)
        c.setPollException(KafkaException("broker gone"))
        assertThatThrownBy { runBlocking { withTimeout(10_000) { c.records(Duration.ofMillis(50)).toList() } } }
            .isInstanceOf(KafkaException::class.java).hasMessageContaining("broker gone")
        assertThat(c.closed()).isTrue()
    }
}
