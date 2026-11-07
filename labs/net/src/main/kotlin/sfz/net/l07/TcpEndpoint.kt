package sfz.net.l07

import sfz.net.l07.Flag.ACK
import sfz.net.l07.Flag.FIN
import sfz.net.l07.Flag.PSH
import sfz.net.l07.Flag.RST
import sfz.net.l07.Flag.SYN
import sfz.net.l07.TcpState.CLOSED
import sfz.net.l07.TcpState.CLOSE_WAIT
import sfz.net.l07.TcpState.CLOSING
import sfz.net.l07.TcpState.ESTABLISHED
import sfz.net.l07.TcpState.FIN_WAIT_1
import sfz.net.l07.TcpState.FIN_WAIT_2
import sfz.net.l07.TcpState.LAST_ACK
import sfz.net.l07.TcpState.LISTEN
import sfz.net.l07.TcpState.SYN_RECEIVED
import sfz.net.l07.TcpState.SYN_SENT
import sfz.net.l07.TcpState.TIME_WAIT

/**
 * One end of a TCP connection: the state the kernel keeps for one socket, reduced to the
 * connection's life story. It doesn't resend, buffer or measure anything. It only follows the
 * rules for opening, numbering and closing, the ones the first Try it captured on the wire.
 *
 * [isn] is this side's initial sequence number (a real kernel picks it at random). [sndNxt] is the
 * next sequence number this side will use, [rcvNxt] the next one it expects from the peer, which
 * is also the number every ACK it sends carries. A SYN and a FIN each use up one sequence number,
 * so add [Segment.sequenceLength], never just the payload. Use [seqPlus] for all sequence
 * arithmetic.
 *
 * Every segment this endpoint sends has `srcPort = localPort`, `dstPort = remotePort` and
 * `window = window`. Time comes from [clock] (milliseconds), so the tests can move it by hand.
 */
class TcpEndpoint(
    val localPort: Int,
    private val isn: Long,
    private val clock: () -> Long = System::currentTimeMillis,
    private val timeWaitMillis: Long = 60_000,
    private val window: Int = 502,
) {
    var state: TcpState = CLOSED
        private set

    /** The peer's port, known after [connect] or after a SYN arrives in LISTEN. */
    var remotePort: Int = 0
        private set

    var sndNxt: Long = isn
        private set

    var rcvNxt: Long = 0
        private set

    /** True once an RST ended the connection: "connection refused" in SYN_SENT, "reset by peer" later. */
    var reset: Boolean = false
        private set

    // add whatever private fields you need, for example when TIME_WAIT started

    /** A server socket: CLOSED to LISTEN. This part is finished. */
    fun listen() {
        check(state == CLOSED) { "listen() in $state" }
        state = LISTEN
    }

    /**
     * The client's `connect()`: remember [remotePort], go to SYN_SENT and return the SYN, which
     * carries `seq = isn`, `ack = 0` and only the SYN flag. The SYN uses one sequence number.
     */
    fun connect(remotePort: Int): Segment {
        TODO("SYN_SENT; return SYN(seq = isn); sndNxt = isn + 1")
    }

    /**
     * The program writes [bytes] bytes. Allowed in ESTABLISHED and in CLOSE_WAIT (the peer has
     * finished sending, but this side may still talk). Returns one segment with PSH and ACK,
     * `seq = sndNxt`, `ack = rcvNxt` and that payload length, and moves [sndNxt] on.
     */
    fun send(bytes: Int): Segment {
        TODO("check the state; return [P.] seq = sndNxt ack = rcvNxt; advance sndNxt by bytes")
    }

    /**
     * The program calls `close()`: send a FIN (with ACK) at `seq = sndNxt`. From ESTABLISHED this
     * side closes first and goes to FIN_WAIT_1; from CLOSE_WAIT it closes second and goes to
     * LAST_ACK. The FIN uses one sequence number.
     */
    fun close(): Segment {
        TODO("FIN_WAIT_1 or LAST_ACK; return [F.] seq = sndNxt ack = rcvNxt; sndNxt + 1")
    }

    /**
     * A segment arrived for this socket. Returns the segment to send back, or null for none.
     *
     * - CLOSED (nobody listens on this port): answer anything that isn't an RST with an RST.
     *   With no ACK flag on the incoming segment the reply is RST+ACK with `seq = 0` and
     *   `ack = seg.seq + seg.sequenceLength`, which is exactly what the "connection refused"
     *   capture shows. If the incoming segment has ACK, reply RST alone with `seq = seg.ack`.
     * - LISTEN: a SYN (without ACK) starts a connection. Remember its source port, set [rcvNxt] past
     *   the SYN, go to SYN_RECEIVED and return SYN+ACK with `seq = isn`. Ignore anything else.
     * - SYN_SENT: an RST whose `ack` is [sndNxt] means refused: go to CLOSED and set [reset].
     *   A SYN+ACK whose `ack` is [sndNxt]: set [rcvNxt] past its SYN, go to ESTABLISHED, return
     *   the ACK. Ignore anything else.
     * - Every other state: an RST closes at once (CLOSED, [reset]). In SYN_RECEIVED, the ACK of
     *   your SYN-ACK moves you to ESTABLISHED. In TIME_WAIT, a FIN means your last ACK was lost:
     *   send the ACK again and restart the TIME_WAIT timer.
     *   Otherwise, if the segment carries data or a FIN but its `seq` isn't [rcvNxt], it is out of
     *   order or a copy: don't take anything from it, just send an ACK of what you expect.
     *   Then in this order: if its ACK covers your FIN (`ack == sndNxt` after you sent one),
     *   FIN_WAIT_1 goes to FIN_WAIT_2, CLOSING goes to TIME_WAIT and LAST_ACK goes to CLOSED.
     *   Count its data into [rcvNxt]. If it has a FIN, count that too and move on: ESTABLISHED to
     *   CLOSE_WAIT, FIN_WAIT_1 to CLOSING (both sides closed at once), FIN_WAIT_2 to TIME_WAIT.
     *   Return an ACK (`seq = sndNxt`, `ack = rcvNxt`, flag ACK only) if it carried data or a FIN.
     *
     * Entering TIME_WAIT starts a timer: note `clock()`.
     */
    fun receive(seg: Segment): Segment? {
        TODO("follow the rules above, state by state")
    }

    /** A timer tick: TIME_WAIT ends, and the state becomes CLOSED, once [timeWaitMillis] have passed. */
    fun tick() {
        TODO("TIME_WAIT -> CLOSED when clock() - start >= timeWaitMillis")
    }
}
