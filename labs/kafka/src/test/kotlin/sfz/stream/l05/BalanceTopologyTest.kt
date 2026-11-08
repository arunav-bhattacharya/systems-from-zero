package sfz.stream.l05

import org.apache.kafka.common.serialization.LongDeserializer
import org.apache.kafka.common.serialization.LongSerializer
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import org.apache.kafka.streams.KeyValue
import org.apache.kafka.streams.StreamsConfig
import org.apache.kafka.streams.TopologyTestDriver
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.nio.file.Files
import java.nio.file.Path
import java.util.Properties

/**
 * Your balance topology in TopologyTestDriver: no broker. The driver feeds records through the topology one at a
 * time and captures what it writes, including the store's changelog topic.
 */
class BalanceTopologyTest {
    private lateinit var driver: TopologyTestDriver

    private val stateDir: Path = Files.createTempDirectory("sfz-stream05-")

    @BeforeEach
    fun setUp() {
        val props = Properties().apply {
            put(StreamsConfig.STATE_DIR_CONFIG, stateDir.toString()) // a directory of its own: RocksDB locks it
            put(StreamsConfig.APPLICATION_ID_CONFIG, "balance-app")
            put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "unused:9092")
            put(StreamsConfig.STATESTORE_CACHE_MAX_BYTES_CONFIG, 0) // no record cache: every update goes downstream
        }
        driver = TopologyTestDriver(BalanceTopology.build(), props)
    }

    @AfterEach
    fun tearDown() {
        if (::driver.isInitialized) driver.close()
        stateDir.toFile().deleteRecursively()
    }

    private fun pay(vararg payments: Pair<String, Long>) {
        val input = driver.createInputTopic(BalanceTopology.PAYMENTS, StringSerializer(), LongSerializer())
        for ((account, cents) in payments) input.pipeInput(account, cents)
    }

    private fun read(topic: String): List<KeyValue<String, Long>> =
        driver.createOutputTopic(topic, StringDeserializer(), LongDeserializer()).readKeyValuesToList()

    @Test
    fun `the balance is the sum of the account's payments`() {
        pay("acct-1" to 10_000, "acct-1" to -3_000, "acct-1" to 500)
        val store = driver.getKeyValueStore<String, Long>(BalanceTopology.STORE)
        assertThat(store.get("acct-1")).isEqualTo(7_500L)
    }

    @Test
    fun `every payment produces one balance update, in order`() {
        pay("acct-1" to 10_000, "acct-1" to -3_000, "acct-1" to 500)
        assertThat(read(BalanceTopology.BALANCES)).containsExactly(
            KeyValue("acct-1", 10_000L), KeyValue("acct-1", 7_000L), KeyValue("acct-1", 7_500L),
        )
    }

    @Test
    fun `each account has its own balance`() {
        pay("acct-1" to 10_000, "acct-2" to 5_000, "acct-1" to -3_000, "acct-2" to -2_000)
        val store = driver.getKeyValueStore<String, Long?>(BalanceTopology.STORE)
        assertThat(store.get("acct-1")).isEqualTo(7_000L)
        assertThat(store.get("acct-2")).isEqualTo(3_000L)
        assertThat(store.get("acct-3")).isNull()
    }

    @Test
    fun `every change to the store is also written to its changelog topic`() {
        pay("acct-1" to 10_000, "acct-2" to 5_000, "acct-1" to -3_000)
        // <application.id>-<store name>-changelog: the compacted topic a restarted instance restores the table from
        assertThat(read("balance-app-balances-changelog")).containsExactly(
            KeyValue("acct-1", 10_000L), KeyValue("acct-2", 5_000L), KeyValue("acct-1", 7_000L),
        )
    }

    @Test
    fun `a balance below zero is also reported on the overdrafts topic`() {
        pay("acct-1" to 2_000, "acct-1" to -5_000, "acct-1" to 1_000, "acct-1" to 4_000)
        assertThat(read(BalanceTopology.OVERDRAFTS)).containsExactly(KeyValue("acct-1", -3_000L), KeyValue("acct-1", -2_000L))
        assertThat(read(BalanceTopology.BALANCES)).hasSize(4)
    }

    @Test
    fun `grouping by the existing key needs no repartition topic`() {
        val description = BalanceTopology.build().describe().toString()
        assertThat(description).contains("stores: [balances]")
        assertThat(description).doesNotContain("repartition")
    }
}
