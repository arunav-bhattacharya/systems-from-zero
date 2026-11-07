package sfz.kafka.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** The ordering checks on hand-made consumer output. No broker needed. */
class KeyOrderingTest {
    // the producer sent seq 0..5: A0 B1 A2 C3 B4 A5. A is in partition 0, B and C in partition 1.
    // A consumer read all of partition 0, then all of partition 1.
    private val readByPartition = listOf(
        Seen("A", 0, 0, 0), Seen("A", 2, 0, 1), Seen("A", 5, 0, 2),
        Seen("B", 1, 1, 0), Seen("C", 3, 1, 1), Seen("B", 4, 1, 2),
    )

    @Test
    fun `per-key order holds when each key lives in one partition`() {
        assertThat(KeyOrdering.keysOutOfOrder(readByPartition)).isEmpty()
    }

    @Test
    fun `global order breaks at the first record that was sent earlier than the one before it`() {
        assertThat(KeyOrdering.firstGlobalBreak(readByPartition)).isEqualTo(3) // B1 arrives after A5
        assertThat(KeyOrdering.firstGlobalBreak(readByPartition.sortedBy { it.seq })).isEqualTo(-1)
        assertThat(KeyOrdering.firstGlobalBreak(emptyList())).isEqualTo(-1)
    }

    @Test
    fun `a key spread over two partitions can come back out of order`() {
        // ignore.keys sent A0 to partition 0 and A2 to partition 1; the consumer read partition 1 first
        val spread = listOf(Seen("A", 2, 1, 0), Seen("B", 1, 1, 1), Seen("A", 0, 0, 0))
        assertThat(KeyOrdering.keysOutOfOrder(spread)).containsExactly("A")
        assertThat(KeyOrdering.partitionsByKey(spread)).containsEntry("A", setOf(0, 1)).containsEntry("B", setOf(1))
    }

    @Test
    fun `records without a key are left out of the per-key checks`() {
        val mixed = readByPartition + Seen(null, 6, 0, 3) + Seen(null, 1, 1, 3)
        assertThat(KeyOrdering.keysOutOfOrder(mixed)).isEmpty()
        assertThat(KeyOrdering.partitionsByKey(mixed).keys).containsExactlyInAnyOrder("A", "B", "C")
    }

    @Test
    fun `growing a topic from 6 to 8 partitions moves about three keys in four`() {
        val keys = (0 until 10_000).map { "acct-$it" }
        val moved = KeyOrdering.movedKeys(keys, 6, 8)
        // a key stays only if hash % 6 == hash % 8, which holds for 6 of every 24 hash values
        assertThat(moved.size).isBetween(7_200, 7_800)
        for (key in keys.take(500)) {
            val stays = KeyPartitioner.partitionFor(key, 6) == KeyPartitioner.partitionFor(key, 8)
            assertThat(key in moved).isEqualTo(!stays)
        }
    }

    @Test
    fun `doubling the partition count moves half the keys, and no change moves none`() {
        val keys = (0 until 10_000).map { "acct-$it" }
        assertThat(KeyOrdering.movedKeys(keys, 6, 12).size).isBetween(4_700, 5_300)
        assertThat(KeyOrdering.movedKeys(keys, 6, 6)).isEmpty()
    }
}
