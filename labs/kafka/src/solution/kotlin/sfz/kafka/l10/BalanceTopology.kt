package sfz.kafka.l10

import org.apache.kafka.common.serialization.Serdes
import org.apache.kafka.common.utils.Bytes
import org.apache.kafka.streams.StreamsBuilder
import org.apache.kafka.streams.Topology
import org.apache.kafka.streams.kstream.Consumed
import org.apache.kafka.streams.kstream.Grouped
import org.apache.kafka.streams.kstream.Materialized
import org.apache.kafka.streams.kstream.Produced
import org.apache.kafka.streams.state.KeyValueStore

/**
 * A running balance per account, kept by Kafka Streams.
 *
 * Input: [PAYMENTS], key = account id, value = amount in cents (a debit is negative).
 * Output: the table of balances, materialized in the state store [STORE]; every change to it written to
 * [BALANCES] (key = account id, value = the new balance in cents); and the changes that leave a balance below
 * zero written to [OVERDRAFTS] as well.
 */
object BalanceTopology {
    const val PAYMENTS = "payments"
    const val BALANCES = "balances"
    const val OVERDRAFTS = "overdrafts"
    const val STORE = "balances"

    @JvmStatic
    fun build(): Topology {
        val builder = StreamsBuilder()
        val balances = builder.stream(PAYMENTS, Consumed.with(Serdes.String(), Serdes.Long()))
            // the records are already keyed by account, so grouping needs no repartition topic
            .groupByKey(Grouped.with(Serdes.String(), Serdes.Long()))
            // the fold: start at 0, add each payment; the table lives in the store, backed by a changelog topic
            .aggregate(
                { 0L },
                { _, amount, balance -> balance + amount },
                Materialized.`as`<String, Long, KeyValueStore<Bytes, ByteArray>>(STORE)
                    .withKeySerde(Serdes.String())
                    .withValueSerde(Serdes.Long()),
            )
        // a table's changes are a stream again: one record per update
        val updates = balances.toStream()
        updates.to(BALANCES, Produced.with(Serdes.String(), Serdes.Long()))
        updates.filter { _, balance -> balance < 0 }.to(OVERDRAFTS, Produced.with(Serdes.String(), Serdes.Long()))
        return builder.build()
    }
}
