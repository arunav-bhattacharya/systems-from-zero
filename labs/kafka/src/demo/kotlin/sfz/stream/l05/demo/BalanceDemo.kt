package sfz.stream.l05.demo

import org.apache.kafka.common.serialization.LongDeserializer
import org.apache.kafka.common.serialization.LongSerializer
import org.apache.kafka.common.serialization.Serdes
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import org.apache.kafka.common.utils.Bytes
import org.apache.kafka.streams.StreamsBuilder
import org.apache.kafka.streams.StreamsConfig
import org.apache.kafka.streams.TopologyTestDriver
import org.apache.kafka.streams.kstream.Consumed
import org.apache.kafka.streams.kstream.Materialized
import org.apache.kafka.streams.kstream.Produced
import org.apache.kafka.streams.state.KeyValueStore
import java.util.Properties

/**
 * A running balance per account: the payments stream folded into a table. Runs in TopologyTestDriver, so it needs
 * no broker: the driver pushes each record through the topology and keeps what it writes.
 */
fun main() {
    val builder = StreamsBuilder()
    builder.stream("payments", Consumed.with(Serdes.String(), Serdes.Long()))      // KStream: one record per payment
        .groupByKey()
        .aggregate({ 0L }, { _, amount, balance -> balance + amount },             // KTable: one row per account
            Materialized.`as`<String, Long, KeyValueStore<Bytes, ByteArray>>("balances")
                .withKeySerde(Serdes.String()).withValueSerde(Serdes.Long()))
        .toStream()                                                                // the table's changes, as a stream
        .to("balances", Produced.with(Serdes.String(), Serdes.Long()))
    val topology = builder.build()
    println(topology.describe())

    val props = Properties().apply {
        put(StreamsConfig.APPLICATION_ID_CONFIG, "balance-demo")
        put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "unused:9092")    // the driver never connects
        put(StreamsConfig.STATE_DIR_CONFIG, "build/streams-state")
        put(StreamsConfig.STATESTORE_CACHE_MAX_BYTES_CONFIG, 0)       // show every update (section 2 explains)
    }
    TopologyTestDriver(topology, props).use { driver ->
        val payments = driver.createInputTopic("payments", StringSerializer(), LongSerializer())
        val balances = driver.createOutputTopic("balances", StringDeserializer(), LongDeserializer())
        for ((account, cents) in listOf("acct-1" to 10_000L, "acct-2" to 5_000L, "acct-1" to -3_000L, "acct-1" to 500L)) {
            payments.pipeInput(account, cents)
            val out = balances.readKeyValue()
            println("payment %s %8s  ->  balances: %s = %s".format(account, money(cents, signed = true), out.key, money(out.value)))
        }
        val changelog = driver.createOutputTopic("balance-demo-balances-changelog", StringDeserializer(), LongDeserializer())
        println("changelog topic balance-demo-balances-changelog: " +
            changelog.readKeyValuesToList().joinToString { "${it.key}=${money(it.value)}" })
        val store = driver.getKeyValueStore<String, Long>("balances")
        println("store 'balances': " + store.all().use { it.asSequence().joinToString { kv -> "${kv.key}=${money(kv.value)}" } })
    }
}

private fun money(cents: Long, signed: Boolean = false) = (if (signed) "%+.2f" else "%.2f").format(cents / 100.0)
