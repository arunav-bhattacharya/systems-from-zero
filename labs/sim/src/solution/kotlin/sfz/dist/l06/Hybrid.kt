package sfz.dist.l06

/**
 * A hybrid logical clock timestamp (Kulkarni et al., 2014): [l] is the largest wall-clock reading this node has
 * heard of, in milliseconds, and [c] counts events that share that [l].
 */
data class Hlc(val l: Long, val c: Int) : Comparable<Hlc> {
    override fun compareTo(other: Hlc): Int = compareValuesBy(this, other, Hlc::l, Hlc::c)   // given

    /** One Long: [l] in the top 48 bits, [c] in the low 16, so comparing the Longs compares the stamps. */
    fun pack(): Long = (l shl 16) or c.toLong()

    override fun toString() = "($l,$c)"

    companion object {
        const val MAX_C = 0xFFFF

        fun unpack(packed: Long): Hlc = Hlc(packed ushr 16, (packed and 0xFFFF).toInt())
    }
}

/** One node's hybrid logical clock. [physical] reads the node's own wall clock, in ms; it may jump back. */
class HybridClock(val node: Int, val physical: () -> Long) {
    var last = Hlc(0, 0)
        private set

    /** A local or send event (the paper's Figure 5, "send or local event"). */
    fun local(): Hlc {
        val pt = physical()
        val l = maxOf(last.l, pt)                        // follow the wall clock, but never go back
        val c = if (l == last.l) last.c + 1 else 0       // same l as before: count; the clock moved on: start at 0
        return set(l, c)
    }

    fun send(): Hlc = local()

    /** Receiving [m] (the paper's "receive event of message m"). */
    fun receive(m: Hlc): Hlc {
        val pt = physical()
        val l = maxOf(last.l, m.l, pt)                   // the largest time anyone in my past has seen
        val c = when {
            l == last.l && l == m.l -> maxOf(last.c, m.c) + 1
            l == last.l -> last.c + 1                    // my own l won
            l == m.l -> m.c + 1                          // the sender's l won: continue its count
            else -> 0                                    // my wall clock is ahead of both
        }
        return set(l, c)
    }

    private fun set(l: Long, c: Int): Hlc {
        check(c <= Hlc.MAX_C) { "the counter would overflow 16 bits" }
        last = Hlc(l, c)
        return last
    }
}
