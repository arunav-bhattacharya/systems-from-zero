package sfz.repl.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** Exercise 3, [pin]: statement-based replication with the leader's values written into each statement. */
class PinTest {
    @Test
    fun `pin replaces now() and random() with the leader's values`() {
        var t = 5_000L
        val leader = Leader({ t }, seed = 1)
        val pinned = pin(Statement.Insert("m1", 1_250), leader) as Statement.Insert
        assertThat(pinned.createdAt).isEqualTo(Ts.At(5_000))
        assertThat(pinned.ref).isInstanceOf(Ref.Fixed::class.java)
        assertThat(pinned.sql).doesNotContain("now()").doesNotContain("random()")
    }

    @Test
    fun `pin leaves fixed values and other statements alone`() {
        val leader = Leader({ 0 }, seed = 1)
        val fixed = Statement.Insert("m1", 1_250, Ref.Fixed("a1"), Ts.At(7))
        assertThat(pin(fixed, leader)).isEqualTo(fixed)
        assertThat(pin(Statement.AddFee("m1", 30), leader)).isEqualTo(Statement.AddFee("m1", 30))
        assertThat(pin(Statement.DeleteSome(null, 2), leader)).isEqualTo(Statement.DeleteSome(null, 2))
    }

    @Test
    fun `with pinned values a statement replica matches the leader on now() and random()`() {
        val p = TwoServers(lagMs = 350)
        p.leader.pinValues = true
        p.sixPayments()
        p.run(Statement.AddFee("m2", 45))
        p.follower.replayStatements(p.leader.statementLog)
        assertThat(p.follower.rows).isEqualTo(p.leader.rows)
    }

    @Test
    fun `pinned values do not fix a LIMIT without ORDER BY or ids taken out of commit order`() {
        val p = TwoServers()
        p.leader.pinValues = true
        p.sixPayments()
        p.run(Statement.AddFee("m1", 30))
        p.follower.loadDump(p.leader.rows.values)
        val from = p.leader.statementLog.size
        p.run(Statement.DeleteSome(null, 2))
        p.leader.runInterleaved(Statement.Insert("m1", 100), Statement.Insert("m2", 200))
        p.follower.replayStatements(p.leader.statementLog.drop(from))

        assertThat(p.follower.rows).isNotEqualTo(p.leader.rows)
        assertThat(p.follower.rows.keys).contains(4L).doesNotContain(1L)   // the leader deleted 2 and 4; the follower 1 and 2
        assertThat(p.follower.rows.getValue(7).amountCents).isEqualTo(200)  // the leader gave id 7 to the 100
    }
}
