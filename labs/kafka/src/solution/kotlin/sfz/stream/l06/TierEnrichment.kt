package sfz.stream.l06

import org.apache.kafka.common.serialization.Serdes
import org.apache.kafka.common.utils.Bytes
import org.apache.kafka.streams.StreamsBuilder
import org.apache.kafka.streams.Topology
import org.apache.kafka.streams.kstream.Consumed
import org.apache.kafka.streams.kstream.Joined
import org.apache.kafka.streams.kstream.KeyValueMapper
import org.apache.kafka.streams.kstream.Materialized
import org.apache.kafka.streams.kstream.Produced
import org.apache.kafka.streams.kstream.ValueJoiner
import org.apache.kafka.streams.state.KeyValueStore
import org.apache.kafka.streams.state.Stores
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

    @JvmStatic
    fun build(): Topology {
        val builder = StreamsBuilder()
        val tiers = builder.table(
            TIERS, Consumed.with(Serdes.String(), Serdes.String()),
            // the fix: a versioned store keeps every tier with the time it took effect, for HISTORY, so the join
            // can ask "which tier was in force at the order's timestamp?" instead of "which tier arrived last?"
            Materialized.`as`<String, String>(Stores.persistentVersionedKeyValueStore(STORE, HISTORY))
                .withKeySerde(Serdes.String()).withValueSerde(Serdes.String()),
        )
        builder.stream(ORDERS, Consumed.with(Serdes.String(), Serdes.String()))
            .leftJoin(tiers, joiner, Joined.with(Serdes.String(), Serdes.String(), Serdes.String()))
            .to(ENRICHED, Produced.with(Serdes.String(), Serdes.String()))
        return builder.build()
    }

    /**
     * The same enrichment against a GlobalKTable: every instance keeps a full copy of [TIERS], so an order finds its
     * customer's tier whatever partition either record is in. No co-partitioning needed.
     */
    @JvmStatic
    fun buildGlobal(): Topology {
        val builder = StreamsBuilder()
        val tiers = builder.globalTable(
            TIERS, Consumed.with(Serdes.String(), Serdes.String()),
            Materialized.`as`<String, String, KeyValueStore<Bytes, ByteArray>>(STORE),
        )
        builder.stream(ORDERS, Consumed.with(Serdes.String(), Serdes.String()))
            // which row of the global table to look up: here the record key, the customer id
            .leftJoin(tiers, KeyValueMapper<String, String, String> { customer, _ -> customer }, joiner)
            .to(ENRICHED, Produced.with(Serdes.String(), Serdes.String()))
        return builder.build()
    }
}
