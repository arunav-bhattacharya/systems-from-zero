package sfz.net.l03

/** The four addresses a NAT looks at in a TCP or UDP packet. */
data class Flow(val srcIp: Int, val srcPort: Int, val dstIp: Int, val dstPort: Int) {
    override fun toString() = "${Ipv4.format(srcIp)}:$srcPort > ${Ipv4.format(dstIp)}:$dstPort"

    companion object {
        /** `Flow.of("10.10.1.10", 41000, "10.10.2.20", 8080)` */
        fun of(srcIp: String, srcPort: Int, dstIp: String, dstPort: Int) =
            Flow(Ipv4.parse(srcIp), srcPort, Ipv4.parse(dstIp), dstPort)
    }
}

/**
 * The translation table of a router doing NAT with port translation (what Linux calls MASQUERADE,
 * and what your home router does). Inside hosts have private addresses; the router has one
 * public address, [publicIp], and hands out ports from [ports].
 *
 * One mapping per connection: the inside flow (inside ip:port to remote ip:port) and the public port
 * the router chose for it. Each connection gets its own public port, the lowest free one in [ports].
 * (Linux is cleverer: it only needs the whole four-tuple to be unique, so it can reuse a port toward
 * different servers, and it keeps the inside port when it is free. One port per connection is enough
 * to show the idea.)
 *
 * A mapping that sees no packet in either direction for [idleTimeoutMillis] or longer is gone:
 * replies after that are dropped, and its port is free for a new connection.
 */
class NatTable(
    val publicIp: Int,
    val ports: IntRange = 40_000..40_999,
    private val idleTimeoutMillis: Long = 120_000,
    private val clock: () -> Long = System::currentTimeMillis,
) {
    // one entry per connection; you may keep a second map keyed by public port for inbound lookups
    private class Mapping(val inside: Flow, val publicPort: Int, var lastSeen: Long)

    private val byInside = HashMap<Flow, Mapping>()

    /**
     * A packet from the inside, on its way out. Returns the packet as it leaves: source rewritten to
     * [publicIp] and the mapping's public port, destination unchanged. The first packet of a new
     * connection creates the mapping; later packets reuse it and keep it alive.
     * Returns null (drop) when every port in [ports] is taken.
     */
    fun outbound(packet: Flow): Flow? {
        TODO("drop idle mappings, find or create the mapping, touch it, rewrite the source")
    }

    /**
     * A packet from the outside, arriving at the public address. Returns it rewritten for the inside
     * host (destination back to the inside ip:port), or null to drop it. Drop it unless it is sent to
     * [publicIp], to a port with a live mapping, and comes from exactly the remote ip:port that mapping
     * talks to. A matching packet keeps the mapping alive.
     */
    fun inbound(packet: Flow): Flow? {
        TODO("drop idle mappings, find the mapping by public port, check the remote, rewrite the destination")
    }

    /** How many live mappings the table holds right now. */
    fun activeMappings(): Int {
        TODO("drop idle mappings, then count")
    }
}
