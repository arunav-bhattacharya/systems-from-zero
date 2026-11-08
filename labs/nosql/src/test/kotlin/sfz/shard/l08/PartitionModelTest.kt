package sfz.shard.l08

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class PartitionModelTest {
    private val gb = 1024L * 1024 * 1024

    /** [count] account keys that land in partition [p] of [partitions]. */
    private fun keysIn(p: Int, partitions: Int, count: Int): List<String> =
        generateSequence(0) { it + 1 }.map { "ACCT#A-%05d".format(it) }.filter { partitionOf(it, partitions) == p }.take(count).toList()

    /** [unitsPerPartition] write units for every partition of [partitions], over ten keys each. */
    private fun everywhere(partitions: Int, unitsPerPartition: Int): Map<String, Int> =
        (0 until partitions).flatMap { p -> keysIn(p, partitions, 10).map { it to unitsPerPartition / 10 } }.toMap()

    /** [units] write units a second on partition [p] of [partitions], over ten keys. */
    private fun on(p: Int, partitions: Int, units: Int): Map<String, Int> = keysIn(p, partitions, 10).associateWith { units / 10 }

    @Test
    fun `a new provisioned table gets enough partitions for its reads, writes and data`() {
        assertThat(Partitions.forNewTable(rcu = 0, wcu = 3_200)).isEqualTo(4)
        assertThat(Partitions.forNewTable(rcu = 12_000, wcu = 100)).isEqualTo(4)
        assertThat(Partitions.forNewTable(rcu = 1, wcu = 1, bytes = 25 * gb)).isEqualTo(3)
        assertThat(Partitions.forNewTable(rcu = 1, wcu = 1)).isEqualTo(1)
    }

    @Test
    fun `partitions split in two and never merge`() {
        assertThat(Partitions.afterSplits(current = 4, needed = 6)).isEqualTo(8)
        assertThat(Partitions.afterSplits(current = 4, needed = 4)).isEqualTo(4)
        assertThat(Partitions.afterSplits(current = 8, needed = 5)).isEqualTo(8)
        assertThat(Partitions.afterSplits(current = 3, needed = 13)).isEqualTo(24)
    }

    @Test
    fun `the paper's example - raising and lowering provisioned WCU`() {
        val t = ProvisionedTable(wcu = 3_200)
        assertThat(t.partitions to t.allocation()).isEqualTo(4 to 800)
        t.updateProvisioned(3_600)
        assertThat(t.partitions to t.allocation()).isEqualTo(4 to 900)
        t.updateProvisioned(6_000)
        assertThat(t.partitions to t.allocation()).isEqualTo(8 to 750)
        t.updateProvisioned(5_000) // fewer units, same partitions: each share shrinks
        assertThat(t.partitions to t.allocation()).isEqualTo(8 to 625)
    }

    @Test
    fun `without adaptive capacity a hot partition throttles while the table is mostly idle`() {
        // the AWS docs' example: 400 WCU over four partitions, 100 each; partition 3 gets 150
        val t = ProvisionedTable(wcu = 400, partitions = 4, adaptive = false)
        val traffic = on(0, 4, 50) + on(1, 4, 50) + on(2, 4, 50) + on(3, 4, 150)
        val r = t.serve(traffic)
        assertThat(r.admitted).isEqualTo(250) // of 400 provisioned
        assertThat(r.throttledByPartition).containsExactly(0, 0, 0, 50)
    }

    @Test
    fun `burst capacity spends five minutes of saved units, then throttles`() {
        val t = ProvisionedTable(wcu = 400, partitions = 4, adaptive = false)
        repeat(300) { t.serve(on(3, 4, 50)) } // a quiet five minutes: partition 3 saves 50 units a second
        assertThat(t.burst[3]).isEqualTo(15_000)

        val spike = on(3, 4, 150)
        val first300 = (1..300).sumOf { t.serve(spike).throttled }
        assertThat(first300).isZero()          // 300 seconds x 50 extra = the 15,000 saved units
        assertThat(t.serve(spike).throttled).isEqualTo(50)
    }

    @Test
    fun `adaptive capacity lends the table's unused units to the hot partition`() {
        val t = ProvisionedTable(wcu = 400, partitions = 4)
        val r = t.serve(on(0, 4, 50) + on(1, 4, 50) + on(2, 4, 50) + on(3, 4, 150))
        assertThat(r.throttled).isZero()
        assertThat(r.admittedByPartition).containsExactly(50, 50, 50, 150)
    }

    @Test
    fun `adaptive capacity stays inside the table's provisioned total`() {
        val t = ProvisionedTable(wcu = 400, partitions = 4)
        val r = t.serve(on(0, 4, 50) + on(1, 4, 50) + on(2, 4, 50) + on(3, 4, 300))
        assertThat(r.admitted).isEqualTo(400)
        assertThat(r.throttledByPartition).containsExactly(0, 0, 0, 50)
    }

    @Test
    fun `a split for size divides the share, and adaptive capacity hides the dilution`() {
        val keys = on(0, 2, 800) // 800 WCU on what will be the lower half of the key space
        val strict = ProvisionedTable(wcu = 1_000, adaptive = false)
        assertThat(strict.partitions to strict.allocation()).isEqualTo(1 to 1_000)
        strict.grow(15 * gb) // more than one partition holds: it splits, and so does its share
        assertThat(strict.partitions to strict.allocation()).isEqualTo(2 to 500)
        assertThat(strict.serve(keys).throttled).isEqualTo(300)

        val modern = ProvisionedTable(wcu = 1_000)
        modern.grow(15 * gb)
        assertThat(modern.serve(keys).throttled).isZero()
    }

    @Test
    fun `one hot key throttles above 1,000 WCU whatever the table has`() {
        val provisioned = ProvisionedTable(wcu = 40_000) // 40 partitions, 1,000 each
        assertThat(provisioned.partitions).isEqualTo(40)
        val hot = mapOf("MERCH#M-0042#TOTAL" to 1_500)
        assertThat((1..10).sumOf { provisioned.serve(hot).throttled }).isEqualTo(5_000)

        val onDemand = OnDemandTable()
        assertThat((1..10).sumOf { onDemand.serve(hot).throttled }).isEqualTo(5_000)
    }

    @Test
    fun `on-demand takes 4,000 writes a second at first, then up to double its previous peak`() {
        val t = OnDemandTable()
        assertThat(t.serve(everywhere(4, 1_500)).throttled).isEqualTo(2_000) // 6,000 asked, 4,000 admitted
        assertThat(t.previousPeak to t.partitions).isEqualTo(4_000 to 8)
        assertThat(t.serve(everywhere(8, 1_000)).throttled).isZero()       // 8,000 = double 4,000
        assertThat(t.ceiling() to t.partitions).isEqualTo(16_000 to 16)
    }

    @Test
    fun `on-demand throttles at double the previous peak even with partitions to spare`() {
        val t = OnDemandTable()
        t.serve(everywhere(4, 750))                                          // a peak of 3,000
        assertThat(t.ceiling() to t.partitions).isEqualTo(6_000 to 8)
        val r = t.serve(everywhere(8, 1_000))                               // 8,000 asked
        assertThat(r.admitted).isEqualTo(6_000)
        assertThat(r.throttledByPartition).containsExactly(0, 0, 0, 0, 0, 0, 1_000, 1_000)
    }
}
