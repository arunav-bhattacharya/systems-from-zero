package sfz.nosql.l10

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import kotlin.random.Random

class PaxosRegisterTest {
    private val b1 = Ballot(1, "p1")
    private val b2 = Ballot(2, "p2")

    @Test
    fun `an acceptor promises only ballots higher than every ballot it has promised`() {
        val a = Acceptor("A")
        assertThat(a.prepare(b1)).isEqualTo(Promise.Ok(null, null))
        assertThat(a.prepare(b1)).isEqualTo(Promise.Rejected(b1)) // the same ballot twice is not "higher"
        assertThat(a.prepare(b2)).isEqualTo(Promise.Ok(null, null))
        assertThat(a.prepare(b1)).isEqualTo(Promise.Rejected(b2))
        assertThat(a.promised).isEqualTo(b2)
    }

    @Test
    fun `an acceptor refuses a proposal below its promise, and reports what it accepted in later promises`() {
        val a = Acceptor("A")
        a.prepare(b2)
        assertThat(a.accept(Proposal(b1, "pay-1"))).isFalse() // p2 prepared after p1: p1 is too late
        assertThat(a.inProgress).isNull()
        assertThat(a.accept(Proposal(b2, "pay-2"))).isTrue()
        assertThat(a.prepare(Ballot(3, "p3"))).isEqualTo(Promise.Ok(Proposal(b2, "pay-2"), null))
        a.commit(Proposal(b2, "pay-2"))
        assertThat(a.prepare(Ballot(4, "p4"))).isEqualTo(Promise.Ok(null, Proposal(b2, "pay-2")))
    }

    @Test
    fun `IF NOT EXISTS on an empty row is applied in four round trips and every replica commits it`() {
        val r = PaxosRegister()
        assertThat(r.compareAndSet("p1", expected = null, newValue = "pay-81723")).isEqualTo(CasResult.Applied(4))
        assertThat(r.names.map(r::valueAt)).containsOnly("pay-81723")
        assertThat(r.acceptors.map { it.inProgress }).containsOnlyNulls()
    }

    @Test
    fun `a second IF NOT EXISTS is not applied and returns the row that won, after two round trips`() {
        val r = PaxosRegister()
        r.compareAndSet("p1", null, "pay-81723")
        assertThat(r.compareAndSet("p2", null, "pay-81799")).isEqualTo(CasResult.NotApplied("pay-81723", 2))
        assertThat(r.names.map(r::valueAt)).containsOnly("pay-81723")
        // IF balance = 10000 style: the condition names the current value
        assertThat(r.compareAndSet("p3", "pay-81723", "pay-81723-voided")).isEqualTo(CasResult.Applied(4))
    }

    @Test
    fun `one replica down still works, two down is Unavailable and changes nothing`() {
        val r = PaxosRegister()
        r.fail("C")
        assertThat(r.compareAndSet("p1", null, "pay-1")).isEqualTo(CasResult.Applied(4))
        assertThat(r.valueAt("C")).isNull() // C was down: it missed the commit
        r.fail("B")
        assertThat(r.compareAndSet("p2", "pay-1", "pay-2")).isEqualTo(CasResult.Unavailable)
        assertThat(r.valueAt("A")).isEqualTo("pay-1")
        assertThat(r.acceptor("A").promised).isEqualTo(Ballot(1, "p1")) // not even a prepare was sent
    }

    @Test
    fun `a proposer that slips in between read and propose wins, and the first one is Contended, never both`() {
        val r = PaxosRegister()
        var second: CasResult? = null
        val first = r.compareAndSet("p1", null, "pay-1", beforePropose = {
            second = r.compareAndSet("p2", null, "pay-2") // p2 prepares a higher ballot after p1's read
        })
        assertThat(second).isEqualTo(CasResult.Applied(4))
        assertThat(first).isEqualTo(CasResult.Contended(Ballot(2, "p2")))
        assertThat(r.names.map(r::valueAt)).containsOnly("pay-2")
    }

    @Test
    fun `an accepted value that never got committed is finished by the next proposer, not overwritten`() {
        val r = PaxosRegister()
        // p1 prepared on all three, but its accept reached only A before p1's coordinator crashed
        r.acceptors.forEach { it.prepare(b1) }
        r.acceptor("A").accept(Proposal(b1, "pay-1"))
        // p2's quorum includes A, so p2 sees pay-1 in progress, finishes it (2 trips), starts again
        assertThat(r.compareAndSet("p2", null, "pay-2")).isEqualTo(CasResult.NotApplied("pay-1", 5))
        assertThat(r.names.map(r::valueAt)).containsOnly("pay-1")
    }

    @Test
    fun `a value accepted by a minority that the next quorum never sees was never chosen, so it can lose`() {
        val r = PaxosRegister()
        r.acceptors.forEach { it.prepare(b1) }
        r.acceptor("A").accept(Proposal(b1, "pay-1"))
        // p2 can't reach A: B and C know nothing about pay-1, and it was on 1 of 3, never a majority
        assertThat(r.compareAndSet("p2", null, "pay-2", reaches = setOf("B", "C"))).isEqualTo(CasResult.Applied(4))
        // later A is back in the quorum, still holding pay-1 in progress. It is older than the commit: ignored
        assertThat(r.compareAndSet("p3", null, "pay-3", reaches = setOf("A", "B"))).isEqualTo(CasResult.NotApplied("pay-2", 2))
    }

    @Test
    fun `racing claims with failures and lost messages never commit two winners`() {
        val random = Random(7)
        repeat(300) { round ->
            val r = PaxosRegister()
            val results = mutableListOf<Pair<String, CasResult>>()
            fun claim(p: String, depth: Int) {
                // each attempt reaches a random set of acceptors; sometimes a rival cuts in before propose
                val reaches = r.names.filter { random.nextInt(4) != 0 }.toSet()
                val result = r.compareAndSet(p, null, "pay-$p", reaches, beforePropose = {
                    if (depth < 3 && random.nextBoolean()) claim("$p.${depth + 1}", depth + 1)
                })
                results += p to result
            }
            // sometimes an earlier coordinator crashed after its accept reached one acceptor
            if (random.nextBoolean()) {
                r.acceptors.forEach { it.prepare(Ballot(1, "crashed")) }
                r.acceptors.random(random).accept(Proposal(Ballot(1, "crashed"), "pay-crashed"))
            }
            repeat(4) { claim("p$it", 0) }
            val winners = results.filter { it.second is CasResult.Applied }.map { "pay-${it.first}" }
            assertThat(winners).`as`("round $round: $results").hasSizeLessThanOrEqualTo(1)
            // everyone told "not applied" was shown the one value that is actually committed
            val committed = r.acceptors.mapNotNull { it.committed }.maxByOrNull { it.ballot }?.value
            results.map { it.second }.filterIsInstance<CasResult.NotApplied>().forEach {
                assertThat(it.current).`as`("round $round").isEqualTo(committed)
            }
            winners.singleOrNull()?.let { assertThat(committed).`as`("round $round").isEqualTo(it) }
        }
    }
}
