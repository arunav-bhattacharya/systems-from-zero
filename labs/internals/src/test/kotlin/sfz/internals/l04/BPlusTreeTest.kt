package sfz.internals.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import java.util.TreeMap
import kotlin.random.Random

class BPlusTreeTest {
    private fun v(k: Long) = "pay-$k"

    /** A tree holding [keys], inserted in the given order. */
    private fun treeOf(keys: List<Long>, order: Int = 4) = BPlusTree(order).also { t -> keys.forEach { t.put(it, v(it)) } }

    private fun shuffled(n: Int, seed: Int = 42) = (1..n.toLong()).shuffled(Random(seed))

    @Test
    fun `an empty tree is one empty leaf`() {
        val t = BPlusTree()
        assertThat(t.get(7)).isNull()
        assertThat(t.range(0, 100)).isEmpty()
        assertThat(t.height).isEqualTo(1)
        assertThat(t.levels()).isEqualTo(listOf(listOf(emptyList<Long>())))
    }

    @Test
    fun `the fourth key splits the root leaf and copies the first key of the right half up`() {
        val t = treeOf(listOf(10, 20, 30))
        assertThat(t.levels()).`as`("three keys still fit in one leaf").isEqualTo(listOf(listOf(listOf(10L, 20L, 30L))))
        t.put(40, v(40))
        // 30 is in the root AND in the right leaf: a leaf split copies its separator up
        assertThat(t.levels()).isEqualTo(
            listOf(
                listOf(listOf(30L)),
                listOf(listOf(10L, 20L), listOf(30L, 40L)),
            )
        )
        assertThat(t.height).isEqualTo(2)
        for (k in listOf(10L, 20L, 30L, 40L)) assertThat(t.get(k)).isEqualTo(v(k))
    }

    @Test
    fun `a full internal node splits and pushes its middle key up into a new root`() {
        val t = treeOf((10L..90L step 10).toList())
        assertThat(t.levels()).`as`("after 10 to 90").isEqualTo(
            listOf(
                listOf(listOf(30L, 50L, 70L)),
                listOf(listOf(10L, 20L), listOf(30L, 40L), listOf(50L, 60L), listOf(70L, 80L, 90L)),
            )
        )
        t.put(100, v(100))
        // the leaf split sends 90 up, the root now has 4 keys and splits: 70 moves up and is in neither half
        assertThat(t.levels()).`as`("after 100").isEqualTo(
            listOf(
                listOf(listOf(70L)),
                listOf(listOf(30L, 50L), listOf(90L)),
                listOf(listOf(10L, 20L), listOf(30L, 40L), listOf(50L, 60L), listOf(70L, 80L), listOf(90L, 100L)),
            )
        )
        assertThat(t.height).isEqualTo(3)
        t.checkInvariants()
    }

    @Test
    fun `put on an existing key replaces the value and adds nothing`() {
        val t = treeOf(shuffled(50))
        val pages = t.pageCount
        t.put(17, "pay-17-captured")
        assertThat(t.get(17)).isEqualTo("pay-17-captured")
        assertThat(t.size).isEqualTo(50)
        assertThat(t.pageCount).`as`("pages after replacing a value").isEqualTo(pages)
    }

    @Test
    fun `random inserts keep every key findable and every invariant true after each insert`() {
        val t = BPlusTree()
        val keys = shuffled(2_000)
        for ((i, k) in keys.withIndex()) {
            t.put(k, v(k))
            try {
                t.checkInvariants()
            } catch (e: IllegalStateException) {
                throw AssertionError("after insert #${i + 1} (key $k): ${e.message}", e)
            }
        }
        assertThat(t.size).isEqualTo(2_000)
        for (k in keys) assertThat(t.get(k)).`as`("get($k)").isEqualTo(v(k))
        assertThat(t.get(0)).isNull()
        assertThat(t.get(2_001)).isNull()
    }

    @Test
    fun `the tree only grows taller when the root splits, one level at a time`() {
        val t = BPlusTree()
        var height = 1
        for (k in shuffled(1_000, seed = 7)) {
            t.put(k, v(k))
            if (t.height != height) {
                assertThat(t.height).`as`("height after inserting $k").isEqualTo(height + 1)
                assertThat(t.levels().first()).`as`("a brand-new root holds one separator").hasSize(1)
                assertThat(t.levels().first().single()).hasSize(1)
                height = t.height
            }
        }
        // leaves hold 2 or 3 keys and internal nodes 2 to 4 children, so 1,000 keys need 6 to 9 levels
        assertThat(t.height).isBetween(6, 9)
        t.checkInvariants()
    }

    @Test
    fun `a lookup reads exactly one page per level`() {
        val t = treeOf(shuffled(1_000))
        for (k in listOf(1L, 2L, 500L, 999L, 1_000L, 5_000L)) {
            t.resetPageReads()
            t.get(k)
            assertThat(t.pageReads).`as`("page reads for get($k) in a tree of height ${t.height}").isEqualTo(t.height.toLong())
        }
    }

    @Test
    fun `range returns the same entries as TreeMap subMap for 200 random ranges`() {
        val rnd = Random(2026)
        val keys = (1..3_000).map { rnd.nextLong(0, 10_000) }.distinct()
        val t = BPlusTree()
        val expected = TreeMap<Long, String>()
        for (k in keys) {
            t.put(k, v(k))
            expected[k] = v(k)
        }
        repeat(200) {
            val a = rnd.nextLong(-50, 10_050)
            val b = a + rnd.nextLong(0, 800)
            val want = expected.subMap(a, true, b, true).map { it.key to it.value }
            assertThat(t.range(a, b)).`as`("range($a, $b)").isEqualTo(want)
        }
        assertThat(t.range(5, 4)).`as`("lo > hi").isEmpty()
        val one = expected.firstKey()
        assertThat(t.range(one, one)).isEqualTo(listOf(one to v(one)))
        assertThat(t.range(Long.MIN_VALUE, Long.MAX_VALUE).map { it.first }).`as`("the whole leaf chain").isEqualTo(expected.keys.toList())
    }

    @Test
    fun `a range scan descends once and then follows the leaf chain`() {
        val t = treeOf(shuffled(1_000))
        val leaves = t.levels().last().size
        t.resetPageReads()
        t.range(Long.MIN_VALUE, Long.MAX_VALUE)
        assertThat(t.pageReads).`as`("page reads for a full scan: the way down, then every other leaf once")
            .isEqualTo((t.height + leaves - 1).toLong())
        t.resetPageReads()
        assertThat(t.range(400, 409)).hasSize(10)
        // ten keys sit on at most six leaves: one descent, then a few sideways steps, not ten descents
        assertThat(t.pageReads).`as`("page reads for range(400, 409)").isLessThanOrEqualTo((t.height + 5).toLong())
    }

    @Test
    fun `a wider node makes a much shorter tree`() {
        val t = treeOf(shuffled(10_000), order = 64)
        t.checkInvariants()
        assertThat(t.height).`as`("height of an order-64 tree with 10,000 keys").isEqualTo(3)
        assertThat(t.range(1_000, 1_099).map { it.first }).isEqualTo((1_000L..1_099L).toList())
        t.resetPageReads()
        assertThat(t.get(4_242)).isEqualTo(v(4_242))
        assertThat(t.pageReads).isEqualTo(3)
    }
}
