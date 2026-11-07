package sfz.net.support

/**
 * Gets application bytes out of captured frames, for labs that parse what TCP carries (TLS in
 * lesson 10, HTTP/2 in lesson 11) rather than the headers around it.
 */
object Tcp {
    /** The TCP payload of one Ethernet + IPv4 + TCP frame (any Ethernet padding is dropped). */
    fun payload(frame: ByteArray): ByteArray {
        require(frame.size >= 54 && (frame[12].toInt() and 0xff) == 0x08 && frame[13].toInt() == 0x00) { "not an IPv4 frame" }
        val ip = 14
        val ipHeader = (frame[ip].toInt() and 0x0f) * 4
        val totalLength = ((frame[ip + 2].toInt() and 0xff) shl 8) or (frame[ip + 3].toInt() and 0xff)
        require(frame[ip + 9].toInt() == 6) { "not TCP" }
        val tcp = ip + ipHeader
        val tcpHeader = ((frame[tcp + 12].toInt() and 0xf0) shr 4) * 4
        return frame.copyOfRange(tcp + tcpHeader, ip + totalLength)
    }

    /** The payloads of several frames joined in order: the bytes one side wrote, as the receiver reads them. */
    fun stream(frames: List<ByteArray>): ByteArray =
        frames.fold(ByteArray(0)) { acc, f -> acc + payload(f) }

    /** The source port of a TCP frame, to tell the two directions of one connection apart. */
    fun sourcePort(frame: ByteArray): Int {
        val tcp = 14 + (frame[14].toInt() and 0x0f) * 4
        return ((frame[tcp].toInt() and 0xff) shl 8) or (frame[tcp + 1].toInt() and 0xff)
    }
}
