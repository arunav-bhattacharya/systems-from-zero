package sfz.net.l01

// Peel a captured Ethernet frame one layer at a time, the way the receiving kernel does.
//
// Everything on the wire is big-endian ("network byte order"). java.nio.ByteBuffer reads
// big-endian by default, so ByteBuffer.wrap(bytes).getShort(2) gives you bytes 2 and 3 as one number.
// Bytes, shorts and ints in Java are signed, so widen them before you use them:
//   byte  -> (b.toInt() and 0xff)
//   short -> (s.toInt() and 0xffff)
//   int   -> (i.toLong() and 0xffffffffL)
// The tests feed you a real frame from curl http://example.com/ (see src/test/resources/sfz/net/l01).

/**
 * Reads the 14-byte Ethernet II header: destination MAC (bytes 0..5), source MAC (6..11),
 * EtherType (12..13). The payload is everything after byte 13.
 * Format MACs as lower-case hex pairs joined by colons.
 */
fun parseEthernet(frame: ByteArray): EthernetFrame {
    TODO("read the two MACs and the EtherType; the payload starts at byte 14")
}

/**
 * Reads an IPv4 header and cuts out its payload.
 *
 * The header length is NOT always 20: take the low 4 bits of byte 0 (IHL) and multiply by 4.
 * The payload ends at the total length (bytes 2..3), NOT at the end of the array: Ethernet pads
 * short frames with zeros up to 60 bytes, and those zeros are not part of the packet.
 */
fun parseIpv4(packet: ByteArray): Ipv4Packet {
    TODO("version and IHL from byte 0, total length, DF flag, TTL, protocol, checksum, both addresses, payload")
}

/**
 * Reads a TCP header. Ports are bytes 0..1 and 2..3, sequence number 4..7, acknowledgment 8..11,
 * data offset is the high 4 bits of byte 12 (times 4 gives the header length in bytes),
 * flags are byte 13 (use [TcpFlag.from]), window is 14..15. The payload starts after the header,
 * options included.
 */
fun parseTcp(segment: ByteArray): TcpSegment {
    TODO("ports, seq and ack as unsigned numbers, header length, flags, window, payload")
}

/**
 * Computes the IPv4 header checksum (RFC 791, RFC 1071): add up the header as 16-bit big-endian
 * words, treating the checksum field itself (bytes 10..11) as zero; fold any carry above 16 bits back
 * into the low 16 bits; return the one's complement (flip all bits) of the low 16 bits.
 *
 * [header] is just the header (headerLength bytes). A router that lowers the TTL must run this
 * again and write the new value, so the result depends on every byte of the header.
 */
fun ipv4Checksum(header: ByteArray): Int {
    TODO("sum 16-bit words, skip bytes 10 and 11, fold the carries, flip the bits")
}

/**
 * Peels all three headers off an Ethernet frame carrying IPv4 and TCP.
 * Check the "what's inside" field of each layer before you hand its payload to the next parser:
 * throw IllegalArgumentException if the EtherType is not 0x0800 or the IP protocol is not 6.
 */
fun decapsulate(frame: ByteArray): Layers {
    TODO("parseEthernet, check the EtherType, parseIpv4, check the protocol, parseTcp")
}
