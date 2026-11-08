package sfz.dist.l06

/**
 * A hybrid logical clock timestamp (Kulkarni et al., 2014): [l] is the largest wall-clock reading this node has
 * heard of, in milliseconds, and [c] counts events that share that [l].
 */
data class Hlc(val l: Long, val c: Int) : Comparable<Hlc> {
    override fun compareTo(other: Hlc): Int = compareValuesBy(this, other, Hlc::l, Hlc::c)   // given

    /** One Long: [l] in the top 48 bits, [c] in the low 16, so comparing the Longs compares the stamps. */
    fun pack(): Long = TODO("dist-06 lab: l shifted left 16, or c")

    override fun toString() = "($l,$c)"

    companion object {
        const val MAX_C = 0xFFFF

        /** The inverse of [pack]. */
        fun unpack(packed: Long): Hlc = TODO("dist-06 lab: the top 48 bits and the low 16")
    }
}

/**
 * One node's hybrid logical clock. [physical] reads the node's own wall clock, in ms; it may jump back.
 * Keep the latest stamp in [last] (start: (0, 0)) and follow the paper's Figure 5, which the lesson walks through.
 */
class HybridClock(val node: Int, val physical: () -> Long) {
    var last = Hlc(0, 0)
        private set

    /**
     * A local or send event. l becomes the larger of last.l and the wall clock. If l didn't change, c is last.c + 1;
     * if it moved forward, c starts again at 0.
     */
    fun local(): Hlc = TODO("dist-06 lab: send or local event")

    fun send(): Hlc = local()

    /**
     * Receiving [m]. l becomes the largest of last.l, m.l and the wall clock. Then c depends on which of them won:
     * both last.l and m.l: max(last.c, m.c) + 1. Only last.l: last.c + 1. Only m.l: m.c + 1. Only the wall clock: 0.
     */
    fun receive(m: Hlc): Hlc = TODO("dist-06 lab: receive event")
}
