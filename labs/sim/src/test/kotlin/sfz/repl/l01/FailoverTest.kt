package sfz.repl.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * Exercise 3, [Cluster.failover], with exercise 2 deciding the acknowledgements: what a failover
 * loses under each mode, and the GitHub 2012 hazard of reused ids. A payment is written every
 * 4 ms from 0 to 996 ms, and the leader dies at 1,001 ms.
 */
class FailoverTest {
    private fun runToCrash(mode: Mode, delays: Map<String, Long> = mapOf("f1" to 20L, "f2" to 50L)): Cluster {
        val sim = Sim()
        val cluster = Cluster(sim, mode, delays)
        cluster.writeEvery(4, from = 0, until = 996)
        sim.at(1_001) { cluster.crash(cluster.leader) }
        sim.runUntil(1_001)
        return cluster
    }

    @Test
    fun `asynchronous failover loses the acknowledged writes the best follower had not received`() {
        val cluster = runToCrash(Mode.Async)
        val result = cluster.failover()

        assertThat(result.newLeader.name).isEqualTo("f1")
        assertThat(result.newLeader.position).isEqualTo(246)      // payments written up to 980 ms reached it
        assertThat(result.lost.map { it.entry.payment }).containsExactly("pay-247", "pay-248", "pay-249", "pay-250")
        assertThat(cluster.leader).isSameAs(result.newLeader)
    }

    @Test
    fun `the new leader is the most up-to-date follower, whatever its place in the list`() {
        val cluster = runToCrash(Mode.Async, mapOf("f1" to 50L, "f2" to 20L))
        val result = cluster.failover()
        assertThat(result.newLeader.name).isEqualTo("f2")
        assertThat(result.lost).hasSize(4)
    }

    @Test
    fun `synchronous failover to the follower that confirmed loses nothing`() {
        val cluster = runToCrash(Mode.Sync(1))
        val result = cluster.failover()
        assertThat(result.lost).isEmpty()
        // payments written after 960 ms were on f1 or in flight, but no client had heard "OK" for them
        assertThat(cluster.acknowledged.size).isEqualTo(241)
    }

    @Test
    fun `semi-sync that fell back to asynchronous loses writes it acknowledged`() {
        val cluster = runToCrash(Mode.SemiSync(timeoutMs = 500), mapOf("f1" to 600L, "f2" to 700L))
        val result = cluster.failover()

        assertThat(cluster.semiSyncOn).isTrue()                   // reset by the promotion
        assertThat(result.newLeader.position).isEqualTo(101)      // only payments written up to 400 ms arrived
        assertThat(result.lost.size).isEqualTo(149)
        assertThat(cluster.acknowledged.size).isEqualTo(250)
    }

    @Test
    fun `after an asynchronous failover the new leader hands out the lost payments' ids again`() {
        val sim = Sim()
        val cluster = Cluster(sim, Mode.Async, mapOf("f1" to 20L, "f2" to 50L))
        // a cache outside the database, filled with id -> payment once the client hears OK (Redis, in GitHub's case)
        val cache = mutableMapOf<Long, String>()
        cluster.writeEvery(4, from = 0, until = 996)
        sim.at(1_001) { cluster.crash(cluster.leader) }
        sim.runUntil(1_001)
        cluster.acknowledged.forEach { cache[it.entry.id] = it.entry.payment }

        val result = cluster.failover()
        val acksBefore = cluster.acknowledged.size
        for (n in 1..4) sim.at(1_100L + n) { cluster.write("after-failover-$n") }
        sim.runUntil(1_200)
        val newAcks = cluster.acknowledged.drop(acksBefore)

        assertThat(result.newLeader.nextId).isEqualTo(251)
        assertThat(newAcks.map { it.entry.id }).containsExactly(247L, 248L, 249L, 250L)
        val wrongOwner = newAcks.filter { cache[it.entry.id] != null && cache[it.entry.id] != it.entry.payment }
        assertThat(wrongOwner).hasSize(4)                         // the cache says id 247 is pay-247; the database says otherwise
    }

    @Test
    fun `writes go on at the new leader and reach the other follower`() {
        val cluster = runToCrash(Mode.Async)
        val result = cluster.failover()
        val sim = cluster.sim
        for (n in 1..10) sim.at(1_100L + 4 * n) { cluster.write("after-$n") }
        sim.runUntil(1_400)

        val f2 = cluster.node("f2")
        assertThat(result.newLeader.position).isEqualTo(256)
        assertThat(f2.position).isEqualTo(256)
        assertThat(f2.rows).isEqualTo(result.newLeader.rows)
    }
}
