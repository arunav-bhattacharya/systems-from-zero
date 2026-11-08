package sfz.stream.l06

import org.apache.kafka.common.serialization.Serdes
import org.apache.kafka.streams.StreamsBuilder
import org.apache.kafka.streams.Topology
import org.apache.kafka.streams.kstream.Consumed
import org.apache.kafka.streams.kstream.Joined
import org.apache.kafka.streams.kstream.Produced
import org.apache.kafka.streams.kstream.ValueJoiner
import java.time.Duration

/**
 * Enrich each order with the customer's loyalty tier, the tier that was in force when the order was placed.
 *
 * Input [ORDERS]: key = customer id, value = order id and amount (`"o-17 120.00"`), record timestamp = when the
 * customer placed the order (event time).
 * Input [TIERS]: key = customer id, value = tier (`"silver"`, `"gold"`), record timestamp = when the tier took effect.
 * Output [ENRICHED]: key = customer id, value = `"<order> tier=<tier>"`, or `"<order> tier=none"` when no tier is
 * known for that time.
 */
object TierEnrichment {
    const val ORDERS = "orders"
    const val TIERS = "customer-tiers"
    const val ENRICHED = "orders-enriched"
    const val STORE = "tiers"

    /** How far back the versioned store keeps old tiers. Orders older than this (in stream time) get no tier. */
    val HISTORY: Duration = Duration.ofDays(7)

    private val joiner = ValueJoiner<String, String?, String> { order, tier -> "$order tier=${tier ?: "none"}" }

    /**
     * THE BUG: this table keeps only the latest tier per customer, whatever its timestamp. An order that arrives
     * late, after the customer's upgrade, is joined with the new tier although it was placed before the upgrade,
     * and the answer depends on which record happened to arrive first.
     *
     * Fix it: materialize the table in a versioned store named [STORE] that keeps [HISTORY] of old tiers, with
     * `Materialized.as(Stores.persistentVersionedKeyValueStore(STORE, HISTORY))` and String serdes. The join then
     * uses the tier whose timestamp is the latest one at or before the order's timestamp.
     */
    @JvmStatic
    fun build(): Topology {
        val builder = StreamsBuilder()
        val tiers = builder.table(TIERS, Consumed.with(Serdes.String(), Serdes.String()))
        builder.stream(ORDERS, Consumed.with(Serdes.String(), Serdes.String()))
            .leftJoin(tiers, joiner, Joined.with(Serdes.String(), Serdes.String(), Serdes.String()))
            .to(ENRICHED, Produced.with(Serdes.String(), Serdes.String()))
        return builder.build()
    }

    /**
     * The same enrichment against a GlobalKTable: `builder.globalTable(TIERS, Consumed..., Materialized.as(STORE))`,
     * then `leftJoin(globalTable, KeyValueMapper { customer, _ -> customer }, joiner)` and write to [ENRICHED].
     * Every instance keeps a full copy of [TIERS], so no co-partitioning is needed.
     */
    @JvmStatic
    fun buildGlobal(): Topology {
        TODO("globalTable(TIERS) materialized as STORE; orders leftJoin it on the record key; write to ENRICHED")
    }
}
