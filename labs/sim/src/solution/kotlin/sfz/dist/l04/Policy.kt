package sfz.dist.l04

/**
 * How a lease holder decides, using only what it can see: its own clock and the replies it has handled. Here that
 * clock is the simulator's, which is monotonic and exact, so lesson 3's clock problems are switched off and every
 * stale write you count comes from a pause.
 */
interface HolderPolicy {
    /**
     * When the holder believes its lease ends, after a grant or a renewal. [sentAt] is when it sent the request,
     * [handledAt] when its code handled the reply, [ttlMs] the lease length.
     */
    fun believedExpiry(sentAt: Long, handledAt: Long, ttlMs: Long): Long

    /** Checked at the start of each tick, before the work. */
    fun mayStartWork(now: Long, believedExpiry: Long): Boolean

    /** Checked when the work is done, right before the write is serialized and sent. */
    fun maySendWrite(now: Long, believedExpiry: Long): Boolean
}

/** The holder from the lesson's first section (given). It is wrong on purpose, in two ways. */
object Naive : HolderPolicy {
    // counts the lease from the moment it handled the reply: a reply that waited out a pause looks fresh
    override fun believedExpiry(sentAt: Long, handledAt: Long, ttlMs: Long) = handledAt + ttlMs

    // checks once, at the start of the tick
    override fun mayStartWork(now: Long, believedExpiry: Long) = now < believedExpiry

    // and never looks again before the write leaves
    override fun maySendWrite(now: Long, believedExpiry: Long) = true
}

/** The mitigations a holder can apply on its own. They shrink the damage; the lab measures how far. */
class Careful(val marginMs: Long) : HolderPolicy {
    // The service started the lease when the request arrived, which is after sentAt. Counting from sentAt can only
    // make the holder's deadline earlier than the real one, however long the reply waited in the socket.
    override fun believedExpiry(sentAt: Long, handledAt: Long, ttlMs: Long) = sentAt + ttlMs

    // Don't start work that the margin doesn't cover.
    override fun mayStartWork(now: Long, believedExpiry: Long) = believedExpiry - now >= marginMs

    // Look again after the work, as late as possible: a pause during the work is caught here. A pause after this
    // line is not, and nothing the holder does can catch it.
    override fun maySendWrite(now: Long, believedExpiry: Long) = believedExpiry - now >= marginMs
}
