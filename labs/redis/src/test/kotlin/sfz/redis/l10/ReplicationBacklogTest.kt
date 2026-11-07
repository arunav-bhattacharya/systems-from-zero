package sfz.redis.l10

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

// a model: no Docker needed
class ReplicationBacklogTest {

    /** One command as RESP, the way the primary writes it into the replication stream. */
    private fun resp(vararg args: String): String =
        "*${args.size}\r\n" + args.joinToString("") { "\$${it.length}\r\n$it\r\n" }

    private val setP1 = resp("SET", "payment:1", "approved")          // 42 bytes
    private val setP2 = resp("SET", "payment:2", "declined")          // 42 bytes
    private val incr = resp("INCR", "auths:card:7")                   // 33 bytes

    @Test
    fun `every byte of every command counts into the offset`() {
        val primary = ReplicationBacklog("8f1c", capacity = 1_000)

        primary.feed(setP1)
        primary.feed(incr)

        assertThat(setP1.length).isEqualTo(42)
        assertThat(primary.offset).isEqualTo(75)
        assertThat(primary.backlogLength).isEqualTo(75)
    }

    @Test
    fun `the backlog keeps only the newest bytes, while the offset keeps counting`() {
        val primary = ReplicationBacklog("8f1c", capacity = 64)

        repeat(10) { primary.feed(incr) }

        assertThat(primary.offset).isEqualTo(330)
        assertThat(primary.backlogLength).isEqualTo(64)
    }

    @Test
    fun `a replica that is up to date continues with nothing to send`() {
        val primary = ReplicationBacklog("8f1c", capacity = 1_000)
        primary.feed(setP1)

        assertThat(primary.psync("8f1c", 42)).isEqualTo(PsyncReply.Continue(""))
    }

    @Test
    fun `a replica that fell behind gets exactly the bytes it missed`() {
        val primary = ReplicationBacklog("8f1c", capacity = 1_000)
        primary.feed(setP1)                                            // the replica applied this, then lost its link
        primary.feed(setP2)
        primary.feed(incr)

        assertThat(primary.psync("8f1c", 42)).isEqualTo(PsyncReply.Continue(setP2 + incr))
    }

    @Test
    fun `once the missing bytes have left the backlog only a full resync will do`() {
        val primary = ReplicationBacklog("8f1c", capacity = 64)
        primary.feed(setP1)
        repeat(5) { primary.feed(incr) }                               // 165 more bytes: the backlog has moved on

        assertThat(primary.psync("8f1c", 42)).isEqualTo(PsyncReply.FullResync("8f1c", 207))
    }

    @Test
    fun `the oldest byte still in the backlog is just enough`() {
        val primary = ReplicationBacklog("8f1c", capacity = 64)
        repeat(6) { primary.feed(incr) }                               // offset 198; the backlog holds bytes 135..198

        val justInside = primary.psync("8f1c", 134)
        val justOutside = primary.psync("8f1c", 133)

        assertThat(justInside).isInstanceOf(PsyncReply.Continue::class.java)
        assertThat((justInside as PsyncReply.Continue).missing).hasSize(64)
        assertThat(justOutside).isEqualTo(PsyncReply.FullResync("8f1c", 198))
    }

    @Test
    fun `a different replication id is a different history`() {
        val primary = ReplicationBacklog("8f1c", capacity = 1_000)
        primary.feed(setP1)

        assertThat(primary.psync("77aa", 42)).isEqualTo(PsyncReply.FullResync("8f1c", 42))
        assertThat(primary.psync("?", -1)).isEqualTo(PsyncReply.FullResync("8f1c", 42))   // a brand-new replica
    }

    @Test
    fun `a replica that claims more than the primary ever wrote needs a full resync`() {
        val primary = ReplicationBacklog("8f1c", capacity = 1_000)
        primary.feed(setP1)

        assertThat(primary.psync("8f1c", 500)).isEqualTo(PsyncReply.FullResync("8f1c", 42))
    }

    @Test
    fun `after a promotion the old primary's replicas still continue from the backlog`() {
        // this stream belongs to a replica that was fully in sync with the old primary 8f1c
        val server = ReplicationBacklog("8f1c", capacity = 1_000)
        server.feed(setP1)
        server.feed(setP2)                                             // offset 84 when the old primary died

        server.promote("c0de")                                         // Sentinel made this replica the primary
        server.feed(incr)                                              // the first write of the new history

        assertThat(server.replId).isEqualTo("c0de")
        assertThat(server.replId2).isEqualTo("8f1c")
        assertThat(server.secondOffset).isEqualTo(84)
        // another replica of the old primary, a little behind, asks with the OLD id
        assertThat(server.psync("8f1c", 42)).isEqualTo(PsyncReply.Continue(setP2 + incr))
        // one that saw bytes the old primary wrote after the switch has a history we never had
        assertThat(server.psync("8f1c", 90)).isEqualTo(PsyncReply.FullResync("c0de", 117))
        // and replicas of the new history continue as usual
        assertThat(server.psync("c0de", 117)).isEqualTo(PsyncReply.Continue(""))
    }
}
