package sfz.msg.l06

import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerConfig
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.config.ConfigException
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import sfz.kafka.support.KafkaSupport

/**
 * What your two models describe, on a real Kafka 4.4 producer and broker. These tests need no code from you:
 * they read the producer's own metrics and ask the broker what it knows about each producer.
 */
class ProducerOnBrokerTest {
    companion object {
        @JvmStatic
        @BeforeAll
        fun startBroker() = KafkaSupport.start()

        /** A small payment event, about 100 bytes, that compresses well (like real JSON events). */
        fun payment(i: Int) = """{"id":"pay-$i","account":"acct-${i % 50}","amount":4000,"currency":"EUR","type":"auth"}"""

        /** A metric from the producer's "producer-metrics" group, as a Double. */
        fun KafkaProducer<String, String>.metric(name: String): Double =
            metrics().entries.single { it.key.group() == "producer-metrics" && it.key.name() == name }.value.metricValue() as Double
    }

    /**
     * Sends 300 records one per millisecond (about 1,000 a second) and returns two metrics:
     * records-per-request-avg and record-queue-time-avg (how long a batch waited in the accumulator, in ms).
     */
    private fun trickle(lingerMs: Int): Pair<Double, Double> {
        val topic = KafkaSupport.newTopic("ledger")
        return KafkaSupport.producer(mapOf(ProducerConfig.LINGER_MS_CONFIG to lingerMs)).use { p ->
            val acks = (0 until 300).map { i -> p.send(ProducerRecord(topic, "acct-1", payment(i))).also { Thread.sleep(1) } }
            acks.forEach { it.get() }
            p.metric("records-per-request-avg") to p.metric("record-queue-time-avg")
        }
    }

    @Test
    fun `at about 1,000 records a second, a longer linger puts more records in each request and makes each batch wait`() {
        val (noneRecords, noneWait) = trickle(0)
        val (fiftyRecords, fiftyWait) = trickle(50)
        // a batch that isn't full waits at least linger.ms, however busy the laptop is
        assertThat(fiftyWait).isGreaterThanOrEqualTo(45.0)
        assertThat(noneWait).isLessThan(45.0)
        // the model says about 1 and about 50 records; a busy machine blurs that, so only the order is checked
        assertThat(fiftyRecords).isGreaterThan(noneRecords)
        assertThat(fiftyRecords).isGreaterThan(5.0)
    }

    @Test
    fun `lz4 shrinks a batch of similar payments, and compression works on whole batches`() {
        val topic = KafkaSupport.newTopic("ledger")
        fun rate(compression: String) = KafkaSupport.producer(
            mapOf(ProducerConfig.COMPRESSION_TYPE_CONFIG to compression, ProducerConfig.LINGER_MS_CONFIG to 20),
        ).use { p ->
            (0 until 2_000).map { p.send(ProducerRecord(topic, "acct-${it % 50}", payment(it))) }.forEach { it.get() }
            p.metric("compression-rate-avg") // compressed size / uncompressed size, per batch
        }
        assertThat(rate("none")).isEqualTo(1.0)
        assertThat(rate("lz4")).isLessThan(0.5)
    }

    @Test
    fun `the default producer is idempotent, so the leader tracks its producer id and last sequence`() {
        val topic = KafkaSupport.newTopic("ledger")
        val tp = TopicPartition(topic, 0)
        KafkaSupport.producer().use { p -> (0 until 100).map { p.send(ProducerRecord(topic, "acct-1", payment(it))) }.forEach { it.get() } }
        val state = KafkaSupport.admin().use { it.describeProducers(listOf(tp)).partitionResult(tp).get().activeProducers() }
        assertThat(state).hasSize(1)
        assertThat(state[0].producerId()).isNotNegative()
        assertThat(state[0].lastSequence()).isEqualTo(99) // sequences 0..99, one per record
    }

    @Test
    fun `acks=1 silently turns idempotence off, so the leader tracks nothing`() {
        val topic = KafkaSupport.newTopic("ledger")
        val tp = TopicPartition(topic, 0)
        KafkaSupport.producer(mapOf(ProducerConfig.ACKS_CONFIG to "1")).use { p ->
            (0 until 100).map { p.send(ProducerRecord(topic, "acct-1", payment(it))) }.forEach { it.get() }
        }
        val state = KafkaSupport.admin().use { it.describeProducers(listOf(tp)).partitionResult(tp).get().activeProducers() }
        assertThat(state).isEmpty() // no producer id, no sequence numbers, no duplicate check
    }

    @Test
    fun `asking for idempotence explicitly turns that silent switch into an error`() {
        assertThatThrownBy {
            KafkaSupport.producer(mapOf(ProducerConfig.ACKS_CONFIG to "1", ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG to true)).close()
        }.isInstanceOf(ConfigException::class.java).hasMessageContaining("acks")
        assertThatThrownBy {
            KafkaSupport.producer(
                mapOf(ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION to 6, ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG to true),
            ).close()
        }.isInstanceOf(ConfigException::class.java).hasMessageContaining("max.in.flight.requests.per.connection")
    }
}
