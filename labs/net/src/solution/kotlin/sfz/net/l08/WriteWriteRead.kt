package sfz.net.l08

/**
 * How long one write-write-read request takes: the client writes a [header], then a [body], then
 * waits for the server's reply. The server replies only once it has the whole request. This part
 * is finished; it uses your [NagleSender].
 *
 * [rttMillis] is the round trip. [delayedAckMillis] is how long the server's kernel holds back an
 * ACK when it has no data to send with it (delayed ACK, RFC 1122: under 500 ms; Linux waits at
 * least 40 ms). Returns milliseconds from the first write to the reply arriving.
 */
fun writeWriteRead(header: Int, body: Int, rttMillis: Double, delayedAckMillis: Double, noDelay: Boolean): Double {
    val oneWay = rttMillis / 2
    val sender = NagleSender(noDelay = noDelay)
    val first = sender.write(header)                     // at t = 0
    val second = sender.write(body)                      // a moment later
    check(first.sum() == header) { "the first write always goes out: nothing was unacknowledged" }
    if (second.sum() == body) {
        // both segments left at once; the server has the whole request after one way, replies at once
        return oneWay + oneWay
    }
    // only the header left. The server has half a request and nothing to send, so it delays its ACK.
    val ackLeavesServer = oneWay + delayedAckMillis
    val ackArrives = ackLeavesServer + oneWay
    val released = sender.onAck(header)                  // Nagle lets the body go now
    check(released.sum() == body) { "the ACK should release the body" }
    val bodyArrives = ackArrives + oneWay
    return bodyArrives + oneWay                          // the reply comes straight back
}
