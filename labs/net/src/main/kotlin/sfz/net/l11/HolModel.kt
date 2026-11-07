package sfz.net.l11

/** One packet on the wire, carrying [bytes] bytes of one stream's data. */
data class Packet(val stream: Int, val bytes: Int)

/**
 * The timing of a lossy path. Packet i leaves at `i * sendGapMs` and arrives [oneWayMs] later. A lost
 * packet is sent again [resendAfterMs] after it first left (the time the sender needs to notice), and
 * that copy arrives [oneWayMs] after that.
 */
data class Timing(val sendGapMs: Long, val oneWayMs: Long, val resendAfterMs: Long)

/**
 * Head-of-line blocking, as a model. The same packets cross the same lossy path; what differs is when
 * the receiver may hand bytes to the application.
 *
 * Both functions return, for every stream, the time (ms) at which the application has all of that
 * stream's bytes: the delivery time of the stream's last packet.
 */
object HolModel {

    /** When packet [i] reaches the receiver, lost or not. */
    fun arrival(i: Int, lost: Set<Int>, t: Timing): Long {
        TODO("i * gap + oneWay, plus resendAfter if i was lost")
    }

    /**
     * HTTP/2 over TCP. TCP delivers one byte stream in order: packet i reaches the application only
     * when it and every packet before it, of any stream, have arrived.
     */
    fun tcp(packets: List<Packet>, lost: Set<Int>, t: Timing): Map<Int, Long> {
        TODO("delivery(i) = the latest arrival among packets 0..i")
    }

    /**
     * HTTP/3 over QUIC. QUIC keeps order only within a stream: packet i reaches the application when
     * it and every earlier packet of the same stream have arrived.
     */
    fun quic(packets: List<Packet>, lost: Set<Int>, t: Timing): Map<Int, Long> {
        TODO("delivery(i) = the latest arrival among earlier packets of the same stream")
    }
}
