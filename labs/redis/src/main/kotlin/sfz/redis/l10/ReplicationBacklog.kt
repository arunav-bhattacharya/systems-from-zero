package sfz.redis.l10

/** What a primary answers when a replica connects and sends `PSYNC <replid> <offset>`. */
sealed interface PsyncReply {
    /** `+CONTINUE`: the backlog still holds every byte the replica is missing. [missing] is those bytes, in order. */
    data class Continue(val missing: String) : PsyncReply

    /**
     * `+FULLRESYNC <replId> <offset>`: the primary will send a whole snapshot taken at [offset], and the
     * stream from there on. The replica throws its data away and loads the snapshot.
     */
    data class FullResync(val replId: String, val offset: Long) : PsyncReply
}

/**
 * A model of a Redis primary's replication stream (lesson 10).
 *
 * Every write the primary runs is sent to its replicas as RESP bytes, one command after another: the
 * replication stream. [offset] counts every byte ever put into it (`master_repl_offset` in
 * `INFO replication`). A replica that has applied the first 1,000 bytes is at offset 1,000. The pair
 * ([replId], [offset]) names one exact version of the data.
 *
 * The primary also keeps the last [capacity] bytes of the stream in memory, the backlog
 * (`repl-backlog-size`, 1 MB by default). When a replica reconnects after a short break, the primary
 * sends it the bytes it missed from the backlog: a partial resync. When the missing bytes are no longer
 * there, or the replica followed a different history, it has to start from a full snapshot.
 *
 * One simplification: on the wire the replica sends the offset of the next byte it wants (its offset
 * plus 1). Here [psync] takes the replica's own offset, the number it shows in INFO as `slave_repl_offset`.
 * Every byte is one character: the stream in the tests is plain ASCII.
 */
class ReplicationBacklog(replId: String, val capacity: Int) {
    init {
        require(capacity > 0) { "the backlog needs room for at least one byte" }
    }

    /** The current history's ID (`master_replid`). A new one starts whenever a server becomes a primary. */
    var replId: String = replId
        private set

    /** Every byte ever put into the stream (`master_repl_offset`). */
    var offset: Long = 0
        private set

    /** The previous history's ID after a [promote] (`master_replid2`), or null. */
    var replId2: String? = null
        private set

    /**
     * The offset up to which [replId2] is still a valid name for this server's data, or -1. INFO shows it
     * plus one, as `second_repl_offset`: the first byte of the new history.
     */
    var secondOffset: Long = -1
        private set

    /** The last bytes of the stream, at most [capacity] of them. Its first char is the byte at offset [offset] - length + 1. */
    private val backlog = StringBuilder()

    /** How many bytes the backlog holds now (`repl_backlog_histlen`). */
    val backlogLength: Int get() = backlog.length

    /**
     * Puts one command's bytes into the stream: add their length to [offset], append them to the backlog,
     * and drop bytes from the front of the backlog until it holds at most [capacity].
     */
    fun feed(bytes: String) {
        TODO("lesson 10 lab: count the bytes into the offset and keep only the last capacity bytes")
    }

    /**
     * Answers a replica that last applied byte [replicaOffset] of history [replicaReplId].
     *
     * Continue only if both hold:
     * 1. The replica names this history: [replicaReplId] equals [replId], or it equals [replId2] and
     *    [replicaOffset] is at most [secondOffset] (the replica never saw bytes from after the switch).
     * 2. Every byte it is missing is still in the backlog: [replicaOffset] is between
     *    `offset - backlogLength` and [offset], both included.
     *
     * Then return [PsyncReply.Continue] with the bytes after [replicaOffset] (empty if it is up to date).
     * Otherwise return [PsyncReply.FullResync] with the current [replId] and [offset]. A brand-new replica
     * sends `PSYNC ? -1`, which never matches.
     */
    fun psync(replicaReplId: String, replicaOffset: Long): PsyncReply {
        TODO("lesson 10 lab: partial resync from the backlog when possible, full resync otherwise")
    }

    /**
     * What a replica does to its stream state when Sentinel promotes it to primary: the current ID becomes
     * [replId2], valid up to the current [offset] ([secondOffset]), and [newReplId] starts a new history.
     * The offset and the backlog carry on, so replicas of the old primary can still continue from it.
     */
    fun promote(newReplId: String) {
        TODO("lesson 10 lab: remember the old history, start a new one")
    }
}
