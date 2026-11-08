package sfz.derive.l05

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.IntRange
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** Exercises 3 and 4: build the tree, then descend only where the hashes differ. */
class MerkleTest {
    private val log = Ledger.log(seed = 5)
    private val truth = recompute(log)

    @Test
    fun `a parent is the hash of its two children`() {
        val t = MerkleTree(truth, leaves = 8)
        for (i in 1 until 8) assertThat(t.nodes[i]).isEqualTo(sha256(t.nodes[2 * i], t.nodes[2 * i + 1]))
    }

    @Test
    fun `equal views have equal roots, and one comparison proves it`() {
        val a = MerkleTree(truth)
        val b = MerkleTree(liveBalances(log))
        assertThat(a.root).isEqualTo(b.root)
        assertThat(compare(a, b)).isEqualTo(MerkleDiff(emptyList(), 1))
    }

    @Test
    fun `one bad account in 1,024 ranges is found with 21 comparisons instead of 1,024`() {
        val bad = account(123)
        val diffs = compare(MerkleTree(truth), MerkleTree(liveBalances(log, Fault.FlipBit(bad, 3))))
        assertThat(diffs.leaves).containsExactly(MerkleTree.leafOf(bad, 1_024))
        assertThat(diffs.comparisons).isEqualTo(1 + 2 * 10)     // the root, then both children at each of 10 levels
    }

    @Test
    fun `three bad accounts are found in their ranges, in order, with fewer than 61 comparisons`() {
        val bad = listOf(account(7), account(250), account(499))
        val live = liveBalances(log, *bad.map { Fault.FlipBit(it, 1) }.toTypedArray())
        val diffs = compare(MerkleTree(truth), MerkleTree(live))
        assertThat(diffs.leaves).containsExactlyElementsOf(bad.map { MerkleTree.leafOf(it, 1_024) }.toSortedSet())
        assertThat(diffs.comparisons).isLessThanOrEqualTo(3 * (2 * 10) + 1)
    }

    @Test
    fun `the ranges the tree points to hold every account the full diff finds`() {
        val live = liveBalances(log, Fault.DropEvery(1_000))
        val ranges = compare(MerkleTree(truth), MerkleTree(live)).leaves.toSet()
        for (d in diff(live, truth)) assertThat(ranges).contains(MerkleTree.leafOf(d.account, 1_024))
    }

    @Property(tries = 50)
    fun `any single changed account is found in its own range and nowhere else`(
        @ForAll @IntRange(min = 0, max = 499) acct: Int,
        @ForAll @IntRange(min = 0, max = 40) bit: Int,
    ) {
        val name = account(acct)
        val live = liveBalances(log, Fault.FlipBit(name, bit))
        assertThat(compare(MerkleTree(truth, 256), MerkleTree(live, 256)).leaves).containsExactly(MerkleTree.leafOf(name, 256))
    }
}
