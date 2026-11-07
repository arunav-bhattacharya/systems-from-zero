package sfz.net.l04

/**
 * A set of [Node]s that pass packets to each other. You give a packet to one node and the network
 * follows it: each node's [Node.handle] decides, and a [Forward] hands the packet to whichever node
 * owns the next-hop address. The hosts answer what reaches them the way Linux does: a ping gets an echo
 * reply, and a UDP datagram to a port nobody listens on gets ICMP Port Unreachable.
 *
 * This file is complete.
 */
class Network(val nodes: List<Node>) {
    /** One packet arriving at a node that accepted it. */
    data class Arrival(val node: Node, val packet: Packet)

    fun node(name: String): Node = nodes.first { it.name == name }

    private fun owner(addr: Int): Node? = nodes.firstOrNull { it.owns(addr) }

    /**
     * Sends [packet] from [origin], which looks up its own route but doesn't lower the TTL (a host only
     * does that when it forwards), and follows it and everything it causes: ICMP errors from routers,
     * and the destination's answer. Returns every packet that some node accepted, in order. A packet
     * sent to a next hop that no node owns is lost, like a frame to a machine that is switched off.
     */
    fun send(origin: Node, packet: Packet): List<Arrival> {
        val arrivals = mutableListOf<Arrival>()
        val queue = ArrayDeque<Pair<Node, Packet>>()           // (sender, packet it originates)
        queue += origin to packet
        var hops = 0
        while (queue.isNotEmpty()) {
            val (from, p) = queue.removeFirst()
            val route = from.table.lookup(p.dst) ?: continue   // "Network is unreachable" at the sender
            var at = owner(route.via ?: p.dst) ?: continue     // lost: nobody owns the next hop
            var current = p
            while (true) {
                check(++hops < 10_000) { "a packet never died: is the TTL going down?" }
                when (val action = at.handle(current)) {
                    is Forward -> { at = owner(action.nextHop) ?: break; current = action.packet }
                    is Deliver -> {
                        arrivals += Arrival(at, action.packet)
                        answer(at, action.packet)?.let { queue += at to it }
                        break
                    }
                    is Reply -> { queue += at to action.error; break }
                    Drop -> break
                }
            }
        }
        return arrivals
    }

    /** Sends [packet] from [origin] and returns the first packet that comes back to [origin], or null. */
    fun probe(origin: Node, packet: Packet): Packet? =
        send(origin, packet).firstOrNull { it.node === origin }?.packet

    /** How a host answers what it receives: echo requests and UDP to closed ports. */
    private fun answer(host: Node, p: Packet): Packet? = when (val body = p.body) {
        is Echo -> if (body.reply) null else Packet(p.dst, p.src, Icmp.DEFAULT_TTL, p.size, body.copy(reply = true))
        is Udp -> if (!host.sendsIcmpErrors) null else Packet(
            p.dst, p.src, Icmp.DEFAULT_TTL, Icmp.ERROR_SIZE,
            IcmpError(Icmp.DEST_UNREACHABLE, Icmp.PORT_UNREACHABLE, p),   // nothing listens on any port here
        )
        is IcmpError -> null
    }
}
