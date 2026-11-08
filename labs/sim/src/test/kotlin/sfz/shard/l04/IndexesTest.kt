package sfz.shard.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import java.util.Random

class IndexesTest {
    /** Payment i is made with card i mod [cards]. */
    private fun payments(count: Int, cards: Int) =
        (0 until count).map { Payment("pay-$it", "M-%04d".format(it % 37), "card-${it % cards}", 1_000L + it) }

    @Test
    fun `a local index writes to one shard and reads from all of them`() {
        val table = LocalIndexTable(shards = 8)
        val writes = payments(1_000, cards = 100).map(table::insert)
        assertThat(writes).containsOnly(1)
        val found = table.findByCard("card-7")
        assertThat(found.ids).hasSize(10).allMatch { it.removePrefix("pay-").toInt() % 100 == 7 }
        assertThat(found.shardsContacted).isEqualTo(8)
    }

    @Test
    fun `a local index asks every shard even when nothing matches`() {
        val table = LocalIndexTable(shards = 8)
        payments(1_000, cards = 100).forEach(table::insert)
        assertThat(table.findByCard("card-never-used")).isEqualTo(QueryResult(emptySet(), 8))
    }

    @Test
    fun `a global index reads one index shard plus the shards that hold the rows`() {
        val clock = VirtualClock()
        val table = GlobalIndexTable(shards = 8, indexShards = 8, lagMillis = 0, clock = clock)
        val writes = payments(1_000, cards = 500).map(table::insert)
        assertThat(writes).containsOnly(2) // the row's shard and the card's index shard
        val found = table.findByCard("card-7") // pay-7 and pay-507
        assertThat(found.ids).containsExactlyInAnyOrder("pay-7", "pay-507")
        assertThat(found.shardsContacted).isEqualTo(1 + setOf(table.shardOf("pay-7"), table.shardOf("pay-507")).size)
        assertThat(table.findByCard("card-never-used")).isEqualTo(QueryResult(emptySet(), 1))
    }

    @Test
    fun `an asynchronous global index misses a write until its lag has passed`() {
        val clock = VirtualClock()
        val table = GlobalIndexTable(shards = 8, indexShards = 4, lagMillis = 200, clock = clock)
        table.insert(Payment("pay-1", "M-0042", "card-4242", 12_000))
        assertThat(table.findById("pay-1")).isNotNull() // the base table has it at once
        clock.advance(100)
        assertThat(table.findByCard("card-4242").ids).isEmpty() // the index doesn't yet
        assertThat(table.pendingUpdates).isEqualTo(1)
        clock.advance(100)
        assertThat(table.findByCard("card-4242").ids).containsExactly("pay-1")
        assertThat(table.pendingUpdates).isZero()
    }

    @Test
    fun `queued index entries land in the order their time comes`() {
        val clock = VirtualClock()
        val table = GlobalIndexTable(shards = 8, indexShards = 4, lagMillis = 200, clock = clock)
        table.insert(Payment("pay-1", "M-0042", "card-4242", 12_000))
        clock.advance(50)
        table.insert(Payment("pay-2", "M-0042", "card-4242", 8_000))
        clock.advance(170) // t = 220: pay-1's entry is due (200), pay-2's is not (250)
        assertThat(table.findByCard("card-4242").ids).containsExactly("pay-1")
        clock.advance(30)
        assertThat(table.findByCard("card-4242").ids).containsExactlyInAnyOrder("pay-1", "pay-2")
    }

    @Test
    fun `a fraud check 50 ms after each payment misses it when the index lags 200 ms`() {
        fun staleChecks(lag: Long): Int {
            val clock = VirtualClock()
            val table = GlobalIndexTable(shards = 8, indexShards = 4, lagMillis = lag, clock = clock)
            var stale = 0
            for (p in payments(1_000, cards = 100)) {
                table.insert(p)
                clock.advance(50) // the fraud check runs 50 ms after the payment
                if (p.id !in table.findByCard(p.card).ids) stale++
                clock.advance(950) // the next payment comes a second later
            }
            return stale
        }
        assertThat(staleChecks(lag = 200)).isEqualTo(1_000)
        assertThat(staleChecks(lag = 20)).isZero()
    }

    @Test
    fun `a scatter-gather is as slow as its slowest shard`() {
        val rnd = Random(42)
        fun latencies(shards: Int) = List(20_000) { FanOut.scatterMillis(shards, rnd) }
        val one = latencies(1)
        val ten = latencies(10)
        val fifty = latencies(50)
        // one shard: 1 reply in 100 is slow. Ten: 1 - 0.99^10, about 9.6%. Fifty: about 39.5%.
        assertThat(FanOut.slowerThan(one, 10.0)).isBetween(0.008, 0.012)
        assertThat(FanOut.slowerThan(ten, 10.0)).isBetween(0.088, 0.104)
        assertThat(FanOut.slowerThan(fifty, 10.0)).isBetween(0.38, 0.41)
        assertThat(FanOut.percentile(one, 99.0)).isLessThan(3.0)
        assertThat(FanOut.percentile(ten, 99.0)).isEqualTo(50.0)
        assertThat(FanOut.percentile(ten, 50.0)).isBetween(2.8, 3.0) // even the median waits for the slowest of ten
    }
}
