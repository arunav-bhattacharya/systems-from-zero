package sfz.repl.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * Exercise 1, [readYourWrites]. A merchant requests a refund at 1,000 ms and the dashboard reloads
 * 10 ms later. The follower behind the load balancer is 300 ms behind the leader.
 */
class ReadYourWritesTest {
    private val leader = Leader()
    private val replica = Replica("r1", lagMs = 300, leader = leader)
    private val client = Client(leader)
    private val merchant = Session("merchant-17")

    private fun requestRefund() {
        client.write(Session("someone-else"), 900, "pay-8", "captured")
        client.write(merchant, 1_000, "refund-pay-41", "requested")
    }

    @Test
    fun `without a token the reload reads the follower and the refund is missing`() {
        requestRefund()
        val read = client.read(merchant, 1_010, "refund-pay-41", Route(replica))
        assertThat(read.node).isEqualTo("r1")
        assertThat(read.position).isEqualTo(0)
        assertThat(read.value).isNull()                            // the merchant clicks "refund" again
    }

    @Test
    fun `with the token the reload goes to the leader while the follower is behind`() {
        requestRefund()
        assertThat(merchant.lastWritten).isEqualTo(2)
        val route = readYourWrites(merchant, replica, leader, now = 1_010)
        assertThat(route).isEqualTo(Route(leader))
        assertThat(client.read(merchant, 1_010, "refund-pay-41", route).value).isEqualTo("requested")
    }

    @Test
    fun `once the follower has replayed the write the read stays on the follower`() {
        requestRefund()
        val route = readYourWrites(merchant, replica, leader, now = 1_300)
        assertThat(route).isEqualTo(Route(replica))
        assertThat(client.read(merchant, 1_300, "refund-pay-41", route).value).isEqualTo("requested")
    }

    @Test
    fun `with a wait budget the read waits on the follower just long enough`() {
        requestRefund()
        val route = readYourWrites(merchant, replica, leader, now = 1_010, maxWaitMs = 500)
        assertThat(route).isEqualTo(Route(replica, waitMs = 290))
        val read = client.read(merchant, 1_010, "refund-pay-41", route)
        assertThat(read.value).isEqualTo("requested")
        assertThat(read.waitMs).isEqualTo(290)
    }

    @Test
    fun `a wait budget shorter than the lag falls back to the leader`() {
        requestRefund()
        assertThat(readYourWrites(merchant, replica, leader, now = 1_010, maxWaitMs = 100)).isEqualTo(Route(leader))
    }

    @Test
    fun `a paused follower never catches up, however long the budget`() {
        requestRefund()
        replica.pause(now = 950)                                  // pg_wal_replay_pause() before the refund replayed
        assertThat(readYourWrites(merchant, replica, leader, now = 5_000, maxWaitMs = 60_000)).isEqualTo(Route(leader))
        replica.resume()
        assertThat(readYourWrites(merchant, replica, leader, now = 5_000)).isEqualTo(Route(replica))
    }

    @Test
    fun `the token covers only the session's own writes, so other readers stay on the follower`() {
        requestRefund()
        val support = Session("support-agent")
        assertThat(readYourWrites(support, replica, leader, now = 1_010)).isEqualTo(Route(replica))
    }

    @Test
    fun `a dead follower is never chosen`() {
        requestRefund()
        replica.alive = false
        assertThat(readYourWrites(merchant, replica, leader, now = 9_000, maxWaitMs = 1_000)).isEqualTo(Route(leader))
    }
}
