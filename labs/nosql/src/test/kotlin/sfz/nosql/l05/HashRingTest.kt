package sfz.nosql.l05

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test
import sfz.nosql.l05.HashRing.Companion.position

class HashRingTest {
    private val keys = (0 until 20_000).map { "pay-$it" }
    private val four = listOf("node-A", "node-B", "node-C", "node-D")

    private fun ring(tokensPerNode: Int, nodes: List<String>) = HashRing(tokensPerNode).apply { nodes.forEach(::addNode) }

    /** The spec, written the slow way: every token, sorted, then the first one at or after the key. */
    private fun slowOwner(key: String, tokensPerNode: Int, nodes: List<String>): String {
        val tokens = nodes.flatMap { n -> (0 until tokensPerNode).map { position("$n#$it") to n } }.sortedBy { it.first }
        return (tokens.firstOrNull { it.first >= position(key) } ?: tokens.first()).second
    }

    @Test
    fun `addNode puts tokensPerNode tokens for each node on the ring`() {
        val r = ring(16, four)
        assertThat(r.tokenCount).isEqualTo(64)
        assertThat(r.nodes).containsExactlyInAnyOrderElementsOf(four)
        assertThat(r.ownership().values.sum()).isCloseTo(1.0, within(1e-9))
    }

    @Test
    fun `ownerOf takes the first token at or after the key, and wraps past the top`() {
        for (t in listOf(1, 16)) {
            val r = ring(t, four)
            for (key in keys.take(2_000)) assertThat(r.ownerOf(key)).`as`(key).isEqualTo(slowOwner(key, t, four))
        }
        // a key above every token belongs to the node with the smallest token
        val r = ring(1, four)
        val top = four.maxOf { position("$it#0") }
        val wrapped = keys.first { position(it) > top }
        assertThat(r.ownerOf(wrapped)).isEqualTo(four.minBy { position("$it#0") })
    }

    @Test
    fun `hash mod S moves most keys when a fifth node joins`() {
        val five = four + "node-E"
        val moved = keys.count { HashRing.modOwner(it, four) != HashRing.modOwner(it, five) }
        assertThat(moved.toDouble() / keys.size).isGreaterThan(0.75)
    }

    @Test
    fun `on the ring, a joining node takes keys and nobody else swaps any`() {
        for (t in listOf(1, 16)) {
            val r = ring(t, four)
            val before = keys.associateWith(r::ownerOf)
            r.addNode("node-E")
            val moved = keys.filter { r.ownerOf(it) != before[it] }
            // every key that moved, moved TO the new node
            assertThat(moved).allMatch { r.ownerOf(it) == "node-E" }
            // and the new node got about its share of the ring
            assertThat(moved.size.toDouble() / keys.size).isCloseTo(r.ownership().getValue("node-E"), within(0.02))
        }
    }

    @Test
    fun `with one token the new node takes from one neighbour, with sixteen from several`() {
        fun donors(t: Int): Set<String> {
            val r = ring(t, four)
            val before = keys.associateWith(r::ownerOf)
            r.addNode("node-E")
            return keys.filter { r.ownerOf(it) == "node-E" }.map { before.getValue(it) }.toSet()
        }
        assertThat(donors(1)).hasSize(1)
        assertThat(donors(16).size).isGreaterThanOrEqualTo(3)
    }

    @Test
    fun `removing a node hands its keys to the others and moves nothing else`() {
        val r = ring(16, four + "node-E")
        val before = keys.associateWith(r::ownerOf)
        r.removeNode("node-C")
        for (key in keys) {
            if (before[key] != "node-C") assertThat(r.ownerOf(key)).isEqualTo(before[key])
            else assertThat(r.ownerOf(key)).isNotEqualTo("node-C")
        }
    }

    @Test
    fun `virtual nodes even out how much of the ring each node owns`() {
        val ten = (0 until 10).map { "node-$it" }
        val one = ring(1, ten).ownership()
        val many = ring(256, ten).ownership()
        // one token each: the luckiest node owns more than twice its fair 10%
        assertThat(one.values.max()).isGreaterThan(0.2)
        // 256 tokens each: every node within 20% of its fair share
        assertThat(many.values).allMatch { it in 0.08..0.12 }
    }

    @Test
    fun `preferenceList returns n distinct physical nodes, owner first, in ring order`() {
        val five = four + "node-E"
        val r = ring(16, five)
        val tokens = five.flatMap { n -> (0 until 16).map { position("$n#$it") to n } }.sortedBy { it.first }
        for (key in keys.take(1_000)) {
            val list = r.preferenceList(key, 3)
            assertThat(list).`as`(key).hasSize(3).doesNotHaveDuplicates()
            assertThat(list.first()).isEqualTo(r.ownerOf(key))
            // the slow way: walk the sorted tokens from the key, twice round at most, skipping repeats
            val start = tokens.indexOfFirst { it.first >= position(key) }.let { if (it < 0) 0 else it }
            val expected = (tokens.indices).map { tokens[(start + it) % tokens.size].second }.distinct().take(3)
            assertThat(list).`as`(key).isEqualTo(expected)
        }
        // fewer nodes than copies asked for: every node, once
        assertThat(ring(16, listOf("node-A", "node-B")).preferenceList("pay-81723", 3))
            .containsExactlyInAnyOrder("node-A", "node-B")
    }
}
