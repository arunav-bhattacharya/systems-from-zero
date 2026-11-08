package sfz.dist.l06

/** A Lamport timestamp: the counter, and the node that made it to break ties. */
data class Stamp(val counter: Long, val node: Int) : Comparable<Stamp> {
    // counter first; two nodes can reach the same counter, so the node id breaks the tie and the order is total
    override fun compareTo(other: Stamp): Int = compareValuesBy(this, other, Stamp::counter, Stamp::node)

    override fun toString() = "($counter,$node)"
}

/** One node's Lamport clock. No wall clock anywhere: it counts events. */
class LamportClock(val node: Int) {
    var counter = 0L
        private set

    /** A local event: count it. */
    fun local(): Stamp {
        counter++
        return Stamp(counter, node)
    }

    /** Sending is an event too; the stamp travels with the message. */
    fun send(): Stamp = local()

    /** Jump past anything the sender had counted, then count the receive itself. */
    fun receive(message: Stamp): Stamp {
        counter = maxOf(counter, message.counter) + 1
        return Stamp(counter, node)
    }
}
