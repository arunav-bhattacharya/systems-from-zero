package sfz.shard.l03

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.IntRange
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class RebalanceTest {
    private val ten = (1..10).map { "node-%02d".format(it) }
    private val keys = (0 until 100_000).map { "pay-$it" }

    @Test
    fun `mod N moves about ten of every eleven keys when an eleventh node joins`() {
        val modN = ModN(ten)
        val moved = movedKeys(keys, modN) { modN.addNode("node-11") }
        assertThat(moved).isBetween(90_000, 92_000) // a key stays only if h mod 10 == h mod 11: 1 in 11
    }

    @Test
    fun `fixed partitions move whole partitions to the new node, about an eleventh of the keys`() {
        val fixed = FixedPartitions(1_000, ten)
        lateinit var partitions: List<Int>
        val moved = movedKeys(keys, fixed) { partitions = fixed.addNode("node-11") }
        assertThat(partitions).hasSize(90) // 1,000 / 11, rounded down
        assertThat(fixed.partitionsOf("node-11")).containsExactlyInAnyOrderElementsOf(partitions)
        // every key that moved belongs to one of the moved partitions, and every one of those keys moved
        assertThat(moved).isEqualTo(keys.count { fixed.partitionOf(it) in partitions })
        assertThat(moved).isBetween(8_500, 9_500)
    }

    @Test
    fun `the busiest node gives first, its highest partition first`() {
        // 12 partitions round robin: A holds 0, 3, 6, 9; B holds 1, 4, 7, 10; C holds 2, 5, 8, 11
        val fixed = FixedPartitions(12, listOf("A", "B", "C"))
        assertThat(fixed.addNode("D")).containsExactly(9, 10, 11)
        assertThat(listOf("A", "B", "C", "D").map { fixed.partitionsOf(it).size }).containsExactly(3, 3, 3, 3)
        // two more nodes: 12 / 6 = 2 each
        assertThat(fixed.addNode("E")).containsExactly(6, 7)
        assertThat(fixed.addNode("F")).containsExactly(8, 11)
        assertThat(listOf("A", "B", "C", "D", "E", "F").map { fixed.partitionsOf(it).size }).containsOnly(2)
    }

    @Test
    fun `a node beyond the partition count gets nothing to do`() {
        val fixed = FixedPartitions(4, listOf("A", "B", "C", "D"))
        assertThat(fixed.addNode("E")).isEmpty()
        assertThat(fixed.partitionsOf("E")).isEmpty()
    }

    @Property(tries = 200)
    fun `after a join every node holds the fair share, rounded down or up`(
        @ForAll @IntRange(min = 1, max = 30) nodes: Int,
        @ForAll @IntRange(min = 1, max = 2_000) partitions: Int,
    ) {
        val fixed = FixedPartitions(partitions, (1..nodes).map { "n$it" })
        val moved = fixed.addNode("new")
        val fair = partitions / (nodes + 1)
        assertThat(moved).hasSize(fair)
        assertThat(fixed.nodes.map { fixed.partitionsOf(it).size }).allMatch { it == fair || it == fair + 1 }
    }

    @Test
    fun `a range splits at its median when it passes maxKeys`() {
        val store = DynamicRanges(maxKeys = 4, firstNode = "A")
        listOf("d", "a", "e", "b").forEach(store::insert)
        assertThat(store.ranges).hasSize(1)
        store.insert("c") // five keys: split at the one at index 2, "c"
        assertThat(store.ranges.map { it.start }).containsExactly("", "c")
        assertThat(store.ranges.map { it.keys.toList() }).containsExactly(listOf("a", "b"), listOf("c", "d", "e"))
        assertThat(store.ranges.map { it.node }).containsOnly("A") // a split moves nothing between nodes
        assertThat(store.ownerOf("bb")).isEqualTo("A")
        assertThat(store.rangeOf("bb").start).isEqualTo("")
        assertThat(store.rangeOf("c").start).isEqualTo("c")
    }

    @Test
    fun `the number of ranges follows the amount of data`() {
        val store = DynamicRanges(maxKeys = 1_000, firstNode = "A")
        keys.take(10_000).forEach(store::insert)
        assertThat(store.ranges.sumOf { it.keys.size }).isEqualTo(10_000)
        assertThat(store.ranges).allMatch { it.keys.size in 500..1_000 }
        assertThat(store.ranges.size).isBetween(10, 20)
        // every key sits in the range rangeOf names, and the ranges are in key order
        assertThat(store.ranges.map { it.start }).isSorted()
        assertThat(store.ranges.all { r -> r.keys.all { store.rangeOf(it) === r } }).isTrue()
    }

    @Test
    fun `time-ordered keys always land in the last range, however often it splits`() {
        val store = DynamicRanges(maxKeys = 100, firstNode = "A")
        var lastRangeInserts = 0
        for (i in 0 until 2_000) {
            val key = "%013d".format(1_700_000_000_000L + i * 5)
            if (store.rangeOf(key) === store.ranges.last()) lastRangeInserts++
            store.insert(key)
        }
        assertThat(lastRangeInserts).isEqualTo(2_000)
        assertThat(store.ranges.size).isGreaterThan(30)
    }

    @Test
    fun `a new node takes whole ranges`() {
        val store = DynamicRanges(maxKeys = 1_000, firstNode = "node-01")
        keys.take(20_000).forEach(store::insert)
        val moved = movedKeys(keys.take(20_000), store) { store.addNode("node-02") }
        val ranges = store.ranges.count { it.node == "node-02" }
        assertThat(ranges).isEqualTo(store.ranges.size / 2)
        assertThat(moved).isEqualTo(store.ranges.filter { it.node == "node-02" }.sumOf { it.keys.size })
    }
}
