package sfz.sql.l16

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test

/**
 * Lesson sql-16, exercises 4 and 5, in src/main/kotlin/sfz/sql/l16/Failover.kt: promoting the
 * right standby and counting what a failover lost, and point-in-time recovery from a base backup
 * and the WAL archive. Exercise 1 (replay) must work for the failover tests.
 */
class FailoverTest {

    private fun cluster(vararg names: String): Cluster {
        val primary = Primary()
        primary.commit(1_000, *(1..6).map { "refund:$it" to "${it * 500}" }.toTypedArray())
        return Cluster(primary, *names)
    }

    // ------------------------------------------------------------------ exercise 4: failover

    @Test
    fun `failover promotes the running standby with the most WAL`() {
        val c = cluster("standby1", "standby2", "standby3")
        c.primary.commit(1_010, "refund:7" to "900")
        c.streamAll()
        c.primary.commit(1_011, "refund:8" to "120")
        c.stream(c.standby("standby1"))                          // standby1 has everything...
        c.stream(c.standby("standby2"))
        c.stream(c.standby("standby3"), flush = false)           // received refund:8, not yet on its disk
        c.standby("standby1").running = false                    // ...but it went down with the primary

        val result = Failover.failover(c.standbys, c.primary.currentLsn, acknowledged = emptyList())
        assertThat(result.promoted.name).describedAs("standby1 is down; standby2 flushed more than standby3").isEqualTo("standby2")
    }

    @Test
    fun `on a tie the first standby in the list wins`() {
        val c = cluster("standby1", "standby2")
        c.primary.commit(1_010, "refund:7" to "900")
        c.streamAll()
        assertThat(Failover.failover(c.standbys, c.primary.currentLsn, emptyList()).promoted.name).isEqualTo("standby1")
    }

    @Test
    fun `an asynchronous failover loses the commits the standby never received`() {
        val c = cluster("standby1")
        val acknowledged = mutableListOf<WalRecord>()
        fun commit(at: Long, vararg w: Pair<String, String?>) = c.primary.commit(at, *w).also { if (c.isAcknowledged(it)) acknowledged += it }

        commit(1_010, "refund:7" to "900")
        c.streamAll()
        c.standby("standby1").running = false                    // lagging, cut off: the same thing
        val r8 = commit(1_011, "refund:8" to "1111")
        val r9 = commit(1_012, "refund:9" to "2222")
        assertThat(acknowledged).describedAs("asynchronous: every client was told 'committed'").hasSize(3)

        c.standby("standby1").running = true                    // the primary is gone; only the standby is left
        val result = Failover.failover(c.standbys, c.primary.currentLsn, acknowledged)
        assertThat(result.lost).containsExactly(r8, r9)
        assertThat(result.promoted.data).containsEntry("refund:7", "900").doesNotContainKeys("refund:8", "refund:9")
    }

    @Test
    fun `with synchronous replication no acknowledged commit is lost`() {
        val c = cluster("standby1")
        c.synchronousStandbyNames = listOf("standby1")
        val acknowledged = mutableListOf<WalRecord>()
        val r7 = c.primary.commit(1_010, "refund:7" to "900")
        c.streamAll()
        if (c.isAcknowledged(r7)) acknowledged += r7
        c.standby("standby1").running = false
        val r8 = c.primary.commit(1_011, "refund:8" to "1111")
        c.streamAll()
        if (c.isAcknowledged(r8)) acknowledged += r8             // never: the client is still waiting

        c.standby("standby1").running = true
        val result = Failover.failover(c.standbys, c.primary.currentLsn, acknowledged)
        assertThat(acknowledged).containsExactly(r7)
        assertThat(result.lost).isEmpty()
    }

    @Test
    fun `promotion replays what the standby flushed but had not replayed`() {
        val c = cluster("standby1")
        c.primary.commit(1_010, "refund:7" to "900")
        c.stream(c.standby("standby1"), replay = false)
        val result = Failover.failover(c.standbys, c.primary.currentLsn, emptyList())
        assertThat(result.promoted.data).isEqualTo(c.primary.data)
        assertThat(result.promoted.replayLsn).isEqualTo(c.primary.currentLsn)
    }

    @Test
    fun `maximum_lag_on_failover refuses a standby that is too far behind`() {
        val c = cluster("standby1")
        c.standby("standby1").running = false
        repeat(30) { c.primary.commit(2_000L + it, "login:$it" to "ok") }
        c.standby("standby1").running = true
        val behind = c.primary.currentLsn - c.standby("standby1").flushLsn
        assertThatThrownBy { Failover.failover(c.standbys, c.primary.currentLsn, emptyList(), maximumLagOnFailover = behind - 1) }
            .isInstanceOf(IllegalStateException::class.java)
        assertThat(Failover.failover(c.standbys, c.primary.currentLsn, emptyList(), maximumLagOnFailover = behind).promoted.name)
            .isEqualTo("standby1")
    }

    @Test
    fun `with no running standby there is nothing to promote`() {
        val c = cluster("standby1")
        c.standby("standby1").running = false
        assertThatThrownBy { Failover.failover(c.standbys, c.primary.currentLsn, emptyList()) }.isInstanceOf(IllegalStateException::class.java)
    }

    // ------------------------------------------------------------------ exercise 5: point-in-time recovery

    /** Fee schedules for four merchants, a base backup, then a day of changes and a bad DELETE. */
    private class Story {
        val primary = Primary()
        init {
            primary.commit(100, *(1..4).map { "fee:$it" to "290" }.toTypedArray())
        }
        val backup = primary.baseBackup()                        // the nightly pg_basebackup
        val r1 = primary.commit(200, "fee:5" to "250")           // a new merchant
        val r2 = primary.commit(300, "fee:2" to "310")           // a price change
        val mistake = primary.commit(400, *(1..5).map { "fee:$it" to null }.toTypedArray())   // DELETE without WHERE
        val r4 = primary.commit(500, "fee:9" to "199")           // the next commit, after the mistake
    }

    @Test
    fun `recovery to a moment before the mistake keeps everything up to it`() {
        val s = Story()
        val got = Pitr.recover(s.backup, s.primary.archive, targetTime = 399)
        assertThat(got.data).isEqualTo(mapOf("fee:1" to "290", "fee:2" to "310", "fee:3" to "290", "fee:4" to "290", "fee:5" to "250"))
        assertThat(got.stoppedAt).describedAs("just before the DELETE's commit").isEqualTo(s.r2.end)
        assertThat(s.primary.data).describedAs("the primary itself still has the damage").doesNotContainKey("fee:1")
    }

    @Test
    fun `a commit at exactly the target time is replayed when inclusive, and not when exclusive`() {
        val s = Story()
        assertThat(Pitr.recover(s.backup, s.primary.archive, targetTime = 300).data).containsEntry("fee:2", "310")
        assertThat(Pitr.recover(s.backup, s.primary.archive, targetTime = 300, inclusive = false).data).containsEntry("fee:2", "290")
        assertThat(Pitr.recover(s.backup, s.primary.archive, targetTime = 400, inclusive = false).stoppedAt).isEqualTo(s.r2.end)
    }

    @Test
    fun `a target before the first commit after the backup gives the backup itself`() {
        val s = Story()
        val got = Pitr.recover(s.backup, s.primary.archive, targetTime = 150)
        assertThat(got.data).isEqualTo(s.backup.data)
        assertThat(got.stoppedAt).isEqualTo(s.backup.lsn)
    }

    @Test
    fun `records already inside the base backup are skipped, not replayed twice`() {
        val primary = Primary()
        primary.commit(100, "fee:1" to "290")
        primary.commit(110, "fee:1" to "300")
        val backup = primary.baseBackup()
        primary.commit(120, "fee:2" to "250")
        primary.commit(130, "fee:3" to "199")
        val got = Pitr.recover(backup, primary.archive, targetTime = 125)
        assertThat(got.data).isEqualTo(mapOf("fee:1" to "300", "fee:2" to "250"))
    }

    @Test
    fun `a hole in the archive stops recovery with an error`() {
        val s = Story()
        val withHole = s.primary.archive.filterNot { it == s.r1 }   // archive_command failed for one segment
        assertThatThrownBy { Pitr.recover(s.backup, withHole, targetTime = 399) }
            .isInstanceOf(IllegalStateException::class.java)
            .hasMessageContaining("recovery ended before configured recovery target was reached")
    }

    @Test
    fun `a target after the last archived commit is an error, not a silent stop`() {
        val s = Story()
        assertThatThrownBy { Pitr.recover(s.backup, s.primary.archive, targetTime = 10_000) }
            .isInstanceOf(IllegalStateException::class.java)
            .hasMessageContaining("recovery ended before configured recovery target was reached")
        assertThat(Pitr.recover(s.backup, s.primary.archive, targetTime = 450).stoppedAt).isEqualTo(s.mistake.end)
        assertThat(s.r4.committedAt).isEqualTo(500)
    }
}
