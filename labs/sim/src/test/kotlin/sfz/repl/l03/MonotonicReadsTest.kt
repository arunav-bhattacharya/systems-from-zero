package sfz.repl.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * Exercise 2, [monotonicReads]. Payment pay-9 is authorized at 0 ms and captured at 1,000 ms. Two
 * followers: r1 is 20 ms behind, r2 is 900 ms behind. The operator reloads the payment page every
 * 50 ms from 1,100 ms, and the load balancer alternates r1, r2, r1, r2...
 */
class MonotonicReadsTest {
    private val leader = Leader()
    private val r1 = Replica("r1", lagMs = 20, leader = leader)
    private val r2 = Replica("r2", lagMs = 900, leader = leader)
    private val replicas = listOf(r1, r2)
    private val client = Client(leader)
    private val writer = Session("payments-service")

    init {
        client.write(writer, 0, "pay-9", "authorized")
        client.write(writer, 1_000, "pay-9", "captured")
    }

    /** Ten reloads; returns what the operator saw each time. */
    private fun reloads(session: Session, route: (Int, Long) -> Route): List<Read> =
        (0 until 10).map { i ->
            val now = 1_100L + 50 * i
            client.read(session, now, "pay-9", route(i, now))
        }

    private fun backwards(reads: List<Read>) = reads.zipWithNext().count { (a, b) -> b.position < a.position }

    @Test
    fun `round-robin reads show the capture and then take it back`() {
        val reads = reloads(Session("ops")) { i, _ -> Route(replicas[i % 2]) }
        assertThat(reads.map { it.value }.take(4)).containsExactly("captured", "authorized", "captured", "authorized")
        assertThat(backwards(reads)).isEqualTo(5)
    }

    @Test
    fun `with the token a read is never served below the highest position the session has seen`() {
        val ops = Session("ops")
        val reads = reloads(ops) { _, now -> monotonicReads(ops, replicas, leader, now) }
        assertThat(backwards(reads)).isEqualTo(0)
        assertThat(reads.map { it.value }.distinct()).containsExactly("captured")
    }

    @Test
    fun `the session's sticky follower is tried first`() {
        val ops = Session("ops")
        val sticky = stickyReplica("ops", replicas)!!
        assertThat(monotonicReads(ops, replicas, leader, now = 1_100)).isEqualTo(Route(sticky))
    }

    @Test
    fun `a follower below the token is skipped, and the leader serves when every follower is behind`() {
        val ops = Session("ops").apply { lastSeen = 2 }
        assertThat(monotonicReads(ops, replicas, leader, now = 1_100)).isEqualTo(Route(r1))
        r1.alive = false
        assertThat(monotonicReads(ops, replicas, leader, now = 1_100)).isEqualTo(Route(leader))
    }

    @Test
    fun `the token also covers the session's own writes`() {
        assertThat(writer.lastWritten).isEqualTo(2)
        r1.pause(now = 500)
        assertThat(monotonicReads(writer, replicas, leader, now = 1_100)).isEqualTo(Route(leader))
    }

    @Test
    fun `sticky routing alone holds until the sticky follower dies, then the reroute goes back in time`() {
        // given behaviour, no exercise: why the token is still needed with sticky routing
        val users = (1..200).map { "user-$it" }
        val onR1 = users.first { stickyReplica(it, replicas) === r1 }
        val ops = Session(onR1)
        val before = client.read(ops, 1_100, "pay-9", Route(stickyReplica(onR1, replicas)!!))
        r1.alive = false
        val after = client.read(ops, 1_150, "pay-9", Route(stickyReplica(onR1, replicas)!!))
        assertThat(before.value).isEqualTo("captured")
        assertThat(after.node).isEqualTo("r2")
        assertThat(after.value).isEqualTo("authorized")
    }
}
