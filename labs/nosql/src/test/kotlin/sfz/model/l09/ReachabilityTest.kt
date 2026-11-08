package sfz.model.l09

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class ReachabilityTest {
    /** C-1 owns C-2 owns C-3 ... owns C-n: the longest possible chain of control. */
    private fun chain(n: Int): Set<Fact> = (1 until n).mapTo(LinkedHashSet()) { Fact("C-$it", "C-${it + 1}") }

    @Test
    fun `on a five-company chain both evaluations find the same 10 facts in 4 rounds`() {
        val owns = chain(5)
        val naive = Reachability.naive(owns)
        val semi = Reachability.semiNaive(owns)
        assertThat(semi.facts).isEqualTo(naive.facts).hasSize(10).contains(Fact("C-1", "C-5"))
        assertThat(semi.iterations).isEqualTo(4)
        assertThat(naive.iterations).isEqualTo(4)
        // 4 base facts, then 3, 2, 1 and 0 new joins: every fact is derived exactly once
        assertThat(semi.derivations).isEqualTo(10)
        assertThat(naive.derivations).isEqualTo(24)
    }

    @Test
    fun `on a 200-company chain semi-naive does a small fraction of the naive work`() {
        val owns = chain(200)
        val naive = Reachability.naive(owns)
        val semi = Reachability.semiNaive(owns)
        assertThat(semi.facts).isEqualTo(naive.facts).hasSize(200 * 199 / 2)
        assertThat(semi.iterations).isEqualTo(199)
        assertThat(semi.derivations).isEqualTo(19_900)
        assertThat(naive.derivations).isGreaterThan(50 * semi.derivations)   // about 1.3 million
    }

    @Test
    fun `a cycle of ownership terminates, and every company ends up controlling every company`() {
        val owns = setOf(Fact("C-1", "C-2"), Fact("C-2", "C-3"), Fact("C-3", "C-1"))
        val semi = Reachability.semiNaive(owns)
        assertThat(semi.facts).hasSize(9).contains(Fact("C-1", "C-1"))
        assertThat(semi.iterations).isEqualTo(3)
        // round 3 joins three facts and finds only facts it already has
        assertThat(semi.derivations).isEqualTo(12)
        assertThat(Reachability.naive(owns).facts).isEqualTo(semi.facts)
    }

    @Test
    fun `a diamond derives the shared fact twice, once per route, but stores it once`() {
        // C-1 owns C-2 and C-3; both own M-0042
        val owns = setOf(Fact("C-1", "C-2"), Fact("C-1", "C-3"), Fact("C-2", "M-0042"), Fact("C-3", "M-0042"))
        val semi = Reachability.semiNaive(owns)
        assertThat(semi.facts).containsExactlyInAnyOrder(*owns.toTypedArray(), Fact("C-1", "M-0042"))
        assertThat(semi.derivations).isEqualTo(6)    // 4 base facts + the same new fact from two routes
        assertThat(semi.iterations).isEqualTo(2)
    }

    @Test
    fun `no facts, no work`() {
        val semi = Reachability.semiNaive(emptySet())
        assertThat(semi.facts).isEmpty()
        assertThat(semi.iterations).isZero()
        assertThat(semi.derivations).isZero()
    }
}
