package sfz.repl.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * What goes wrong when a follower runs the leader's statements again. The leader writes its logs
 * with exercise 1's [rowEvents], so these need it too.
 */
class StatementReplayTest {
    @Test
    fun `now() on the follower is the follower's own clock`() {
        val p = TwoServers(lagMs = 350)
        p.run(Statement.Insert("m1", 1_250, ref = Ref.Fixed("a1")))
        p.follower.replayStatements(p.leader.statementLog)
        assertThat(p.follower.rows.getValue(1).createdAt - p.leader.rows.getValue(1).createdAt).isEqualTo(350)
    }

    @Test
    fun `random() on the follower draws a different reference`() {
        val p = TwoServers()
        p.run(Statement.Insert("m1", 1_250, createdAt = Ts.At(0)))
        p.follower.replayStatements(p.leader.statementLog)
        assertThat(p.follower.rows.getValue(1).ref).isNotEqualTo(p.leader.rows.getValue(1).ref)
    }

    @Test
    fun `replaying a relative update twice charges the fee twice`() {
        val p = TwoServers()
        p.run(Statement.Insert("m1", 1_250, Ref.Fixed("a1"), Ts.At(0)), Statement.AddFee("m1", 30))
        p.follower.replayStatements(p.leader.statementLog)
        p.follower.replayStatements(p.leader.statementLog.drop(1))     // a resend after a reconnect
        assertThat(p.leader.rows.getValue(1).feeCents).isEqualTo(30)
        assertThat(p.follower.rows.getValue(1).feeCents).isEqualTo(60)
    }

    @Test
    fun `a DELETE with LIMIT and no ORDER BY removes different rows when the heaps differ`() {
        val p = TwoServers()
        p.sixPayments()
        p.run(Statement.AddFee("m1", 30))                         // m1's rows get new versions at the heap's end
        assertThat(p.leader.rows.keys).containsExactly(2L, 4L, 6L, 1L, 3L, 5L)
        p.follower.loadDump(p.leader.rows.values)                 // the follower was built from a dump: id order
        val from = p.leader.statementLog.size

        p.run(Statement.DeleteSome(merchant = null, limit = 2))
        p.follower.replayStatements(p.leader.statementLog.drop(from))

        assertThat(p.leader.rows.keys).containsExactlyInAnyOrder(1L, 3L, 5L, 6L)
        assertThat(p.follower.rows.keys).containsExactlyInAnyOrder(3L, 4L, 5L, 6L)
    }

    @Test
    fun `two inserts that commit in the other order get swapped ids on the follower`() {
        val p = TwoServers()
        p.leader.runInterleaved(
            Statement.Insert("m1", 1_250, Ref.Fixed("auth-A"), Ts.At(0)),
            Statement.Insert("m2", 9_900, Ref.Fixed("auth-B"), Ts.At(0)),
        )
        p.follower.replayStatements(p.leader.statementLog)
        assertThat(p.leader.rows.getValue(1).ref).isEqualTo("auth-A")
        assertThat(p.follower.rows.getValue(1).ref).isEqualTo("auth-B")
    }
}
