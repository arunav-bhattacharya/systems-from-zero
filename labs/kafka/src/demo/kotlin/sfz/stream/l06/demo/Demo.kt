package sfz.stream.l06.demo

import org.apache.kafka.streams.StreamsConfig
import org.apache.kafka.streams.Topology
import org.apache.kafka.streams.TopologyTestDriver
import java.io.File
import java.time.Instant
import java.util.Properties

/** "10:04" on 2026-11-07, UTC. */
fun at(hm: String): Instant = Instant.parse("2026-11-07T$hm:00Z")

/** "10:04:30" from an Instant. */
fun hms(t: Instant): String = t.toString().substring(11, 19)

/** Runs [body] with [topology] in a TopologyTestDriver: no broker, each record goes through the topology at once. */
fun <T> drive(topology: Topology, name: String, body: (TopologyTestDriver) -> T): T {
    val dir = File("build/streams-state/$name").apply { deleteRecursively() }
    val props = Properties().apply {
        put(StreamsConfig.APPLICATION_ID_CONFIG, name)
        put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "unused:9092")   // the driver never connects
        put(StreamsConfig.STATE_DIR_CONFIG, dir.path)
        put(StreamsConfig.STATESTORE_CACHE_MAX_BYTES_CONFIG, 0)      // every update goes downstream at once
    }
    return TopologyTestDriver(topology, props).use(body)
}
