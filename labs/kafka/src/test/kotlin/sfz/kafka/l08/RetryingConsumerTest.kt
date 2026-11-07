package sfz.kafka.l08

import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.MockConsumer
import org.apache.kafka.clients.producer.MockProducer
import org.apache.kafka.common.Cluster
import org.apache.kafka.common.KafkaException
import org.apache.kafka.common.Node
import org.apache.kafka.common.PartitionInfo
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.serialization.StringSerializer
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import java.time.Duration

/**
 * The retrying consumer against MockConsumer and MockProducer: no broker, and no real waiting either, because the
 * test passes a `sleep` that only records how long the consumer asked to wait.
 */
class RetryingConsumerTest {
    private val tp = TopicPartition("payments", 0)
    private val poll = Duration.ofMillis(10)

    /** A value the handler can't parse: the poison pill. */
    private val poison = "pay-0004,acct-4,12x50"

    private fun consumerWith(values: List<Pair<String, String>>, maxPollRecords: Long = 500): MockConsumer<String, String> {
        val c = MockConsumer<String, String>("earliest")
        c.assign(listOf(tp))
        c.updateBeginningOffsets(mapOf(tp to 0L))
        c.setMaxPollRecords(maxPollRecords)
        values.forEachIndexed { offset, (key, value) -> c.addRecord(ConsumerRecord("payments", 0, offset.toLong(), key, value)) }
        return c
    }

    /** A MockProducer that knows the DLT topic (one partition), so it can pick a partition for keyed records. */
    private fun dltProducer(): MockProducer<String, String> {
        val node = Node(0, "localhost", 9092)
        val cluster = Cluster("test", listOf(node), listOf(PartitionInfo("payments.DLT", 0, node, arrayOf(node), arrayOf(node))), emptySet(), emptySet())
        return MockProducer(cluster, true, null, StringSerializer(), StringSerializer())
    }

    /** pay-0000 .. pay-0009, one account each, except where [overrides] says otherwise. */
    private fun payments(vararg overrides: Pair<Int, Pair<String, String>>): List<Pair<String, String>> {
        val o = overrides.toMap()
        return (0 until 10).map { i -> o[i] ?: ("acct-$i" to "pay-%04d,acct-$i,1000".format(i)) }
    }

    private val processed = mutableListOf<Long>()
    private val slept = mutableListOf<Duration>()

    private fun parseAndRecord(r: ConsumerRecord<String, String>) {
        val amount = r.value().split(",")[2].toLong() // throws NumberFormatException on the poison pill
        check(amount > 0)
        processed += r.offset()
    }

    private fun retrying(c: MockConsumer<String, String>, p: MockProducer<String, String>, handler: (ConsumerRecord<String, String>) -> Unit) =
        RetryingConsumer(c, p, "payments.DLT", 3, { n -> Duration.ofMillis(100L shl (n - 1)) }, { slept += it }, handler)

    @Test
    fun `a poison pill goes to the dead-letter topic and every other record is processed in order`() {
        val c = consumerWith(payments(4 to ("acct-4" to poison)))
        val p = dltProducer()
        assertThat(retrying(c, p, ::parseAndRecord).pollOnce(poll)).isEqualTo(10)

        assertThat(processed).containsExactly(0, 1, 2, 3, 5, 6, 7, 8, 9)
        assertThat(p.history()).hasSize(1)
        val dl = p.history().single()
        assertThat(dl.value()).isEqualTo(poison)
        assertThat(DeadLetters.header(dl.headers(), DeadLetters.ORIGINAL_OFFSET)).isEqualTo("4")
        assertThat(DeadLetters.header(dl.headers(), DeadLetters.EXCEPTION_CLASS)).isEqualTo("java.lang.NumberFormatException")
        assertThat(c.committed(setOf(tp))[tp]?.offset()).isEqualTo(10L) // the bookmark moved past the poison pill
        assertThat(slept).isEmpty()                                       // bad data is never retried
    }

    @Test
    fun `a transient failure is retried with backoff and then succeeds`() {
        var failuresLeft = 2
        val c = consumerWith(payments())
        val p = dltProducer()
        retrying(c, p) { r ->
            if (r.offset() == 3L && failuresLeft-- > 0) throw TransientFailure("card issuer timed out")
            parseAndRecord(r)
        }.pollOnce(poll)

        assertThat(processed).containsExactly(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
        assertThat(slept).containsExactly(Duration.ofMillis(100), Duration.ofMillis(200))
        assertThat(p.history()).isEmpty()
    }

    @Test
    fun `a transient failure that never clears is given up after maxAttempts calls`() {
        var calls = 0
        val c = consumerWith(payments())
        val p = dltProducer()
        retrying(c, p) { r ->
            if (r.offset() == 3L) { calls++; throw TransientFailure("card issuer timed out") }
            parseAndRecord(r)
        }.pollOnce(poll)

        assertThat(calls).isEqualTo(3)
        assertThat(slept).containsExactly(Duration.ofMillis(100), Duration.ofMillis(200)) // no wait after the last try
        assertThat(DeadLetters.header(p.history().single().headers(), DeadLetters.EXCEPTION_CLASS))
            .isEqualTo(TransientFailure::class.java.name)
        assertThat(processed).hasSize(9)
    }

    @Test
    fun `later payments of a failed account are parked behind it, other accounts carry on`() {
        val c = consumerWith(
            payments(2 to ("acct-42" to "pay-0002,acct-42,12x50"), 5 to ("acct-42" to "pay-0005,acct-42,500"), 8 to ("acct-42" to "pay-0008,acct-42,700")),
            maxPollRecords = 6,
        )
        val p = dltProducer()
        val rc = retrying(c, p, ::parseAndRecord)
        rc.pollOnce(poll) // offsets 0..5
        rc.pollOnce(poll) // offsets 6..9: the parked key is remembered across polls

        assertThat(processed).containsExactly(0, 1, 3, 4, 6, 7, 9)
        assertThat(p.history().map { DeadLetters.header(it.headers(), DeadLetters.ORIGINAL_OFFSET) }).containsExactly("2", "5", "8")
        val parkedBehind = p.history().drop(1).map { DeadLetters.header(it.headers(), DeadLetters.EXCEPTION_MESSAGE) }
        assertThat(parkedBehind).containsOnly("key is parked behind payments-0@2")
        assertThat(DeadLetters.header(p.history()[1].headers(), DeadLetters.EXCEPTION_CLASS)).isEqualTo(ParkedKeyException::class.java.name)
        assertThat(rc.parked).isEqualTo(mapOf("acct-42" to "payments-0@2"))
        assertThat(c.committed(setOf(tp))[tp]?.offset()).isEqualTo(10L)
    }

    @Test
    fun `if the dead letter can't be written, nothing is committed`() {
        val c = consumerWith(payments(4 to ("acct-4" to poison)))
        val p = dltProducer()
        p.sendException = KafkaException("DLT unavailable")
        assertThatThrownBy { retrying(c, p, ::parseAndRecord).pollOnce(poll) }.isInstanceOf(Exception::class.java)
        assertThat(c.committed(setOf(tp))[tp]).isNull() // the batch is read again after a restart
    }

    @Test
    fun `an empty poll commits nothing`() {
        val c = consumerWith(emptyList())
        assertThat(retrying(c, dltProducer(), ::parseAndRecord).pollOnce(poll)).isZero()
        assertThat(c.committed(setOf(tp))[tp]).isNull()
    }
}
