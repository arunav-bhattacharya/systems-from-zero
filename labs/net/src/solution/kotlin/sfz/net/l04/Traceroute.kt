package sfz.net.l04

/**
 * One line of traceroute output: the TTL of the probe, who answered it (null prints as `*`), and the
 * ICMP type and code of the answer.
 */
data class Hop(val ttl: Int, val from: Int?, val icmpType: Int? = null, val icmpCode: Int? = null) {
    /** The destination itself answered: Port Unreachable for the probe's port. */
    val reached: Boolean get() = icmpType == Icmp.DEST_UNREACHABLE && icmpCode == Icmp.PORT_UNREACHABLE

    override fun toString() = "%2d  %s".format(ttl, from?.let(Ip::format) ?: "*")
}

/** The first destination port Linux traceroute uses (`-p`); each later probe uses the next port. */
const val TRACEROUTE_BASE_PORT = 33434

/**
 * Traceroute from [src] to [dst], the way Linux's `traceroute` does by default, one probe per TTL.
 *
 * For each TTL from 1 to [maxHops]: build a 60-byte UDP probe from [src] to [dst] with that TTL, to
 * port [TRACEROUTE_BASE_PORT] + (ttl - 1) (any source port, say 40000), and pass it to [send], which
 * returns whatever came back for it, or null when nothing did.
 *
 * - An answer counts only if it is an [IcmpError] whose quoted original is a UDP datagram to this
 *   probe's port. Anything else (a stray error about an older probe, no answer) is a `*` hop.
 * - Time Exceeded: record the hop (the answer's source address) and go on with the next TTL.
 * - Destination Unreachable of any code: record the hop and stop. Port Unreachable means the
 *   destination answered; any other code means the path ends there.
 */
fun traceroute(src: Int, dst: Int, maxHops: Int = 30, send: (Packet) -> Packet?): List<Hop> {
    val hops = mutableListOf<Hop>()
    for (ttl in 1..maxHops) {
        val port = TRACEROUTE_BASE_PORT + ttl - 1                  // the port is how we recognise the answer
        val answer = send(Packet(src, dst, ttl, 60, Udp(40_000, port)))
        val error = answer?.body as? IcmpError
        val quoted = error?.original?.body as? Udp
        if (error == null || quoted?.dstPort != port) {            // nothing, or not about this probe
            hops += Hop(ttl, null)
            continue
        }
        hops += Hop(ttl, answer.src, error.type, error.code)
        if (error.type == Icmp.DEST_UNREACHABLE) break             // reached, or the path ends here
    }
    return hops
}
