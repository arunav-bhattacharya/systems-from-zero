package sfz.net.l04

/** One network card: its name, its address, and the largest packet its link carries (the MTU). */
data class Interface(val name: String, val address: Int, val mtu: Int = 1500) {
    companion object {
        fun of(name: String, address: String, mtu: Int = 1500) = Interface(name, Ip.parse(address), mtu)
    }
}

/** What a node decides to do with one packet. */
sealed interface Action

/** Send [packet] out of [dev] to [nextHop]: the next router, or the destination itself when it is on that link. */
data class Forward(val packet: Packet, val dev: String, val nextHop: Int) : Action

/** The packet is for this node. */
data class Deliver(val packet: Packet) : Action

/** The packet is dropped, and [error], an ICMP error, goes back to its source. */
data class Reply(val error: Packet) : Action

/** The packet is dropped and nobody is told. */
data object Drop : Action

/**
 * A machine with one or more cards and a routing table. A router has [forwarding] on (Linux:
 * `net.ipv4.ip_forward=1`); a host has it off and only accepts packets addressed to itself.
 * A node with [sendsIcmpErrors] off drops packets silently, like a router behind a firewall that
 * filters ICMP, or one whose ICMP rate limit is used up.
 */
class Node(
    val name: String,
    val interfaces: List<Interface>,
    val table: RoutingTable,
    val forwarding: Boolean = true,
    val sendsIcmpErrors: Boolean = true,
) {
    /** True when [addr] belongs to one of this node's cards. */
    fun owns(addr: Int): Boolean = interfaces.any { it.address == addr }

    /** The card called [name]. */
    fun iface(name: String): Interface = interfaces.first { it.name == name }

    /**
     * The address this node writes as the source of a packet to [dst]: the address of the card its
     * route to [dst] leaves through. Linux does the same for ICMP errors, which is why traceroute shows
     * each router's address on the side facing you.
     */
    fun addressToward(dst: Int): Int =
        table.lookup(dst)?.let { iface(it.dev).address } ?: interfaces.first().address

    /**
     * What Linux does with one arriving packet, in this order:
     *
     * 1. Addressed to one of my cards: [Deliver], whatever its TTL.
     * 2. Not mine and [forwarding] is off (a host): [Drop].
     * 3. TTL 1 or less: it may not cross another link. Reply with ICMP Time Exceeded (type 11, code 0).
     * 4. Look up the destination. No route: reply Destination Unreachable, Net Unreachable (3/0).
     * 5. Bigger than the MTU of the card the route leaves through: reply Destination Unreachable,
     *    Fragmentation Needed (3/4), with that card's MTU in [IcmpError.mtu].
     * 6. Otherwise [Forward] a copy with the TTL one lower, out of the route's card, to the route's `via`,
     *    or to the destination itself when `via` is null.
     *
     * Every ICMP error is a new [Packet]: source [addressToward] the dropped packet's source, destination
     * that source, TTL [Icmp.DEFAULT_TTL], size [Icmp.ERROR_SIZE], body an [IcmpError] quoting the packet
     * exactly as it arrived. Two exceptions turn a [Reply] into a [Drop]: this node doesn't send ICMP
     * errors, or the dropped packet is itself an ICMP error (RFC 1122: never answer an error with an
     * error, or two confused routers could bounce errors between them forever).
     */
    fun handle(packet: Packet): Action {
        if (owns(packet.dst)) return Deliver(packet)               // for me: TTL no longer matters
        if (!forwarding) return Drop                               // a host never passes packets on
        if (packet.ttl <= 1) return error(Icmp.TIME_EXCEEDED, 0, packet)   // Linux checks <= 1 before it decrements
        val route = table.lookup(packet.dst)
            ?: return error(Icmp.DEST_UNREACHABLE, Icmp.NET_UNREACHABLE, packet)
        val out = iface(route.dev)
        if (packet.size > out.mtu) {                               // DF is always set here: never split, report
            return error(Icmp.DEST_UNREACHABLE, Icmp.FRAG_NEEDED, packet, out.mtu)
        }
        return Forward(packet.copy(ttl = packet.ttl - 1), route.dev, route.via ?: packet.dst)
    }

    private fun error(type: Int, code: Int, about: Packet, mtu: Int = 0): Action {
        if (!sendsIcmpErrors || about.body is IcmpError) return Drop   // silent node, or an error about an error
        val reply = Packet(
            src = addressToward(about.src),                        // the card on my way back to the sender
            dst = about.src,
            ttl = Icmp.DEFAULT_TTL,
            size = Icmp.ERROR_SIZE,
            body = IcmpError(type, code, about, mtu),              // quote the packet as it arrived
        )
        return Reply(reply)
    }
}
