package sfz.repl.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * Exercise 2, [Cluster.isAcknowledged]: when the client hears "OK", and what a slow or dead
 * follower does to that. f1 is 20 ms from the leader and f2 is 50 ms, one way; a payment is
 * written every 4 ms.
 */
class AckTest {
    private fun cluster(mode: Mode, delays: Map<String, Long> = mapOf("f1" to 20L, "f2" to 50L)): Pair<Sim, Cluster> {
        val sim = Sim()
        val cluster = Cluster(sim, mode, delays)
        cluster.writeEvery(4, from = 0, until = 996)            // 250 payments in one second
        return sim to cluster
    }

    @Test
    fun `asynchronous replication answers at once`() {
        val (sim, cluster) = cluster(Mode.Async)
        sim.runUntil(2_000)
        assertThat(cluster.acknowledged.size).isEqualTo(250)
        assertThat(cluster.acknowledged.map { it.latencyMs }.distinct()).containsExactly(0L)
    }

    @Test
    fun `waiting for one follower costs a round trip to the nearest one`() {
        val (sim, cluster) = cluster(Mode.Sync(1))
        sim.runUntil(2_000)
        assertThat(cluster.acknowledged.size).isEqualTo(250)
        assertThat(cluster.acknowledged.map { it.latencyMs }.distinct()).containsExactly(40L)
    }

    @Test
    fun `waiting for every follower costs a round trip to the slowest one`() {
        val (sim, cluster) = cluster(Mode.Sync(2))
        sim.runUntil(2_000)
        assertThat(cluster.acknowledged.size).isEqualTo(250)
        assertThat(cluster.acknowledged.map { it.latencyMs }.distinct()).containsExactly(100L)
    }

    @Test
    fun `waiting for every follower stops all writes when one of them dies`() {
        val (sim, cluster) = cluster(Mode.Sync(2))
        sim.at(500) { cluster.crash(cluster.node("f2")) }
        sim.runUntil(5_000)
        // payments written before about 400 ms made the round trip to f2; nothing after that ever returns
        assertThat(cluster.acknowledged.maxOf { it.entry.position }).isLessThan(115)
        assertThat(cluster.acknowledged.size).isLessThan(115)
        assertThat(cluster.leader.position).isEqualTo(250)       // the leader has them all, and can't say OK
    }

    @Test
    fun `waiting for one of two followers carries on when one dies`() {
        val (sim, cluster) = cluster(Mode.Sync(1))
        sim.at(500) { cluster.crash(cluster.node("f1")) }
        sim.runUntil(5_000)
        assertThat(cluster.acknowledged.size).isEqualTo(250)
        assertThat(cluster.acknowledged.last().latencyMs).isEqualTo(100L)  // now f2's round trip
    }

    @Test
    fun `semi-sync with a healthy follower waits for one confirmation and stays on`() {
        val (sim, cluster) = cluster(Mode.SemiSync(timeoutMs = 500))
        sim.runUntil(2_000)
        assertThat(cluster.semiSyncOn).isTrue()
        assertThat(cluster.acknowledged.map { it.latencyMs }.distinct()).containsExactly(40L)
    }

    @Test
    fun `semi-sync with slow followers times out once and then quietly runs asynchronously`() {
        val (sim, cluster) = cluster(Mode.SemiSync(timeoutMs = 500), mapOf("f1" to 600L, "f2" to 700L))
        sim.runUntil(1_000)
        assertThat(cluster.semiSyncOn).isFalse()
        val first = cluster.acknowledged.first()
        assertThat(first.entry.position).isEqualTo(1)
        assertThat(first.latencyMs).isEqualTo(500L)               // the first payment waited the full timeout
        val afterSwitch = cluster.acknowledged.filter { it.sentAt > 500 }
        assertThat(afterSwitch).isNotEmpty
        assertThat(afterSwitch.map { it.latencyMs }.distinct()).containsExactly(0L)   // no waiting, no copy
    }

    @Test
    fun `semi-sync comes back on once a follower catches up`() {
        val (sim, cluster) = cluster(Mode.SemiSync(timeoutMs = 100))
        sim.at(200) { cluster.cut += setOf("f1", "f2") }
        sim.at(400) { cluster.cut -= setOf("f1", "f2") }
        sim.runUntil(350)
        assertThat(cluster.semiSyncOn).isFalse()
        sim.runUntil(2_000)
        assertThat(cluster.semiSyncOn).isTrue()
        assertThat(cluster.acknowledged.size).isEqualTo(250)
        assertThat(cluster.acknowledged.last().latencyMs).isEqualTo(40L)
    }
}
