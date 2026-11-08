package sfz.dist.l06

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.IntRange
import net.jqwik.api.constraints.LongRange
import org.assertj.core.api.Assertions.assertThat

/** Vector clocks know happens-before exactly; Lamport and hybrid stamps must never contradict them. */
class CausalityPropertyTest {
    @Property(tries = 100)
    fun `if a happened before b, both Lamport and hybrid stamps put a first`(
        @ForAll seed: Long,
        @ForAll @IntRange(min = 2, max = 6) nodes: Int,
        @ForAll @LongRange(min = 0, max = 100) maxSkewMs: Long,
    ) {
        val h = Histories.generate(seed, nodes = nodes, events = 150, maxSkewMs = maxSkewMs)
        val vc = vectorStamps(h)
        val lamport = lamportStamps(h)
        val hlc = hlcStamps(h)
        for (a in h.events.indices) for (b in h.events.indices) {
            if (vc[a] happenedBefore vc[b]) {
                assertThat(lamport[a]).`as`("Lamport, event $a before event $b").isLessThan(lamport[b])
                assertThat(hlc[a]).`as`("HLC, event $a before event $b").isLessThan(hlc[b])
            }
        }
    }

    @Property(tries = 50)
    fun `Lamport stamps are unique, so they order every pair, concurrent or not`(@ForAll seed: Long) {
        val h = Histories.generate(seed, nodes = 4, events = 200)
        val lamport = lamportStamps(h)
        assertThat(lamport.toSet()).hasSize(lamport.size)
    }

    @Property(tries = 100)
    fun `l never falls behind the node's wall clock, nor runs ahead by more than the skew`(
        @ForAll seed: Long,
        @ForAll @LongRange(min = 0, max = 200) maxSkewMs: Long,
    ) {
        val h = Histories.generate(seed, nodes = 5, events = 300, maxSkewMs = maxSkewMs)
        val hlc = hlcStamps(h)
        val skew = h.offsets.max() - h.offsets.min()                // the largest disagreement between two clocks
        for ((i, e) in h.events.withIndex()) {
            assertThat(hlc[i].l).`as`("event $i").isBetween(e.physical, e.physical + skew)
        }
    }

    @Property(tries = 50)
    fun `stamps on a node keep growing when its wall clock steps back`(
        @ForAll seed: Long,
        @ForAll @LongRange(min = 1, max = 2_000) stepMs: Long,
    ) {
        val h = Histories.generate(seed, nodes = 3, events = 300, steps = listOf(Step(node = 1, atRealMs = 300, byMs = stepMs)))
        val hlc = hlcStamps(h)
        for (node in 0 until h.nodes) {
            val mine = h.events.indices.filter { h.events[it].node == node }.map { hlc[it] }
            assertThat(mine).`as`("node $node").isSorted()
            assertThat(mine.toSet()).hasSize(mine.size)
        }
    }

    @Property(tries = 30)
    fun `with a few milliseconds of skew the counter is usually 0`(@ForAll seed: Long) {
        val h = Histories.generate(seed, nodes = 4, events = 400, maxSkewMs = 3, delayMs = 5L..20L, meanGapMs = 10)
        val counters = hlcStamps(h).map { it.c }
        assertThat(counters.count { it == 0 }.toDouble() / counters.size).isGreaterThan(0.6)
        assertThat(counters.max()).isLessThan(10)
    }
}
