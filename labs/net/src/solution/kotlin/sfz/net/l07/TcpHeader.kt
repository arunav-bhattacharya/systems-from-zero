package sfz.net.l07

import java.nio.ByteBuffer

/**
 * Reads the TCP segment out of one captured Ethernet frame (IPv4 inside), as tcpdump does.
 *
 * Where everything is:
 * - Ethernet is 14 bytes. The IPv4 header starts at byte 14. Its length is the low 4 bits of its
 *   first byte times 4 (`0x45` means 20 bytes). Bytes 2-3 of the IPv4 header are the total length
 *   of the IP packet, and byte 9 is the protocol, which must be 6 (TCP).
 * - The TCP header starts right after the IPv4 header:
 *   bytes 0-1 source port, 2-3 destination port, 4-7 sequence number, 8-11 acknowledgment number,
 *   the high 4 bits of byte 12 are the header length in 32-bit words (`a0` means 10 words = 40
 *   bytes), byte 13 holds the flags, 14-15 the window.
 * - Options fill the header after its first 20 bytes. Each option starts with a kind byte:
 *   0 ends the list, 1 is a one-byte NOP (padding), and every other kind is followed by a length
 *   byte that counts the kind and length bytes too. Kind 2 is the MSS: length 4, then 16 bits.
 * - The payload length is the IP total length minus both header lengths. Don't use the frame's
 *   size: Ethernet pads frames shorter than 60 bytes with zeros that belong to no one.
 *
 * Throws [IllegalArgumentException] when the frame doesn't carry IPv4 and TCP.
 */
object TcpHeader {
    fun parse(frame: ByteArray): Segment {
        val b = ByteBuffer.wrap(frame)                             // big-endian, network byte order
        require(b.getShort(12).toInt() and 0xffff == 0x0800) { "not IPv4" }
        val ip = 14
        val ipHeaderLength = (frame[ip].toInt() and 0x0f) * 4
        val ipTotalLength = b.getShort(ip + 2).toInt() and 0xffff
        require(frame[ip + 9].toInt() == 6) { "not TCP" }

        val tcp = ip + ipHeaderLength
        val tcpHeaderLength = ((frame[tcp + 12].toInt() and 0xf0) ushr 4) * 4

        // options: everything between byte 20 and the end of the TCP header
        var mss: Int? = null
        var at = tcp + 20
        while (at < tcp + tcpHeaderLength) {
            when (val kind = frame[at].toInt() and 0xff) {
                0 -> break                                         // end of option list
                1 -> at += 1                                       // NOP: one byte of padding
                else -> {
                    val length = frame[at + 1].toInt() and 0xff    // counts kind and length too
                    if (kind == 2) mss = b.getShort(at + 2).toInt() and 0xffff
                    at += length
                }
            }
        }

        return Segment(
            srcPort = b.getShort(tcp).toInt() and 0xffff,
            dstPort = b.getShort(tcp + 2).toInt() and 0xffff,
            seq = b.getInt(tcp + 4).toLong() and 0xFFFF_FFFFL,     // unsigned 32-bit
            ack = b.getInt(tcp + 8).toLong() and 0xFFFF_FFFFL,
            flags = Flag.decode(frame[tcp + 13].toInt() and 0xff),
            window = b.getShort(tcp + 14).toInt() and 0xffff,
            payloadLength = ipTotalLength - ipHeaderLength - tcpHeaderLength,
            mss = mss,
        )
    }
}
