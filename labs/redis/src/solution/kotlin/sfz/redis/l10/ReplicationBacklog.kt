package sfz.redis.l10

sealed interface PsyncReply {
    data class Continue(val missing: String) : PsyncReply

    data class FullResync(val replId: String, val offset: Long) : PsyncReply
}

class ReplicationBacklog(replId: String, val capacity: Int) {
    init {
        require(capacity > 0) { "the backlog needs room for at least one byte" }
    }

    var replId: String = replId
        private set

    var offset: Long = 0
        private set

    var replId2: String? = null
        private set

    var secondOffset: Long = -1
        private set

    private val backlog = StringBuilder()

    val backlogLength: Int get() = backlog.length

    fun feed(bytes: String) {
        offset += bytes.length                         // the offset counts every byte, kept or not
        backlog.append(bytes)
        val extra = backlog.length - capacity
        if (extra > 0) backlog.delete(0, extra)        // a ring buffer in real Redis: the oldest bytes are overwritten
    }

    fun psync(replicaReplId: String, replicaOffset: Long): PsyncReply {
        val sameHistory = replicaReplId == replId ||
            (replicaReplId == replId2 && replicaOffset <= secondOffset)   // old history, but not past the switch
        val inBacklog = replicaOffset in (offset - backlog.length)..offset
        if (!sameHistory || !inBacklog) return PsyncReply.FullResync(replId, offset)
        val missing = (offset - replicaOffset).toInt()
        return PsyncReply.Continue(backlog.substring(backlog.length - missing))   // only the bytes after its offset
    }

    fun promote(newReplId: String) {
        replId2 = replId                               // the old primary's history, up to here, is ours too
        secondOffset = offset
        replId = newReplId                             // anything written from now on is a new history
    }
}
