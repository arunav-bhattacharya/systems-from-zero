package sfz.shard.l01

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.AlphaChars
import net.jqwik.api.constraints.StringLength
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.shard.l01.Workload.at

class ShardingTest {
    private val abc = RangeSharding(listOf("g", "p"))

    // eight shards cut from the morning's keys; the afternoon's payments then arrive on top
    private val morning = Workload.payments(20_000, startMillis = at(8), everyMillis = 1_000)
    private val afternoon = Workload.payments(10_000, startMillis = at(14), firstId = 20_000, seed = 8)

    @Test
    fun `a key equal to a boundary belongs to the shard on its right`() {
        assertThat(abc.shardCount).isEqualTo(3)
        assertThat(listOf("a", "f", "g", "o", "p", "z").map(abc::shardOf)).containsExactly(0, 0, 1, 1, 2, 2)
    }

    @Property(tries = 300)
    fun `the binary search agrees with counting boundaries`(@ForAll @AlphaChars @StringLength(min = 0, max = 4) key: String) {
        val bounds = RangeSharding(listOf("Cat", "Dog", "dog", "m", "mm", "x"))
        assertThat(bounds.shardOf(key)).isEqualTo(bounds.boundaries.count { it <= key })
    }

    @Test
    fun `a range scan asks only the shards whose ranges overlap it`() {
        assertThat(abc.shardsForRange("h", "k")).containsExactly(1)
        assertThat(abc.shardsForRange("c", "g")).containsExactly(0) // "g" itself is excluded
        assertThat(abc.shardsForRange("g", "p")).containsExactly(1)
        assertThat(abc.shardsForRange("a", "q")).containsExactly(0, 1, 2)
        assertThat(abc.shardsForRange("k", "k")).isEmpty()
    }

    @Test
    fun `split points from a sample give shards of equal size`() {
        val sample = (0 until 1_000).map { "acct-%04d".format(it) }.shuffled(java.util.Random(1))
        val shards = RangeSharding.fromSample(sample, 4)
        assertThat(shards.boundaries).containsExactly("acct-0250", "acct-0500", "acct-0750")
        assertThat(load(shards, sample)).containsExactly(250, 250, 250, 250)
    }

    @Test
    fun `time-ordered keys send every new payment to the last range`() {
        val shards = RangeSharding.fromSample(morning.map(Keys::byTime), 8)
        val inserts = load(shards, afternoon.map(Keys::byTime))
        assertThat(inserts).containsExactly(0, 0, 0, 0, 0, 0, 0, 10_000)
        assertThat(skew(inserts)).isEqualTo(8.0)
    }

    @Test
    fun `hashing the same keys spreads the inserts evenly`() {
        val inserts = load(HashSharding(8), afternoon.map(Keys::byTime))
        assertThat(inserts.sum()).isEqualTo(10_000)
        assertThat(skew(inserts)).isLessThan(1.05)
    }

    @Test
    fun `hashing gives up range scans`() {
        // "every payment between 14:00 and 14:05"
        val from = "%013d".format(at(14))
        val to = "%013d".format(at(14, 5))
        assertThat(RangeSharding.fromSample(morning.map(Keys::byTime), 8).shardsForRange(from, to)).hasSize(1)
        assertThat(HashSharding(8).shardsForRange(from, to)).hasSize(8)
    }

    @Test
    fun `merchant first spreads the inserts and keeps one merchant's day together`() {
        val shards = RangeSharding.fromSample(morning.map(Keys::byMerchant), 8)
        assertThat(skew(load(shards, afternoon.map(Keys::byMerchant)))).isLessThan(1.15)
        // all of M-0042's payments sort between "M-0042#" and "M-0042$" ('$' comes right after '#')
        assertThat(shards.shardsForRange("M-0042#", "M-0042$")).hasSize(1)
    }

    @Test
    fun `a hot merchant stays hot whatever the hash`() {
        val blackFriday = Workload.payments(10_000, startMillis = at(12), hotShare = 0.2)
        val byMerchant = load(HashSharding(8), blackFriday.map { it.merchant })
        // one partition key can't be split by hashing: its shard takes at least its 20%
        assertThat(byMerchant.max()).isGreaterThanOrEqualTo(2_000)
        assertThat(skew(byMerchant)).isGreaterThan(1.6)
    }

    @Test
    fun `every process computes the same shard for a key`() {
        // MD5 is the same on every machine, so these numbers are too (Python's hashlib agrees)
        assertThat(stableHash("pay-1")).isEqualTo(-8832585514199362806L)
        assertThat(HashSharding(8).shardOf("pay-1")).isEqualTo(2) // floorMod: never negative
        assertThat(HashSharding(8).shardOf("M-0042")).isEqualTo(7)
    }
}
