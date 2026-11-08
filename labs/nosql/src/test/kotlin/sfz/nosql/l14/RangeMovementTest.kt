package sfz.nosql.l14

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test
import sfz.nosql.support.NodetoolCaptures

/**
 * Checks the range-movement model against what the lab cluster really did when cass4 joined and
 * then left (captured with nodetool and from cass4's log, in src/test/resources/sfz/nosql/l14).
 */
class RangeMovementTest {
    private val names = mapOf("172.21.0.2" to "cass1", "172.21.0.3" to "cass2", "172.21.0.4" to "cass3", "172.21.0.5" to "cass4")

    private fun ring(resource: String) =
        Ring(NodetoolCaptures.ring("/sfz/nosql/l14/$resource").associate { it.token to names.getValue(it.address) }, rf = 3)

    private val before = ring("ring-before-join.txt")
    private val after = ring("ring-after-join.txt")
    private val cass4Tokens = after.tokens.filterValues { it == "cass4" }.keys

    @Test
    fun `the captured rings are three nodes, then four, with sixteen tokens each`() {
        assertThat(before.tokens).hasSize(48)
        assertThat(after.tokens).hasSize(64)
        assertThat(after.tokens.filterValues { it != "cass4" }).isEqualTo(before.tokens) // nobody else's tokens moved
        assertThat(before.withNode("cass4", cass4Tokens).tokens).isEqualTo(after.tokens)
    }

    @Test
    fun `the given replica walk agrees with nodetool describering, range by range`() {
        val described = NodetoolCaptures.describering("/sfz/nosql/l14/describering-after-join.txt")
        assertThat(described).hasSize(after.ranges.size)
        for (d in described) {
            assertThat(after.replicas(TokenRange(d.start, d.end))).`as`("(${d.start}, ${d.end}]")
                .containsExactlyElementsOf(d.endpoints.map(names::getValue))
        }
    }

    @Test
    fun `the given owns() matches Owns (effective) in nodetool status`() {
        // from status-after-join.txt: cass3 77.4%, cass4 73.2%, cass2 74.7%, cass1 74.7%
        val printed = mapOf("cass1" to 0.747, "cass2" to 0.747, "cass3" to 0.774, "cass4" to 0.732)
        for ((node, owns) in printed) assertThat(after.owns(node)).`as`(node).isCloseTo(owns, within(0.0006))
        assertThat(before.owns("cass1")).isCloseTo(1.0, within(1e-9)) // three nodes, three copies: everyone has everything
    }

    @Test
    fun `bootstrap streams each new range from the one replica the newcomer replaces`() {
        val plan = RangeMovement.bootstrapSources(before, after, "cass4")
        // every range cass4 now replicates is fetched exactly once
        assertThat(plan.values.flatten()).hasSize(after.rangesOf("cass4").size).doesNotHaveDuplicates()
        assertThat(plan.values.flatten().toSet()).isEqualTo(after.rangesOf("cass4"))
        // from three different nodes, in parallel, and never from cass4 itself
        assertThat(plan.keys).containsExactlyInAnyOrder("cass1", "cass2", "cass3")
        for ((source, ranges) in plan) for (r in ranges) {
            assertThat(before.replicasOf(r.end)).contains(source)
            assertThat(after.replicas(r)).doesNotContain(source)
        }
    }

    @Test
    fun `the plan matches the stream sources cass4 logged while it joined`() {
        val logged = NodetoolCaptures.streamSources("/sfz/nosql/l14/bootstrap-sources.txt").filter { it.keyspace == "payments" }
        assertThat(logged).hasSize(47)
        val plan = RangeMovement.bootstrapSources(before, after, "cass4")
        val predicted = plan.flatMap { (source, ranges) -> ranges.map { it to source } }.toMap()
        for (line in logged) {
            assertThat(predicted[TokenRange(line.start, line.end)]).`as`("(${line.start},${line.end}]")
                .isEqualTo(names.getValue(line.source))
        }
        assertThat(predicted).hasSize(logged.size)
    }

    @Test
    fun `cleanup deletes on each old node exactly what it streamed to the newcomer`() {
        val streamed = RangeMovement.bootstrapSources(before, after, "cass4")
        val cleaned = RangeMovement.cleanup(before, after)
        assertThat(cleaned).isEqualTo(streamed)
        // and afterwards each old node holds just its new share: from 100% down to about 75%
        for (node in listOf("cass1", "cass2", "cass3")) {
            val kept = after.ranges.filter { node in before.replicasOf(it.end) } - cleaned.getValue(node)
            assertThat(kept.sumOf { it.share }).`as`(node).isCloseTo(after.owns(node), within(1e-9))
        }
    }

    @Test
    fun `decommission hands every range back to the node it came from`() {
        val handedBack = RangeMovement.decommissionTargets(after, "cass4")
        assertThat(handedBack).isEqualTo(RangeMovement.bootstrapSources(before, after, "cass4"))
        // and the ring nodetool printed after the decommission is the ring from before the join
        assertThat(ring("ring-after-decommission.txt").tokens).isEqualTo(before.tokens)
        assertThat(after.withoutNode("cass4").tokens).isEqualTo(before.tokens)
    }

    @Test
    fun `with one token per node, a joining node streams everything from one neighbour`() {
        // a small ring with RF 1, so each range has one replica and the picture is lesson 5's
        val small = Ring(mapOf(-6_000L to "a", -1_000L to "b", 4_000L to "c"), rf = 1)
        val grown = small.withNode("d", listOf(2_000L))
        val plan = RangeMovement.bootstrapSources(small, grown, "d")
        assertThat(plan).isEqualTo(mapOf("c" to setOf(TokenRange(-1_000L, 2_000L))))
        assertThat(RangeMovement.cleanup(small, grown)).isEqualTo(plan)
        assertThat(RangeMovement.decommissionTargets(grown, "d")).isEqualTo(plan)
    }
}
