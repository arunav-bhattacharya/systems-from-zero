package sfz.net.l07

/** The TCP flags this lab uses, with their bit in byte 13 of the TCP header. */
enum class Flag(val bit: Int) {
    FIN(0x01), SYN(0x02), RST(0x04), PSH(0x08), ACK(0x10), URG(0x20);

    companion object {
        /** The flags whose bits are set in [byte]. */
        fun decode(byte: Int): Set<Flag> = entries.filter { byte and it.bit != 0 }.toSet()
    }
}

/**
 * One TCP segment, reduced to the fields this lesson needs. Sequence and acknowledgment numbers are
 * unsigned 32-bit values, kept in a [Long] so they never turn negative. [window] is the raw 16-bit
 * field (before any window scaling), [payloadLength] the number of data bytes, and [mss] the value
 * of the MSS option when the segment carries one (only SYNs do).
 */
data class Segment(
    val srcPort: Int,
    val dstPort: Int,
    val seq: Long,
    val ack: Long,
    val flags: Set<Flag>,
    val window: Int = 0,
    val payloadLength: Int = 0,
    val mss: Int? = null,
) {
    fun has(flag: Flag): Boolean = flag in flags

    /**
     * How much sequence space this segment uses: one number per data byte, plus one for a SYN and
     * one for a FIN. The ACK that answers it is `seq + sequenceLength`.
     */
    val sequenceLength: Long
        get() = payloadLength + (if (has(Flag.SYN)) 1L else 0L) + (if (has(Flag.FIN)) 1L else 0L)

    /** The same segment in tcpdump's notation, for example `50744 > 9000 [S.] seq 244700535 ack 4042781691`. */
    override fun toString(): String {
        val f = buildString {
            if (has(Flag.SYN)) append('S')
            if (has(Flag.FIN)) append('F')
            if (has(Flag.RST)) append('R')
            if (has(Flag.PSH)) append('P')
            if (has(Flag.ACK)) append('.')
        }
        val data = if (payloadLength > 0) " length $payloadLength" else ""
        return "$srcPort > $dstPort [$f] seq $seq ack $ack win $window$data"
    }
}

/** Adds [n] to a 32-bit sequence number, wrapping around after 4,294,967,295 as TCP does. */
fun seqPlus(seq: Long, n: Long): Long = (seq + n) and 0xFFFF_FFFFL
