package sfz.net.l08

/**
 * The sending side of one TCP connection, reduced to Nagle's algorithm (RFC 896, and RFC 9293
 * section 3.7.4): "don't send a small segment while an earlier one is still unacknowledged."
 *
 * The program calls [write]; the kernel decides what goes on the wire now. The rule:
 * - With [noDelay] (the `TCP_NODELAY` socket option), or when nothing sent is still unacknowledged,
 *   send everything buffered at once, cut into segments of at most [mss] bytes.
 * - Otherwise send only full segments of [mss] bytes, and hold the rest back until the ACK for
 *   everything in flight arrives ([onAck] brings [unacked] to 0). Then send what was held.
 *
 * Both methods return the sizes of the segments sent now, in order (empty when nothing goes out).
 * Sending adds to [unacked].
 */
class NagleSender(private val mss: Int = 1448, private val noDelay: Boolean = false) {
    /** Bytes sent and not yet acknowledged. */
    var unacked: Int = 0
        private set

    /** Bytes written by the program and not yet sent. */
    var buffered: Int = 0
        private set

    fun write(bytes: Int): List<Int> {
        buffered += bytes
        return flush()
    }

    /** The peer acknowledged [bytes] more bytes. */
    fun onAck(bytes: Int): List<Int> {
        unacked -= bytes
        return flush()
    }

    private fun flush(): List<Int> {
        val sent = mutableListOf<Int>()
        if (noDelay || unacked == 0) {
            while (buffered > 0) sent += take(minOf(buffered, mss))      // everything, now
        } else {
            while (buffered >= mss) sent += take(mss)                    // full segments only
        }                                                                // a small tail waits for the ACK
        return sent
    }

    private fun take(n: Int): Int {
        buffered -= n
        unacked += n
        return n
    }
}
