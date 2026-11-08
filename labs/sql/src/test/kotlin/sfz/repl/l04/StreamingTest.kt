package sfz.repl.l04

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test

/**
 * Lesson repl-04, exercises 1 to 3, in src/main/kotlin/sfz/repl/l04/Streaming.kt: replay, what a
 * commit waits for, and what a checkpoint may remove. A model, so no Docker: they run in a second.
 */
class StreamingTest {

    /** A primary with the seed's six refunds, and a cluster with one standby per name, cloned from it. */
    private fun cluster(vararg names: String): Cluster {
        val primary = Primary()
        primary.commit(1_000, *(1..6).map { "refund:$it" to "${it * 500}" }.toTypedArray())
        return Cluster(primary, *names)
    }

    // ------------------------------------------------------------------ exercise 1: replay

    @Test
    fun `a standby replays the WAL it has flushed, in order, and then matches the primary`() {
        val c = cluster("standby1")
        val s = c.standby("standby1")
        val r1 = c.primary.commit(1_010, "refund:7" to "900")
        c.primary.commit(1_011, "refund:7" to "950", "refund:8" to "120")
        c.stream(s, replay = false)
        assertThat(s.data).describedAs("received and flushed, not replayed yet").doesNotContainKey("refund:7")
        assertThat(s.flushLsn).isEqualTo(c.primary.currentLsn)

        s.replay()
        assertThat(s.data).isEqualTo(c.primary.data)
        assertThat(s.data["refund:7"]).describedAs("the later record wins: order matters").isEqualTo("950")
        assertThat(s.replayLsn).isEqualTo(c.primary.currentLsn).isGreaterThan(r1.end)
    }

    @Test
    fun `replay applies whole records only, and stops before one that upTo cuts`() {
        val c = cluster("standby1")
        val s = c.standby("standby1")
        val r1 = c.primary.commit(1_010, "refund:7" to "900")
        val r2 = c.primary.commit(1_011, "refund:8" to "120")
        c.stream(s, replay = false)

        s.replay(upTo = r2.end - 1)                              // inside r2
        assertThat(s.replayLsn).isEqualTo(r1.end)
        assertThat(s.data).containsEntry("refund:7", "900").doesNotContainKey("refund:8")

        s.replay(upTo = r2.end)
        assertThat(s.replayLsn).isEqualTo(r2.end)
        assertThat(s.data).containsEntry("refund:8", "120")
    }

    @Test
    fun `replay never runs ahead of the flush`() {
        val c = cluster("standby1")
        val s = c.standby("standby1")
        c.primary.commit(1_010, "refund:7" to "900")
        c.stream(s, flush = false, replay = false)               // written to the OS, not fsynced
        assertThat(s.writeLsn).isEqualTo(c.primary.currentLsn)
        assertThat(c.lag(s)).describedAs("write, flush and replay lag in bytes")
            .isEqualTo(Triple(0L, c.primary.currentLsn - s.flushLsn, c.primary.currentLsn - s.replayLsn))

        s.replay(upTo = Long.MAX_VALUE)
        assertThat(s.data).doesNotContainKey("refund:7")
        assertThat(s.replayLsn).isEqualTo(s.flushLsn)
    }

    @Test
    fun `a delete replays as a delete`() {
        val c = cluster("standby1")
        val s = c.standby("standby1")
        c.primary.commit(1_010, "refund:2" to null, "refund:3" to null)
        c.stream(s)
        assertThat(s.data.keys).containsExactly("refund:1", "refund:4", "refund:5", "refund:6")
    }

    // ------------------------------------------------------------------ exercise 2: isAcknowledged

    @Test
    fun `asynchronous replication answers at once, even with the standby down`() {
        val c = cluster("standby1")
        c.standby("standby1").running = false
        val r = c.primary.commit(1_010, "refund:7" to "900")
        assertThat(c.isAcknowledged(r)).isTrue()
    }

    @Test
    fun `a synchronous commit waits for the standby's flush, for as long as the standby is down`() {
        val c = cluster("standby1")
        c.synchronousStandbyNames = listOf("standby1")
        val s = c.standby("standby1")
        s.running = false
        val r = c.primary.commit(1_010, "refund:7" to "900")
        c.streamAll()
        assertThat(c.isAcknowledged(r)).describedAs("the COMMIT is still waiting").isFalse()
        assertThat(c.primary.data).describedAs("yet the primary has it: it committed locally").containsKey("refund:7")

        s.running = true
        c.stream(s, flush = false)
        assertThat(c.isAcknowledged(r)).describedAs("written but not flushed on the standby").isFalse()
        c.stream(s)
        assertThat(c.isAcknowledged(r)).isTrue()
    }

    @Test
    fun `each synchronous_commit level waits for a later stage`() {
        val c = cluster("standby1")
        c.synchronousStandbyNames = listOf("standby1")
        val s = c.standby("standby1")
        val r = c.primary.commit(1_010, "refund:7" to "900")
        c.stream(s, flush = false, replay = false)
        val afterWrite = SyncCommit.entries.associateWith { c.synchronousCommit = it; c.isAcknowledged(r) }
        assertThat(afterWrite).isEqualTo(
            mapOf(SyncCommit.OFF to true, SyncCommit.LOCAL to true, SyncCommit.REMOTE_WRITE to true, SyncCommit.ON to false, SyncCommit.REMOTE_APPLY to false),
        )
        c.stream(s, replay = false)
        c.synchronousCommit = SyncCommit.ON
        assertThat(c.isAcknowledged(r)).isTrue()
        c.synchronousCommit = SyncCommit.REMOTE_APPLY
        assertThat(c.isAcknowledged(r)).describedAs("flushed, not replayed: a read on the standby would not see it yet").isFalse()
        s.replay()
        assertThat(c.isAcknowledged(r)).isTrue()
    }

    @Test
    fun `SET LOCAL synchronous_commit = local skips the wait for one transaction`() {
        val c = cluster("standby1")
        c.synchronousStandbyNames = listOf("standby1")
        c.standby("standby1").running = false
        val r = c.primary.commit(1_010, "audit:1" to "page viewed")
        c.synchronousCommit = SyncCommit.LOCAL
        assertThat(c.isAcknowledged(r)).isTrue()
    }

    @Test
    fun `with ANY 1 of two standbys, one is enough`() {
        val c = cluster("standby1", "standby2")
        c.synchronousStandbyNames = listOf("standby1", "standby2")
        c.standby("standby1").running = false
        val r = c.primary.commit(1_010, "refund:7" to "900")
        c.streamAll()
        assertThat(c.isAcknowledged(r)).isTrue()
        c.standby("standby2").running = false
        val r2 = c.primary.commit(1_011, "refund:8" to "120")
        c.streamAll()
        assertThat(c.isAcknowledged(r2)).describedAs("both down: commits wait").isFalse()
    }

    // ------------------------------------------------------------------ exercise 3: checkpoint

    @Test
    fun `once every standby has the WAL, a checkpoint removes it`() {
        val c = cluster("standby1")
        repeat(20) { c.primary.commit(1_010L + it, "refund:${7 + it}" to "100") }
        c.streamAll()
        val before = c.primary.walOnDisk()
        assertThat(c.primary.checkpoint()).isEqualTo(before)
        assertThat(c.primary.walOnDisk()).isZero()
    }

    @Test
    fun `a stopped standby's slot keeps every record since it stopped`() {
        val c = cluster("standby1")
        val s = c.standby("standby1")
        c.streamAll()
        c.primary.checkpoint()
        s.running = false
        val written = (1..500).sumOf { c.primary.commit(2_000L + it, "login:$it" to "ok").size.toLong() }

        assertThat(c.primary.checkpoint()).describedAs("the slot needs all of it").isZero()
        assertThat(c.primary.walOnDisk()).isEqualTo(written)
        assertThat(c.primary.slots.getValue("standby1").restartLsn).isEqualTo(s.flushLsn)

        s.running = true
        c.stream(s)                                              // it catches up from its slot
        assertThat(s.data).isEqualTo(c.primary.data)
        assertThat(c.primary.checkpoint()).isEqualTo(written)
    }

    @Test
    fun `without a slot, a standby that was down past a checkpoint must be rebuilt`() {
        val primary = Primary()
        primary.commit(1_000, "refund:1" to "500")
        val s = Standby("standby1", primary.baseBackup(), slot = null)
        val c = Cluster(primary, listOf(s))
        s.running = false
        primary.commit(1_010, "refund:2" to "600")
        assertThat(primary.checkpoint()).describedAs("no slot holds anything back").isGreaterThan(0)
        s.running = true
        assertThatThrownBy { c.stream(s) }.isInstanceOf(WalRemovedException::class.java)
    }

    @Test
    fun `max_slot_wal_keep_size gives up on a slot that falls too far behind`() {
        val c = cluster("standby1", "standby2")
        c.primary.maxSlotWalKeepSize = 4_000
        c.streamAll()
        c.standby("standby1").running = false
        repeat(60) { c.primary.commit(3_000L + it, "login:$it" to "ok") }   // about 5 kB of WAL
        c.stream(c.standby("standby2"))
        c.primary.checkpoint()

        assertThat(c.primary.slots.getValue("standby1").lost).describedAs("wal_status = 'lost'").isTrue()
        assertThat(c.primary.slots.getValue("standby2").lost).isFalse()
        assertThat(c.primary.walOnDisk()).describedAs("pg_wal no longer grows for the lost slot").isZero()
        c.standby("standby1").running = true
        assertThatThrownBy { c.stream(c.standby("standby1")) }.isInstanceOf(WalRemovedException::class.java)
    }

    @Test
    fun `a slot within max_slot_wal_keep_size keeps its WAL`() {
        val c = cluster("standby1")
        c.primary.maxSlotWalKeepSize = 1_000_000
        c.standby("standby1").running = false
        val written = (1..60).sumOf { c.primary.commit(3_000L + it, "login:$it" to "ok").size.toLong() }
        c.primary.checkpoint()
        assertThat(c.primary.slots.getValue("standby1").lost).isFalse()
        assertThat(c.primary.walOnDisk()).isEqualTo(written)
    }
}
