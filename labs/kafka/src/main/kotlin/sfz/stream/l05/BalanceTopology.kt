package sfz.stream.l05

import org.apache.kafka.streams.Topology

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

    /**
     * Build it with a `StreamsBuilder`:
     *
     * 1. `stream(PAYMENTS, Consumed.with(Serdes.String(), Serdes.Long()))`
     * 2. group by the key the records already have (no repartition topic: the tests check the topology),
     * 3. `aggregate` from 0 by adding each amount, materialized as [STORE] with String and Long serdes,
     * 4. `toStream()` the table and write every update to [BALANCES], and the negative ones to [OVERDRAFTS].
     */
    @JvmStatic
    fun build(): Topology {
        TODO("payments -> groupByKey -> aggregate into STORE -> toStream -> BALANCES; negative balances also to OVERDRAFTS")
    }
}
