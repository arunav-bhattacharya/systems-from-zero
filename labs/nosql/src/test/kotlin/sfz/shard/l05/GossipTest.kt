package sfz.shard.l05

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import kotlin.math.ceil
import kotlin.math.log2

class GossipTest {
    private val gen = 1_794_100_000

    /** Two nodes that both know cass1, cass2 and cass3. */
    private fun pair(): Pair<GossipNode, GossipNode> {
        val a = GossipNode("cass1", gen)
        val b = GossipNode("cass2", gen)
        val c = GossipNode("cass3", gen)
        repeat(3) { a.beat(); b.beat(); c.beat() }
        a.set("STATUS", "NORMAL"); b.set("STATUS", "NORMAL"); c.set("STATUS", "NORMAL")
        for (n in listOf(a, b)) for (m in listOf(a, b, c)) if (n !== m) n.endpoints[m.name] = m.self
        return a to b
    }

    @Test
    fun `two nodes that agree exchange digests and nothing else`() {
        val (a, b) = pair()
        val ack = b.examine(a.digests())
        assertThat(ack.requests).isEmpty()
        assertThat(ack.states).isEmpty()
    }

    @Test
    fun `examine asks for what is newer at the sender and sends what is newer here`() {
        val (a, b) = pair()
        a.beat(); a.set("LOAD", "81967.0")     // a moved on: heartbeat 5, LOAD at 6
        b.beat()                               // b moved on too: heartbeat 5
        val ack = b.examine(a.digests())
        // b wants cass1's news, from the version it already has (4)
        assertThat(ack.requests).containsExactly(Digest("cass1", gen, 4))
        // and b has news about itself that a lacks: only the part newer than what a knows
        assertThat(ack.states.keys).containsExactly("cass2")
        assertThat(ack.states.getValue("cass2").heartbeat).isEqualTo(5)
        assertThat(ack.states.getValue("cass2").states).isEmpty() // STATUS (version 4) is old news for a
        // the Ack2 answers the request with only cass1's newer parts
        val ack2 = a.answer(ack.requests)
        assertThat(ack2.getValue("cass1").states.keys).containsExactly("LOAD")
    }

    @Test
    fun `examine requests everything about a node it has never heard of`() {
        val (a, b) = pair()
        val d = GossipNode("cass4", gen + 300)
        d.beat(); d.set("STATUS", "BOOT")
        a.endpoints["cass4"] = d.self
        val ack = b.examine(a.digests())
        assertThat(ack.requests).containsExactly(Digest("cass4", gen + 300, 0))
        assertThat(a.answer(ack.requests).getValue("cass4").states.getValue("STATUS").value).isEqualTo("BOOT")
    }

    @Test
    fun `apply keeps the newest version of each state and ignores older news`() {
        val (a, b) = pair()
        a.beat(); a.set("LOAD", "81967.0")
        b.apply(mapOf("cass1" to a.self))
        assertThat(b.endpoints.getValue("cass1").states.getValue("LOAD").value).isEqualTo("81967.0")
        // a stale copy of cass1's state (older versions) changes nothing
        val stale = EndpointState(gen, 2, mapOf("LOAD" to Versioned("1.0", 2), "STATUS" to Versioned("BOOT", 1)))
        b.apply(mapOf("cass1" to stale))
        assertThat(b.endpoints.getValue("cass1")).isEqualTo(a.self)
        // and nobody else's view of b replaces b's own
        b.apply(mapOf("cass2" to EndpointState(gen + 999, 1)))
        assertThat(b.self.generation).isEqualTo(gen)
    }

    @Test
    fun `apply reports whose heartbeat moved, for the failure detector`() {
        val (a, b) = pair()
        a.beat()
        assertThat(b.apply(mapOf("cass1" to a.self))).containsExactly("cass1")
        assertThat(b.apply(mapOf("cass1" to a.self))).isEmpty() // the same heartbeat again is no news
    }

    @Test
    fun `a higher generation wins even though its versions are smaller`() {
        val (a, b) = pair()
        repeat(40) { a.beat() } // cass1 has been up a while: heartbeat 44
        b.apply(mapOf("cass1" to a.self))
        // cass1 restarts: a new generation, and its version counter starts again from zero
        val restarted = GossipNode("cass1", gen + 60)
        restarted.beat(); restarted.set("STATUS", "NORMAL")
        assertThat(restarted.self.maxVersion).isLessThan(b.endpoints.getValue("cass1").maxVersion)
        // b's digest says "cass1 at the old generation"; the restarted node must win anyway
        val ack = restarted.examine(b.digests())
        assertThat(ack.states).containsKey("cass1")
        assertThat(b.apply(ack.states)).contains("cass1")
        assertThat(b.endpoints.getValue("cass1")).isEqualTo(restarted.self)
        // and old news about the previous life of cass1 is now ignored
        b.apply(mapOf("cass1" to a.self))
        assertThat(b.endpoints.getValue("cass1").generation).isEqualTo(gen + 60)
    }

    @Test
    fun `a new state reaches every node in about log2 N rounds`() {
        for (n in listOf(6, 32, 128)) {
            val worst = (1L..20L).maxOf { seed ->
                val cluster = GossipCluster.of(n, seed)
                repeat(3) { cluster.round() } // settle: everyone has beaten a few times
                val source = cluster.nodes.getValue("node-%02d".format(n))
                source.set("STATUS", "LEAVING")
                val version = source.self.maxVersion
                var rounds = 0
                while (!cluster.everyoneKnows(source.name, cluster.startedAt, version)) {
                    cluster.round(); rounds++
                    check(rounds < 50) { "no convergence after 50 rounds" }
                }
                rounds
            }
            // epidemic spread: the informed set roughly doubles (or better) every round
            assertThat(worst).`as`("worst of 20 runs, N = $n").isLessThanOrEqualTo(ceil(log2(n.toDouble())).toInt() + 2)
        }
    }

    @Test
    fun `a stopped node's heartbeat stops advancing everywhere`() {
        val cluster = GossipCluster.of(6, randomSeed = 7)
        repeat(5) { cluster.round() }
        cluster.stop("node-03")
        repeat(2) { cluster.round() } // let the last heartbeat it sent finish spreading
        val frozen = cluster.nodes.values.filter { cluster.isRunning(it.name) }.map { it.endpoints.getValue("node-03").heartbeat }.toSet()
        val othersBefore = cluster.nodes.getValue("node-01").endpoints.getValue("node-02").heartbeat
        repeat(10) { cluster.round() }
        for (n in cluster.nodes.values.filter { cluster.isRunning(it.name) }) {
            assertThat(n.endpoints.getValue("node-03").heartbeat).`as`(n.name).isIn(frozen)
        }
        assertThat(cluster.nodes.getValue("node-01").endpoints.getValue("node-02").heartbeat).isGreaterThan(othersBefore)
        // the observers stopped hearing it: their last-heard rounds for node-03 are all old
        assertThat(cluster.lastHeard.getValue("node-01")["node-03"] ?: 0).isLessThanOrEqualTo(cluster.round - 10)
    }

    @Test
    fun `a restarted node bumps its generation and the whole cluster takes its new state`() {
        val cluster = GossipCluster.of(6, randomSeed = 3)
        repeat(20) { cluster.round() }
        val oldHeartbeat = cluster.nodes.getValue("node-01").endpoints.getValue("node-04").heartbeat
        cluster.stop("node-04")
        repeat(3) { cluster.round() }
        cluster.restart("node-04", generation = cluster.startedAt + 120)
        repeat(8) { cluster.round() }
        for (n in cluster.nodes.values) {
            val seen = n.endpoints.getValue("node-04")
            assertThat(seen.generation).`as`(n.name).isEqualTo(cluster.startedAt + 120)
            assertThat(seen.heartbeat).`as`(n.name).isLessThan(oldHeartbeat) // versions started again from zero
        }
    }
}
