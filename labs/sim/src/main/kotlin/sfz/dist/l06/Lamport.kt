package sfz.dist.l06

/** A Lamport timestamp: the counter, and the node that made it to break ties. */
data class Stamp(val counter: Long, val node: Int) : Comparable<Stamp> {
    /** Compare by [counter]; when two stamps have the same counter, the smaller [node] id comes first. */
    override fun compareTo(other: Stamp): Int = TODO("dist-06 lab: counter first, then node")

    override fun toString() = "($counter,$node)"
}

/** One node's Lamport clock. No wall clock anywhere: it counts events. */
class LamportClock(val node: Int) {
    var counter = 0L
        private set

    /** A local event: add one to [counter] and return the stamp. */
    fun local(): Stamp = TODO("dist-06 lab: count the event")

    /** Sending is an event too; the stamp travels with the message. */
    fun send(): Stamp = local()

    /** Receiving: jump past the larger of your counter and the message's, then count the receive itself. */
    fun receive(message: Stamp): Stamp = TODO("dist-06 lab: max of the two counters, plus one")
}
