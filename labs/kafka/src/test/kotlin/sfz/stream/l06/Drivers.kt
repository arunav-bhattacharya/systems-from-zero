package sfz.stream.l06

import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import org.apache.kafka.streams.StreamsConfig
import org.apache.kafka.streams.Topology
import org.apache.kafka.streams.TopologyTestDriver
import java.nio.file.Files
import java.time.Instant
import java.util.Properties

/** One record to pipe into the topology: which topic, key, value and event time. */
data class In(val topic: String, val key: String, val value: String, val at: Instant)

fun tier(customer: String, tier: String, at: String) = In(TierEnrichment.TIERS, customer, tier, time(at))
fun order(customer: String, order: String, at: String) = In(TierEnrichment.ORDERS, customer, order, time(at))

/** "09:30" on 2026-11-07, or "d3 09:30" for three days later. UTC. */
fun time(at: String): Instant {
    val (day, hm) = if (at.startsWith("d")) at.substringBefore(' ').drop(1).toLong() to at.substringAfter(' ') else 0L to at
    return Instant.parse("2026-11-07T$hm:00Z").plusSeconds(day * 86_400)
}

/**
 * Runs [topology] in a fresh TopologyTestDriver (no broker), pipes [records] in the given arrival order and returns
 * the enriched output as "<order> tier=<tier>" strings, keyed by customer, in output order.
 */
fun runTopology(topology: Topology, records: List<In>): List<Pair<String, String>> {
    val stateDir = Files.createTempDirectory("sfz-stream06-")
    val props = Properties().apply {
        put(StreamsConfig.APPLICATION_ID_CONFIG, "tier-enrichment")
        put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "unused:9092")
        put(StreamsConfig.STATE_DIR_CONFIG, stateDir.toString())   // RocksDB locks its directory: one per driver
        put(StreamsConfig.STATESTORE_CACHE_MAX_BYTES_CONFIG, 0)
    }
    try {
        TopologyTestDriver(topology, props).use { driver ->
            val inputs = listOf(TierEnrichment.ORDERS, TierEnrichment.TIERS)
                .associateWith { driver.createInputTopic(it, StringSerializer(), StringSerializer()) }
            for (r in records) inputs.getValue(r.topic).pipeInput(r.key, r.value, r.at)
            return driver.createOutputTopic(TierEnrichment.ENRICHED, StringDeserializer(), StringDeserializer())
                .readKeyValuesToList().map { it.key to it.value }
        }
    } finally {
        stateDir.toFile().deleteRecursively()
    }
}
