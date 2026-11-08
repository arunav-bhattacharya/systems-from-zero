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

/**
 * The mitigations a holder can apply on its own. Write all three; each test in `MitigationTest` says which one it
 * needs. Remember that the lease service starts a lease when the request ARRIVES, which is after [sentAt] and before
 * [handledAt].
 */
class Careful(val marginMs: Long) : HolderPolicy {
    /** Count the lease from the moment the request left, so a reply that waited out a pause can't look fresh. */
    override fun believedExpiry(sentAt: Long, handledAt: Long, ttlMs: Long): Long =
        TODO("dist-04 lab: count the lease from sentAt")

    /** Start the work only if at least [marginMs] of the believed lease is left. */
    override fun mayStartWork(now: Long, believedExpiry: Long): Boolean =
        TODO("dist-04 lab: at least marginMs left?")

    /** Look again after the work, right before sending: at least [marginMs] still left? */
    override fun maySendWrite(now: Long, believedExpiry: Long): Boolean =
        TODO("dist-04 lab: check again, as late as possible")
}
