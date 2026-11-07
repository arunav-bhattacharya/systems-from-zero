package sfz.net.l08

/**
 * Reno congestion control (RFC 5681), the sender's guess of how much the path can carry. Every
 * number here counts segments, not bytes: multiply by the MSS (1,448 bytes in the lesson's
 * captures) to get bytes.
 *
 * [cwnd] is the congestion window: how many segments may be in flight, unacknowledged, right now.
 * [ssthresh] is the slow-start threshold: below it the window grows fast, above it slowly. It
 * starts "infinite", so a new connection is in slow start until its first loss.
 *
 * This version simplifies fast recovery the way most diagrams do: after three duplicate ACKs the
 * window drops straight to the new [ssthresh].
 */
class Reno(initialWindow: Int = 10) {
    /** Segments allowed in flight. Linux starts at 10 (RFC 6928). */
    var cwnd: Int = initialWindow
        private set

    var ssthresh: Int = Int.MAX_VALUE
        private set

    val inSlowStart: Boolean
        get() = cwnd < ssthresh

    // ACKs counted toward the next +1 in congestion avoidance (Linux calls it snd_cwnd_cnt)
    private var acked = 0

    /**
     * One ACK arrived that acknowledges one new segment.
     * - In slow start, add one segment for every ACK. A whole window of ACKs comes back each round
     *   trip, so the window doubles every round trip.
     * - In congestion avoidance, count ACKs, and add one segment once a full window's worth
     *   (`cwnd` of them) has arrived: one more segment per round trip. Integer counting keeps it
     *   exact, which is also how Linux does it.
     */
    fun onAck() {
        if (inSlowStart) {
            cwnd += 1                       // exponential: doubles per round trip
        } else if (++acked >= cwnd) {
            cwnd += 1                       // linear: one segment per round trip
            acked = 0
        }
    }

    /**
     * Three duplicate ACKs: one segment was lost, but later ones are still arriving, so the path
     * still works. Halve: `ssthresh = max(cwnd / 2, 2)`, then `cwnd = ssthresh`. Reset the ACK count.
     */
    fun onTripleDuplicateAck() {
        ssthresh = maxOf(cwnd / 2, 2)       // multiplicative decrease
        cwnd = ssthresh
        acked = 0
    }

    /**
     * The retransmission timer fired: nothing came back for a whole timeout, the worst sign there
     * is. `ssthresh = max(cwnd / 2, 2)` as above, but restart from `cwnd = 1` and slow start again.
     */
    fun onTimeout() {
        ssthresh = maxOf(cwnd / 2, 2)
        cwnd = 1                            // start over, carefully
        acked = 0
    }
}
