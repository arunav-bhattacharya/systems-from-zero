package sfz.net.l07

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
        TODO("read ports, seq, ack, flags and window; walk the options for the MSS; compute the payload length from the IP total length")
    }
}
