package sfz.kafka.l10.demo

import org.apache.kafka.clients.admin.Admin
import org.apache.kafka.clients.admin.NewTopic
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.config.ConfigResource
import org.apache.kafka.common.serialization.LongSerializer
import org.apache.kafka.common.serialization.Serdes
import org.apache.kafka.common.serialization.StringSerializer
import org.apache.kafka.common.utils.Bytes
import org.apache.kafka.streams.CloseOptions
import org.apache.kafka.streams.KafkaStreams
import org.apache.kafka.streams.StoreQueryParameters
import org.apache.kafka.streams.StreamsBuilder
import org.apache.kafka.streams.StreamsConfig
import org.apache.kafka.streams.Topology
import org.apache.kafka.streams.kstream.Consumed
import org.apache.kafka.streams.kstream.Materialized
import org.apache.kafka.streams.kstream.Produced
import org.apache.kafka.streams.processor.StateRestoreListener
import org.apache.kafka.streams.state.KeyValueStore
import org.apache.kafka.streams.state.QueryableStoreTypes
import java.io.File

private const val BOOTSTRAP = "localhost:9092"

/**
 * The balance app on a real broker. Run 1 folds 1,000 payments for 10 accounts into the store "balances" and
 * stops. Then the demo deletes the app's local state directory, as if the instance moved to a machine with an
 * empty disk, and run 2 starts: Kafka Streams rebuilds the store from the changelog topic before it processes
 * anything. Argument "eos" runs both with processing.guarantee=exactly_once_v2.
 */
fun main(args: Array<String>) {
    val eos = args.firstOrNull() == "eos"
    val run = System.currentTimeMillis() % 100_000
    val payments = "payments-$run"
    val appId = "balance-$run"
    Admin.create(mapOf<String, Any>("bootstrap.servers" to BOOTSTRAP)).use { admin ->
        admin.createTopics(listOf(NewTopic(payments, 1, 1.toShort()), NewTopic("balances-$run", 1, 1.toShort()))).all().get()
        KafkaProducer(mapOf<String, Any>("bootstrap.servers" to BOOTSTRAP), StringSerializer(), LongSerializer()).use { p ->
            for (i in 0 until 1000) p.send(ProducerRecord(payments, 0, "acct-${i % 10}", (i % 7 - 3) * 1_000L))
        }
        val stateDir = File("build/streams-state")
        val config = StreamsConfig(mapOf<String, Any>(
            StreamsConfig.APPLICATION_ID_CONFIG to appId,           // also the group id and the prefix of internal topics
            StreamsConfig.BOOTSTRAP_SERVERS_CONFIG to BOOTSTRAP,
            StreamsConfig.STATE_DIR_CONFIG to stateDir.path,        // where RocksDB keeps the store on local disk
            StreamsConfig.PROCESSING_GUARANTEE_CONFIG to if (eos) StreamsConfig.EXACTLY_ONCE_V2 else StreamsConfig.AT_LEAST_ONCE,
            StreamsConfig.STATESTORE_CACHE_MAX_BYTES_CONFIG to 0,   // no record cache: every update reaches the changelog
            "auto.offset.reset" to "earliest",
        ))

        runApp("run 1", topology(payments, "balances-$run"), config)
        val changelog = "$appId-balances-changelog"
        val policy = admin.describeConfigs(listOf(ConfigResource(ConfigResource.Type.TOPIC, changelog))).all().get()
            .values.first().get("cleanup.policy").value()
        println("changelog topic $changelog has cleanup.policy=$policy")
        val local = File(stateDir, "$appId/0_0/rocksdb/balances")
        println("local store: ${local.path}, ${local.listFiles()!!.size} files")
        File(stateDir, appId).deleteRecursively()
        println("deleted ${File(stateDir, appId).path}: the local copy is gone")
        runApp("run 2", topology(payments, "balances-$run"), config)
    }
}

private fun topology(payments: String, balances: String): Topology = StreamsBuilder().apply {
    stream(payments, Consumed.with(Serdes.String(), Serdes.Long()))
        .groupByKey()
        .aggregate({ 0L }, { _, amount, balance -> balance + amount },
            Materialized.`as`<String, Long, KeyValueStore<Bytes, ByteArray>>("balances")
                .withKeySerde(Serdes.String()).withValueSerde(Serdes.Long()))
        .toStream()
        .to(balances, Produced.with(Serdes.String(), Serdes.Long()))
}.build()

/** What the store must hold once all 1,000 payments are in: the sum of each account's payments, in cents. */
private val expected: Map<String, Long> = (0 until 1000).groupBy { "acct-${it % 10}" }.mapValues { (_, i) -> i.sumOf { (it % 7 - 3) * 1_000L } }

/** Starts the app, waits until all 1,000 payments are in the store, prints two balances and stops. */
private fun runApp(label: String, topology: Topology, config: StreamsConfig) {
    val streams = KafkaStreams(topology, config)
    streams.setGlobalStateRestoreListener(object : StateRestoreListener {
        override fun onRestoreStart(tp: TopicPartition, store: String, start: Long, end: Long) =
            println("$label: restoring store '$store' from $tp, offsets $start to $end")
        override fun onBatchRestored(tp: TopicPartition, store: String, batchEnd: Long, restored: Long) {}
        override fun onRestoreEnd(tp: TopicPartition, store: String, total: Long) =
            println("$label: restored $total records")
    })
    streams.start()
    val deadline = System.nanoTime() + 120_000_000_000L
    var balances = emptyMap<String, Long>()
    while (balances != expected && System.nanoTime() < deadline) {
        Thread.sleep(200)
        balances = try {
            val store = streams.store(StoreQueryParameters.fromNameAndType("balances", QueryableStoreTypes.keyValueStore<String, Long>()))
            store.all().use { it.asSequence().associate { kv -> kv.key to kv.value } }
        } catch (e: Exception) {
            emptyMap() // not running yet, or still restoring
        }
    }
    println("$label: ${balances.size} accounts in the store, acct-0 = ${balances["acct-0"]} cents, acct-1 = ${balances["acct-1"]} cents")
    // a clean shutdown that leaves the group at once, so run 2 doesn't wait for run 1's session to time out
    streams.close(CloseOptions.groupMembershipOperation(CloseOptions.GroupMembershipOperation.LEAVE_GROUP))
}
