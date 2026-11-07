package sfz.kafka.l10

import org.apache.kafka.common.serialization.LongSerializer
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import org.apache.kafka.streams.KeyValue
import org.apache.kafka.streams.StreamsConfig
import org.apache.kafka.streams.TestInputTopic
import org.apache.kafka.streams.TopologyTestDriver
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Duration
import java.time.Instant
import java.nio.file.Files
import java.nio.file.Path
import java.util.Properties

/**
 * Your fraud rule in TopologyTestDriver: more than 3 debits per account in a one-minute tumbling window, with a
 * 30-second grace period. Every record carries its own timestamp, so the tests control event time exactly.
 */
class FraudRuleTest {
    private lateinit var driver: TopologyTestDriver
    private lateinit var payments: TestInputTopic<String, Long>

    private val stateDir: Path = Files.createTempDirectory("sfz-l10-")

    @BeforeEach
    fun setUp() {
        val props = Properties().apply {
            put(StreamsConfig.STATE_DIR_CONFIG, stateDir.toString()) // a directory of its own: RocksDB locks it
            put(StreamsConfig.APPLICATION_ID_CONFIG, "fraud-app")
            put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "unused:9092")
            put(StreamsConfig.STATESTORE_CACHE_MAX_BYTES_CONFIG, 0)
        }
        driver = TopologyTestDriver(FraudRule.build(Duration.ofMinutes(1), Duration.ofSeconds(30), 3), props)
        payments = driver.createInputTopic(FraudRule.PAYMENTS, StringSerializer(), LongSerializer())
    }

    @AfterEach
    fun tearDown() {
        if (::driver.isInitialized) driver.close()
        stateDir.toFile().deleteRecursively()
    }

    /** 10:mm:ss on the day of the tests, in UTC. */
    private fun at(time: String): Instant = Instant.parse("2026-11-07T$time.000Z")

    private fun debit(account: String, time: String, cents: Long = -2_500) = payments.pipeInput(account, cents, at(time))

    private fun alerts(): List<KeyValue<String, String>> =
        driver.createOutputTopic(FraudRule.ALERTS, StringDeserializer(), StringDeserializer()).readKeyValuesToList()

    @Test
    fun `four debits in one minute raise an alert`() {
        for (t in listOf("10:00:05", "10:00:20", "10:00:40", "10:00:55")) debit("acct-7", t)
        assertThat(alerts()).containsExactly(KeyValue("acct-7", "4 debits in 2026-11-07T10:00:00Z/2026-11-07T10:01:00Z"))
    }

    @Test
    fun `three debits do not, and credits never count`() {
        for (t in listOf("10:00:05", "10:00:20", "10:00:40")) debit("acct-7", t)
        payments.pipeInput("acct-7", 10_000L, at("10:00:50")) // a refund: not a debit
        assertThat(alerts()).isEmpty()
    }

    @Test
    fun `every debit above the limit raises another alert`() {
        for (t in listOf("10:00:05", "10:00:10", "10:00:15", "10:00:20", "10:00:25")) debit("acct-7", t)
        assertThat(alerts().map { it.value }).containsExactly(
            "4 debits in 2026-11-07T10:00:00Z/2026-11-07T10:01:00Z",
            "5 debits in 2026-11-07T10:00:00Z/2026-11-07T10:01:00Z",
        )
    }

    @Test
    fun `windows are aligned to the clock, not to the first debit`() {
        // four debits within 30 seconds, but two fall in [10:00, 10:01) and two in [10:01, 10:02)
        for (t in listOf("10:00:40", "10:00:50", "10:01:05", "10:01:10")) debit("acct-7", t)
        assertThat(alerts()).isEmpty()
    }

    @Test
    fun `each account is counted on its own`() {
        for (t in listOf("10:00:05", "10:00:20")) debit("acct-7", t)
        for (t in listOf("10:00:30", "10:00:40")) debit("acct-8", t)
        assertThat(alerts()).isEmpty()
    }

    @Test
    fun `a late debit inside the grace period still counts`() {
        for (t in listOf("10:00:05", "10:00:20", "10:00:40")) debit("acct-7", t)
        debit("acct-9", "10:01:20")  // another account moves stream time to 10:01:20
        debit("acct-7", "10:00:55")  // late, but the window [10:00, 10:01) stays open until 10:01:30
        assertThat(alerts()).containsExactly(KeyValue("acct-7", "4 debits in 2026-11-07T10:00:00Z/2026-11-07T10:01:00Z"))
    }

    @Test
    fun `a debit later than the grace period is dropped`() {
        for (t in listOf("10:00:05", "10:00:20", "10:00:40")) debit("acct-7", t)
        debit("acct-9", "10:01:40")  // stream time 10:01:40: the window [10:00, 10:01) closed at 10:01:30
        debit("acct-7", "10:00:55")  // too late: no window takes it
        assertThat(alerts()).isEmpty()
    }
}
