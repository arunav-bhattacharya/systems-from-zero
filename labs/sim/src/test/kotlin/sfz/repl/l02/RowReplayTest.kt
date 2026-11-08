package sfz.repl.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** Exercise 2, [Server.applyRow]: a follower that applies row events ends up with the leader's table. */
class RowReplayTest {
    @Test
    fun `row events carry the leader's now() and random values`() {
        val p = TwoServers(lagMs = 350)
        p.sixPayments()
        p.follower.replayRows(p.leader.rowLog)
        assertThat(p.follower.rows).isEqualTo(p.leader.rows)
    }

    @Test
    fun `row events name the rows a LIMIT picked, whatever the follower's heap order`() {
        val p = TwoServers()
        p.sixPayments()
        p.run(Statement.AddFee("m1", 30))
        p.follower.loadDump(p.leader.rows.values)
        val from = p.leader.rowLog.size
        p.run(Statement.DeleteSome(merchant = null, limit = 2))
        p.follower.replayRows(p.leader.rowLog.drop(from))
        assertThat(p.follower.rows).isEqualTo(p.leader.rows)
    }

    @Test
    fun `row events carry the ids the leader handed out, whatever the commit order`() {
        val p = TwoServers()
        p.leader.runInterleaved(
            Statement.Insert("m1", 1_250, Ref.Fixed("auth-A"), Ts.At(0)),
            Statement.Insert("m2", 9_900, Ref.Fixed("auth-B"), Ts.At(0)),
        )
        p.follower.replayRows(p.leader.rowLog)
        assertThat(p.follower.rows).isEqualTo(p.leader.rows)
    }

    @Test
    fun `applying the same row events twice changes nothing`() {
        val p = TwoServers()
        p.sixPayments()
        p.run(Statement.AddFee("m1", 30), Statement.DeleteSome("m2", 1))
        p.follower.replayRows(p.leader.rowLog)
        p.follower.replayRows(p.leader.rowLog)                    // the whole log again
        p.follower.replayRows(p.leader.rowLog.takeLast(4))        // and its tail a third time
        assertThat(p.follower.rows).isEqualTo(p.leader.rows)
        assertThat(p.follower.rows.getValue(1).feeCents).isEqualTo(30)
    }

    @Test
    fun `a follower's id counter moves past every replicated id, so a promotion does not reuse one`() {
        val p = TwoServers()
        p.sixPayments()
        p.run(Statement.DeleteSome("m2", 3))                      // ids 2, 4 and 6 are gone
        p.follower.replayRows(p.leader.rowLog)
        assertThat(p.follower.nextId).isEqualTo(7)

        p.follower.execute(Statement.Insert("m3", 500, Ref.Fixed("after-promotion"), Ts.At(0)))
        assertThat(p.follower.rows.keys).contains(7L)
        assertThat(p.follower.rows.getValue(7).ref).isEqualTo("after-promotion")
    }

    @Test
    fun `deleting a row that is already gone is not an error`() {
        val follower = Server("f", { 0 }, seed = 3)
        follower.applyRow(RowEvent.Deleted(42))
        assertThat(follower.rows).isEmpty()
    }
}
