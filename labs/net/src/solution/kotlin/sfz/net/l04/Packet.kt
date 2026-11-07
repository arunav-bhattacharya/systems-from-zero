package sfz.net.l04

/**
 * An IPv4 packet, cut down to the fields a router looks at. [size] is the whole packet in bytes,
 * IP header included. Every packet in this lab has the Don't Fragment flag set, as Linux sets it
 * on TCP and on ping, so a router never splits one: it drops it and says why.
 *
 * This file is complete.
 */
data class Packet(val src: Int, val dst: Int, val ttl: Int, val size: Int, val body: Body) {
    override fun toString() = "${Ip.format(src)} > ${Ip.format(dst)} ttl $ttl size $size $body"
}

/** What the packet carries. */
sealed interface Body

/** A UDP datagram. Traceroute's probes are UDP datagrams to ports nobody listens on (33434 and up). */
data class Udp(val srcPort: Int, val dstPort: Int) : Body

/** A ping: ICMP echo request (type 8) or echo reply (type 0). */
data class Echo(val id: Int, val seq: Int, val reply: Boolean = false) : Body

/**
 * An ICMP error: the message a router or host sends back to a packet's source when it drops it.
 * [original] is the dropped packet as that node received it. The real message quotes its IP header
 * and at least its first 8 bytes (the UDP ports), which is how the sender tells which packet died.
 * [mtu] is set only for Fragmentation Needed: the largest packet the next link carries.
 */
data class IcmpError(val type: Int, val code: Int, val original: Packet, val mtu: Int = 0) : Body {
    override fun toString() = "ICMP $type/$code about (${original.body})" + if (mtu > 0) " mtu $mtu" else ""
}

/** The ICMP types and codes this lab uses (RFC 792 and RFC 1191). */
object Icmp {
    const val DEST_UNREACHABLE = 3
    const val TIME_EXCEEDED = 11

    /** Codes for DEST_UNREACHABLE. */
    const val NET_UNREACHABLE = 0
    const val PORT_UNREACHABLE = 3
    const val FRAG_NEEDED = 4

    /** An ICMP error is 20 bytes of IP header, 8 of ICMP header, and the quoted 20-byte header plus 8 bytes. */
    const val ERROR_SIZE = 56

    /** Linux starts every packet it sends with this TTL (net.ipv4.ip_default_ttl). */
    const val DEFAULT_TTL = 64
}
