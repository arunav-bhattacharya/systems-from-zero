package sfz.shard.l05

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.nosql.support.NodetoolCaptures
import java.nio.ByteBuffer
import java.security.MessageDigest

class PlacementTest {
    private fun position(text: String): Long =
        ByteBuffer.wrap(MessageDigest.getInstance("MD5").digest(text.toByteArray())).long

    /** A ring with 16 tokens per node, at the MD5 of "<name>#<i>", as in lesson 2's lab. */
    private fun ring(vararg nodes: Endpoint, tokensPerNode: Int = 16): TokenRing =
        TokenRing(nodes.flatMap { n -> (0 until tokensPerNode).map { position("${n.name}#$it") to n } }.toMap())

    private val keys = (0 until 2_000).map { TokenRing.murmur3("pay-$it") }

    // six nodes in dc1, two per rack, and three in dc2, all in one rack
    private val dc1 = (1..6).map { Endpoint("cass$it", "dc1", "rack${(it + 1) / 2}") }
    private val dc2 = (7..9).map { Endpoint("cass$it", "dc2", "rack1") }

    @Test
    fun `murmur3 gives the tokens Cassandra printed for the payment keys`() {
        // from lesson 2's Try-it: SELECT account_id, token(account_id) FROM payments.balances
        assertThat(TokenRing.murmur3("A-1001")).isEqualTo(-4994511478997274402)
        assertThat(TokenRing.murmur3("A-2002")).isEqualTo(1517767796525818520)
        assertThat(TokenRing.murmur3("M-0042")).isEqualTo(5210081981202411406)
    }

    @Test
    fun `each datacenter gets its own replication factor`() {
        val r = ring(*(dc1 + dc2).toTypedArray())
        for (k in keys) {
            val replicas = r.networkTopology(k, mapOf("dc1" to 3, "dc2" to 2))
            assertThat(replicas.count { it.dc == "dc1" }).isEqualTo(3)
            assertThat(replicas.count { it.dc == "dc2" }).isEqualTo(2)
            assertThat(replicas).doesNotHaveDuplicates()
        }
        // a datacenter missing from the map gets no copies
        assertThat(r.networkTopology(keys[0], mapOf("dc1" to 3))).allMatch { it.dc == "dc1" }
    }

    @Test
    fun `with at least as many racks as copies, every copy lands on its own rack`() {
        val r = ring(*dc1.toTypedArray())
        var simpleDoubledUp = 0
        for (k in keys) {
            val replicas = r.networkTopology(k, mapOf("dc1" to 3))
            assertThat(replicas.map { it.rack }).doesNotHaveDuplicates()
            if (r.simpleStrategy(k, 3).map { it.rack }.toSet().size < 3) simpleDoubledUp++
        }
        // SimpleStrategy ignores racks, so it often puts two copies in one rack
        assertThat(simpleDoubledUp).isGreaterThan(keys.size / 4)
    }

    @Test
    fun `a node in a rack already used is skipped, and the walk goes on`() {
        val a = Endpoint("A", "dc1", "r1")
        val b = Endpoint("B", "dc1", "r1")
        val c = Endpoint("C", "dc1", "r2")
        val d = Endpoint("D", "dc1", "r3")
        val r = TokenRing(mapOf(100L to a, 200L to b, 300L to c, 400L to d))
        // the walk from 150 meets B, C, D, A: B is the first copy, A would repeat rack r1
        assertThat(r.networkTopology(150, mapOf("dc1" to 3))).containsExactly(b, c, d)
        // from 50 it meets A, B (r1 again: skipped), C, D
        assertThat(r.networkTopology(50, mapOf("dc1" to 3))).containsExactly(a, c, d)
        // a token exactly on a node's token belongs to that node's range
        assertThat(r.networkTopology(300, mapOf("dc1" to 1))).containsExactly(c)
        // SimpleStrategy would have taken A and B together
        assertThat(r.simpleStrategy(50, 3)).containsExactly(a, b, c)
    }

    @Test
    fun `with fewer racks than copies, every rack is used and the first repeat is taken in walk order`() {
        val a = Endpoint("A", "dc1", "r1")
        val b = Endpoint("B", "dc1", "r1")
        val c = Endpoint("C", "dc1", "r1")
        val d = Endpoint("D", "dc1", "r2")
        val r = TokenRing(mapOf(100L to a, 200L to b, 300L to c, 400L to d))
        // RF 3, 2 racks: one repeat allowed. Walk A, B (repeat, allowed), C (repeat, not allowed), D (new rack).
        assertThat(r.networkTopology(50, mapOf("dc1" to 3))).containsExactly(a, b, d)
        // and a datacenter with fewer nodes than copies gets all its nodes
        val small = TokenRing(mapOf(100L to a, 400L to d))
        assertThat(small.networkTopology(50, mapOf("dc1" to 3))).containsExactly(a, d)
    }

    @Test
    fun `the only node in its rack holds a copy of everything`() {
        // racks of sizes 2, 2 and 1: with RF 3, every range needs one copy per rack
        val nodes = listOf(
            Endpoint("cass1", "dc1", "rack1"), Endpoint("cass2", "dc1", "rack1"),
            Endpoint("cass3", "dc1", "rack2"), Endpoint("cass4", "dc1", "rack2"),
            Endpoint("cass5", "dc1", "rack3"),
        )
        val r = ring(*nodes.toTypedArray())
        val copies = keys.flatMap { r.networkTopology(it, mapOf("dc1" to 3)) }.groupingBy { it.name }.eachCount()
        assertThat(copies.getValue("cass5")).isEqualTo(keys.size)               // 100% of the keys
        assertThat(copies.getValue("cass1").toDouble() / keys.size).isBetween(0.3, 0.7) // about half
    }

    @Test
    fun `on the captured three-node ring, the walk gives what nodetool getendpoints printed`() {
        val name = mapOf("172.23.0.2" to "cass1", "172.23.0.3" to "cass2", "172.23.0.4" to "cass3")
        val lines = NodetoolCaptures.ring("/sfz/shard/l05/ring-3-nodes.txt")
        assertThat(lines).hasSize(48) // 16 tokens on each of three nodes
        val r = TokenRing(lines.associate { it.token to Endpoint(name.getValue(it.address), "dc1", it.rack) })
        val printed = NodetoolCaptures.endpoints("/sfz/shard/l05/getendpoints-3-nodes.txt")
        for ((key, addresses) in printed) {
            assertThat(r.networkTopology(TokenRing.murmur3(key), mapOf("dc1" to 3)).map { it.name })
                .`as`(key).containsExactlyElementsOf(addresses.map(name::getValue))
        }
    }
}
