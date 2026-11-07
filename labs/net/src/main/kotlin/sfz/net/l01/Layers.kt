package sfz.net.l01

// The parsed headers of one frame, one class per layer. These are complete: your work is in Decapsulate.kt.
// All numbers are unsigned on the wire, so every field here is widened to Int or Long and is never negative.

/** Ethernet II: 6 bytes destination MAC, 6 bytes source MAC, 2 bytes EtherType, then the payload. */
class EthernetFrame(
    /** Destination MAC, lower-case hex pairs joined by colons: `"22:d2:d5:a2:32:a3"`. */
    val dst: String,
    val src: String,
    /** What the payload is: 0x0800 IPv4, 0x0806 ARP, 0x86dd IPv6. */
    val etherType: Int,
    /** Everything after the 14-byte header. */
    val payload: ByteArray,
) {
    override fun toString() = "Ethernet $src > $dst type 0x%04x, %d bytes inside".format(etherType, payload.size)
}

/** IPv4: a header of at least 20 bytes, then the payload. */
class Ipv4Packet(
    /** Always 4 here. */
    val version: Int,
    /** Header length in bytes: the IHL field (low 4 bits of byte 0) times 4. 20 when there are no options. */
    val headerLength: Int,
    /** Header plus payload, in bytes (bytes 2 and 3). */
    val totalLength: Int,
    /** The Don't Fragment flag (bit 0x40 of byte 6). */
    val dontFragment: Boolean,
    /** Time to live (byte 8): every router lowers it by one and drops the packet at zero. */
    val ttl: Int,
    /** What the payload is (byte 9): 6 TCP, 17 UDP, 1 ICMP. */
    val protocol: Int,
    /** The header checksum as written in the packet (bytes 10 and 11). */
    val headerChecksum: Int,
    /** Source address, dotted: `"172.20.0.2"` (bytes 12 to 15). */
    val src: String,
    /** Destination address, dotted (bytes 16 to 19). */
    val dst: String,
    /** Exactly `totalLength - headerLength` bytes: the TCP segment, UDP datagram or ICMP message. */
    val payload: ByteArray,
) {
    override fun toString() = "IPv4 $src > $dst proto $protocol ttl $ttl, $totalLength bytes"
}

/** TCP: a header of at least 20 bytes, then the application's bytes. */
class TcpSegment(
    val srcPort: Int,
    val dstPort: Int,
    /** Sequence number: a 32-bit unsigned number, so it needs a Long. */
    val seq: Long,
    /** Acknowledgment number, also 32-bit unsigned. */
    val ack: Long,
    /** Header length in bytes: the data offset (high 4 bits of byte 12) times 4. 20 without options. */
    val headerLength: Int,
    /** The control flags set in byte 13. */
    val flags: Set<TcpFlag>,
    /** Receive window as written (before any window scaling). */
    val window: Int,
    /** The application's bytes: everything after the TCP header. Empty for a bare SYN or ACK. */
    val payload: ByteArray,
) {
    override fun toString() = "TCP $srcPort > $dstPort $flags seq $seq ack $ack, ${payload.size} bytes of data"
}

/** The TCP flags in byte 13 of the TCP header, with their bit values. */
enum class TcpFlag(val bit: Int) {
    FIN(0x01), SYN(0x02), RST(0x04), PSH(0x08), ACK(0x10), URG(0x20);

    companion object {
        /** The flags whose bits are set in [byte13]. */
        fun from(byte13: Int): Set<TcpFlag> = entries.filter { byte13 and it.bit != 0 }.toSet()
    }
}

/** One frame, peeled: the three headers and the application data at the centre. */
class Layers(val ethernet: EthernetFrame, val ip: Ipv4Packet, val tcp: TcpSegment) {
    /** The bytes the application wrote, for example an HTTP request. */
    val application: ByteArray get() = tcp.payload
}
