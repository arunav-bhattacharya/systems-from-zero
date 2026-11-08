package sfz.cons.l05

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout

@Timeout(10)
class ElectionTest {
    private class World(fenced: Boolean = true) {
        val sim = Sim()
        val coord = Coordinator(sim)
        val ledger = Ledger(sim, fenced)
        fun candidate(name: String, startAt: Long): Candidate {
            val c = Candidate(name, sim, coord, ledger, ttlMs = 3_000, workEveryMs = 500)
            sim.at(startAt) { c.start() }
            return c
        }
    }

    // ---------------------------------------------------------------- the fence on its own

    @Test
    fun `a fenced ledger refuses a token lower than one it has accepted`() {
        val sim = Sim()
        val ledger = Ledger(sim)
        assertThat(ledger.append(33, "pod-a")).isTrue()
        assertThat(ledger.append(33, "pod-a")).`as`("the same leader writes again").isTrue()
        assertThat(ledger.append(34, "pod-b")).`as`("a newer leader").isTrue()
        assertThat(ledger.append(33, "pod-a")).`as`("the old leader, after the new one wrote").isFalse()
        assertThat(ledger.highestToken).isEqualTo(34)
        assertThat(ledger.rejected).isEqualTo(1)
        assertThat(ledger.entries.map { it.token }).containsExactly(33L, 33L, 34L)
    }

    // ---------------------------------------------------------------- the recipe

    @Test
    fun `the lowest sequence number leads and every other candidate watches only the one before it`() {
        val w = World()
        val a = w.candidate("pod-a", 0)
        val b = w.candidate("pod-b", 10)
        val c = w.candidate("pod-c", 20)
        w.sim.runUntil(100)
        assertThat(listOf(a, b, c).map { it.isLeader }).containsExactly(true, false, false)
        assertThat(listOf(a, b, c).map { it.node })
            .containsExactly("/election/n-0000000000", "/election/n-0000000001", "/election/n-0000000002")
        assertThat(a.token).`as`("the leader's token is its node's createRevision").isEqualTo(1)
        assertThat(listOf(a, b, c).map { it.watchesSet }).containsExactly(0, 1, 1)
    }

    @Test
    fun `when the leader dies only the next candidate is woken and it leads with a higher token`() {
        val w = World()
        val a = w.candidate("pod-a", 0)
        val b = w.candidate("pod-b", 10)
        val c = w.candidate("pod-c", 20)
        w.sim.at(1_500) { a.crash() }                    // its last keep-alive was at 1,000: the lease ends at 4,000
        w.sim.runUntil(4_001)
        assertThat(b.isLeader).`as`("the watch event is still on its way").isFalse()
        w.sim.runUntil(4_002)
        assertThat(b.isLeader).isTrue()
        assertThat(b.token).isEqualTo(2)
        assertThat(c.isLeader).isFalse()
        assertThat(w.coord.notificationsSent).`as`("one leader died, one process woke up: no herd").isEqualTo(1)

        w.sim.at(5_000) { b.crash() }
        w.sim.runUntil(10_000)
        assertThat(c.isLeader).isTrue()
        assertThat(c.token).isEqualTo(3)
        assertThat(w.coord.notificationsSent).isEqualTo(2)
        assertThat(w.ledger.entries.map { it.writer }.distinct()).containsExactly("pod-a", "pod-b", "pod-c")
        assertThat(w.ledger.entries.map { it.token }).isSorted()
    }

    // ---------------------------------------------------------------- the paused leader

    private fun pausedLeader(fenced: Boolean): Triple<World, Candidate, Candidate> {
        val w = World(fenced)
        val a = w.candidate("pod-a", 0)
        val b = w.candidate("pod-b", 10)
        w.sim.at(1_200) { a.pause(6_000) }               // a GC pause, or a stopped VM, from 1,200 to 7,200
        w.sim.runUntil(10_000)
        return Triple(w, a, b)
    }

    @Test
    fun `a leader paused past its lease is replaced, and its late write is refused`() {
        val (w, a, b) = pausedLeader(fenced = true)
        assertThat(b.isLeader).isTrue()
        assertThat(b.token).isEqualTo(2)
        assertThat(a.isLeader).`as`("after waking, its keep-alive failed and it rejoined").isFalse()
        assertThat(a.node).`as`("it rejoined at the back, with a new number").isEqualTo("/election/n-0000000002")
        assertThat(w.ledger.rejected).`as`("the write pod-a had in flight when it froze").isEqualTo(1)

        val byA = w.ledger.entries.filter { it.writer == "pod-a" }
        val byB = w.ledger.entries.filter { it.writer == "pod-b" }
        assertThat(byA.map { it.at }).containsExactly(500L, 1_000L)
        assertThat(byB.first().at).`as`("pod-b leads from 4,002 and writes on its next tick").isEqualTo(4_010L)
        assertThat(w.ledger.entries.map { it.token }).isSorted()
    }

    @Test
    fun `without the fence the paused leader's write lands after the new leader's`() {
        val (w, _, _) = pausedLeader(fenced = false)
        val late = w.ledger.entries.single { it.at == 7_200L }
        assertThat(late.writer).isEqualTo("pod-a")
        assertThat(late.token).isEqualTo(1)
        val before = w.ledger.entries.filter { it.at < 7_200L }
        assertThat(before.last().token).`as`("pod-b had already written with token 2").isEqualTo(2)
    }
}
