package sfz.repl.l01

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test

/** Exercise 1, [Node.apply]: entries in log order, a new follower from a snapshot, and catch-up. */
class CatchUpTest {
    private fun entries(range: LongRange) = range.map { LogEntry(it, it, "pay-$it") }

    @Test
    fun `apply takes entries in order and moves the position`() {
        val node = Node("f1")
        assertThat(node.apply(entries(1L..3L))).isEqualTo(3)
        assertThat(node.position).isEqualTo(3)
        assertThat(node.rows).containsExactlyEntriesOf(mapOf(1L to "pay-1", 2L to "pay-2", 3L to "pay-3"))
        assertThat(node.log.map { it.position }).containsExactly(1L, 2L, 3L)
    }

    @Test
    fun `apply skips entries it already has, so a resend changes nothing`() {
        val node = Node("f1")
        node.apply(entries(1L..5L))
        assertThat(node.apply(entries(3L..7L))).isEqualTo(2)
        assertThat(node.position).isEqualTo(7)
        assertThat(node.log.map { it.position }).containsExactly(1L, 2L, 3L, 4L, 5L, 6L, 7L)
    }

    @Test
    fun `apply stops at a gap instead of applying out of order`() {
        val node = Node("f1")
        node.apply(entries(1L..2L))
        assertThat(node.apply(entries(4L..6L))).isEqualTo(0)
        assertThat(node.position).isEqualTo(2)
        assertThat(node.rows.keys).containsExactly(1L, 2L)
    }

    @Test
    fun `a new follower is a snapshot plus every entry after the snapshot's position`() {
        val sim = Sim()
        val cluster = Cluster(sim, Mode.Async, mapOf("f1" to 5L))
        cluster.writeEvery(10, from = 0, until = 590)            // 60 payments
        sim.runUntil(595)
        val snapshot = cluster.leader.snapshot()                 // taken at position 60
        cluster.writeEvery(10, from = 600, until = 990)          // 40 more while the copy is made
        sim.runUntil(1_000)

        val f2 = Node("f2")
        f2.restore(snapshot)
        val applied = f2.apply(cluster.leader.entriesAfter(snapshot.position))

        assertThat(snapshot.position).isEqualTo(60)
        assertThat(applied).isEqualTo(40)
        assertThat(f2.position).isEqualTo(cluster.leader.position)
        assertThat(f2.rows).isEqualTo(cluster.leader.rows)
    }

    @Test
    fun `a follower cut off for a while catches up when its link comes back`() {
        val sim = Sim()
        val cluster = Cluster(sim, Mode.Async, mapOf("f1" to 5L))
        val f1 = cluster.node("f1")
        cluster.writeEvery(10, from = 0, until = 990)
        sim.at(200) { cluster.cut += "f1" }
        sim.at(500) { cluster.cut -= "f1" }
        sim.runUntil(450)
        val stuckAt = f1.position
        sim.runUntil(1_100)

        assertThat(stuckAt).isEqualTo(20)                        // entries written from 200 on never arrived
        assertThat(f1.position).isEqualTo(100)
        assertThat(f1.rows).isEqualTo(cluster.leader.rows)
    }

    @Test
    fun `a follower whose missing entries are gone has to be rebuilt from a snapshot`() {
        val leader = Node("leader")
        leader.apply(entries(1L..100L))
        leader.truncateLogThrough(80)                            // the leader kept only 81..100
        val f1 = Node("f1")
        f1.apply(entries(1L..50L))

        assertThatThrownBy { f1.apply(leader.entriesAfter(f1.position)) }.isInstanceOf(LogGoneException::class.java)

        f1.restore(leader.snapshot())
        assertThat(f1.apply(leader.entriesAfter(f1.position))).isEqualTo(0)
        assertThat(f1.rows).isEqualTo(leader.rows)
    }
}
