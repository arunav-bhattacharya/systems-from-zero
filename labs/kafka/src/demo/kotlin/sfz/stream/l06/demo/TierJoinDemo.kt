package sfz.stream.l06.demo

import org.apache.kafka.common.serialization.Serdes
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import org.apache.kafka.streams.StreamsBuilder
import org.apache.kafka.streams.Topology
import org.apache.kafka.streams.kstream.Consumed
import org.apache.kafka.streams.kstream.Joined
import org.apache.kafka.streams.kstream.Materialized
import org.apache.kafka.streams.kstream.Produced
import org.apache.kafka.streams.kstream.ValueJoiner
import org.apache.kafka.streams.state.Stores
import java.time.Duration

/**
 * Orders joined with the customer's tier, three ways: an ordinary (unversioned) table, a versioned table, and a
 * versioned table with a 5-minute grace period on the order side. Customer c-1 is silver from 09:00 and gold from
 * 10:00. Each scenario pipes the same records in a different arrival order, and ends with order o-9 at 10:30.
 */
fun main() {
    val variants = listOf("unversioned" to topology(versioned = false, grace = null),
        "versioned" to topology(versioned = true, grace = null),
        "versioned+grace" to topology(versioned = true, grace = Duration.ofMinutes(5)))
    val scenarios = listOf(
        "A1 o-1 (09:30) arrives before the upgrade" to listOf("tier silver 09:00", "order o-1 09:30", "tier gold 10:00", "order o-9 10:30"),
        "A2 o-1 (09:30) arrives after the upgrade" to listOf("tier silver 09:00", "tier gold 10:00", "order o-1 09:30", "order o-9 10:30"),
        "B  upgrade (10:00) arrives after o-2 (10:02)" to listOf("tier silver 09:00", "order o-2 10:02", "tier gold 10:00", "order o-9 10:30"),
    )
    println("%-45s %-21s %-21s %s".format("scenario", "unversioned", "versioned", "versioned+grace"))
    for ((name, records) in scenarios) {
        val results = variants.map { (label, t) -> run(t, label, records) }
        println("%-45s %-21s %-21s %s".format(name, *results.toTypedArray()))
    }
}

private fun topology(versioned: Boolean, grace: Duration?): Topology {
    val builder = StreamsBuilder()
    val consumed = Consumed.with(Serdes.String(), Serdes.String())
    val tiers = if (versioned) {
        // every version of each customer's tier, with the time it took effect, kept for 7 days
        builder.table("customer-tiers", consumed, Materialized.`as`<String, String>(
            Stores.persistentVersionedKeyValueStore("tiers", Duration.ofDays(7))))
    } else {
        builder.table("customer-tiers", consumed)          // the latest tier per customer, nothing else
    }
    var joined = Joined.with(Serdes.String(), Serdes.String(), Serdes.String())
    if (grace != null) joined = joined.withGracePeriod(grace)   // hold each order this long (stream time) before joining
    builder.stream("orders", consumed)
        .leftJoin(tiers, ValueJoiner<String, String?, String> { order, tier -> "$order=${tier ?: "none"}" }, joined)
        .to("orders-enriched", Produced.with(Serdes.String(), Serdes.String()))
    return builder.build()
}

/** Pipes "tier <tier> <time>" and "order <id> <time>" records for customer c-1; returns the orders' tiers. */
private fun run(topology: Topology, label: String, records: List<String>): String = drive(topology, "tier-join-$label") { driver ->
    val orders = driver.createInputTopic("orders", StringSerializer(), StringSerializer())
    val tiers = driver.createInputTopic("customer-tiers", StringSerializer(), StringSerializer())
    for (r in records) {
        val (kind, value, time) = r.split(" ")
        if (kind == "tier") tiers.pipeInput("c-1", value, at(time)) else orders.pipeInput("c-1", value, at(time))
    }
    driver.createOutputTopic("orders-enriched", StringDeserializer(), StringDeserializer())
        .readValuesToList().joinToString(" ")
}
