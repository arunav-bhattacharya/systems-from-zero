package sfz.net.l07

/**
 * The eleven states of a TCP connection from RFC 9293, as `ss -tan` prints them (with dashes:
 * `SYN-SENT`, `FIN-WAIT-2`, `TIME-WAIT`).
 *
 * The client side goes CLOSED, SYN_SENT, ESTABLISHED. The server side goes CLOSED, LISTEN,
 * SYN_RECEIVED, ESTABLISHED. Whoever closes first goes FIN_WAIT_1, FIN_WAIT_2, TIME_WAIT, CLOSED;
 * the other side goes CLOSE_WAIT, LAST_ACK, CLOSED. CLOSING is the rare case where both close at
 * the same moment.
 */
enum class TcpState {
    CLOSED, LISTEN, SYN_SENT, SYN_RECEIVED, ESTABLISHED,
    FIN_WAIT_1, FIN_WAIT_2, CLOSING, TIME_WAIT,
    CLOSE_WAIT, LAST_ACK,
}
