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
    private class Mapping(val inside: Flow, val publicPort: Int, var lastSeen: Long)

    private val byInside = HashMap<Flow, Mapping>()   // outbound lookups: the original flow
    private val byPort = HashMap<Int, Mapping>()      // inbound lookups: the public port

    private fun expire() {
        val now = clock()
        val idle = byInside.values.filter { now - it.lastSeen >= idleTimeoutMillis }
        for (m in idle) {                             // forget it in both maps, so the port is free again
            byInside.remove(m.inside)
            byPort.remove(m.publicPort)
        }
    }

    /**
     * A packet from the inside, on its way out. Returns the packet as it leaves: source rewritten to
     * [publicIp] and the mapping's public port, destination unchanged. The first packet of a new
     * connection creates the mapping; later packets reuse it and keep it alive.
     * Returns null (drop) when every port in [ports] is taken.
     */
    fun outbound(packet: Flow): Flow? {
        expire()
        val m = byInside[packet] ?: run {
            val port = ports.firstOrNull { it !in byPort } ?: return null   // table full: drop
            Mapping(packet, port, clock()).also { byInside[packet] = it; byPort[port] = it }
        }
        m.lastSeen = clock()
        return packet.copy(srcIp = publicIp, srcPort = m.publicPort)       // the server will see this
    }

    /**
     * A packet from the outside, arriving at the public address. Returns it rewritten for the inside
     * host (destination back to the inside ip:port), or null to drop it. Drop it unless it is sent to
     * [publicIp], to a port with a live mapping, and comes from exactly the remote ip:port that mapping
     * talks to. A matching packet keeps the mapping alive.
     */
    fun inbound(packet: Flow): Flow? {
        expire()
        if (packet.dstIp != publicIp) return null
        val m = byPort[packet.dstPort] ?: return null                      // nobody inside asked: drop
        // only the remote this connection talks to may answer on this port
        if (packet.srcIp != m.inside.dstIp || packet.srcPort != m.inside.dstPort) return null
        m.lastSeen = clock()
        return packet.copy(dstIp = m.inside.srcIp, dstPort = m.inside.srcPort)
    }

    /** How many live mappings the table holds right now. */
    fun activeMappings(): Int {
        expire()
        return byInside.size
    }
}
