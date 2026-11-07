package sfz.net.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class TracerouteTest {
    private val client = ip("10.10.1.10")

    private fun trace(net: Network, to: String, maxHops: Int = 30): List<String?> {
        val origin = net.node("client")
        return traceroute(client, ip(to), maxHops) { net.probe(origin, it) }.map { it.from?.let(Ip::format) }
    }

    @Test
    fun `each TTL dies one router further, then the destination answers`() {
        val net = LabNetwork.build()
        val hops = traceroute(client, ip("10.10.4.40")) { net.probe(net.node("client"), it) }
        assertThat(hops.map { it.from?.let(Ip::format) }).containsExactly("10.10.1.2", "10.10.3.3", "10.10.4.40")
        assertThat(hops.map { it.icmpType }).containsExactly(Icmp.TIME_EXCEEDED, Icmp.TIME_EXCEEDED, Icmp.DEST_UNREACHABLE)
        assertThat(hops.last().reached).isTrue()
        assertThat(hops.map { it.ttl }).containsExactly(1, 2, 3)
    }

    @Test
    fun `probes use port 33434 and up, one port per TTL`() {
        val net = LabNetwork.build()
        val sent = mutableListOf<Packet>()
        traceroute(client, ip("10.10.4.40")) { p -> sent += p; net.probe(net.node("client"), p) }
        assertThat(sent.map { it.ttl }).containsExactly(1, 2, 3)
        assertThat(sent.map { (it.body as Udp).dstPort }).containsExactly(33434, 33435, 33436)
        assertThat(sent.map { it.src }.distinct()).containsExactly(client)
    }

    @Test
    fun `a missing route on the router sends the probes to Docker's gateway, and then nowhere`() {
        val net = LabNetwork.build(router = LabNetwork.router(knowsDc = false))
        assertThat(trace(net, "10.10.4.40", maxHops = 5)).containsExactly("10.10.1.2", "10.10.1.1", null, null, null)
    }

    @Test
    fun `a router that sends no ICMP shows as a star, and the trace still gets through`() {
        val net = LabNetwork.build(router2 = LabNetwork.router2(sendsIcmpErrors = false))
        assertThat(trace(net, "10.10.4.40")).containsExactly("10.10.1.2", null, "10.10.4.40")
    }

    @Test
    fun `a destination with no route back looks exactly like a dead one`() {
        assertThat(trace(LabNetwork.build(), "10.10.2.20", maxHops = 4)).containsExactly("10.10.1.2", null, null, null)
        assertThat(trace(LabNetwork.build(server = LabNetwork.server(routeBack = true)), "10.10.2.20")).containsExactly("10.10.1.2", "10.10.2.20")
    }

    @Test
    fun `an answer about some other probe does not count`() {
        // every "answer" quotes the probe for port 40000: a late reply from an earlier trace
        val stale = Packet(ip("10.10.1.2"), client, 64, Icmp.ERROR_SIZE,
            IcmpError(Icmp.TIME_EXCEEDED, 0, Packet(client, ip("10.10.4.40"), 1, 60, Udp(40_000, 40_000))))
        val hops = traceroute(client, ip("10.10.4.40"), maxHops = 3) { stale }
        assertThat(hops.map { it.from }).containsExactly(null, null, null)
    }

    @Test
    fun `an unreachable network ends the trace`() {
        val lonely = Node("router", listOf(Interface.of("eth0", "10.10.1.2")), RoutingTable.of("10.10.1.0/24 dev eth0"))
        val net = Network(listOf(LabNetwork.client(), lonely))
        val hops = traceroute(client, ip("10.10.4.40")) { net.probe(net.node("client"), it) }
        assertThat(hops).hasSize(2)
        assertThat(hops[1].icmpCode).isEqualTo(Icmp.NET_UNREACHABLE)
        assertThat(hops[1].reached).isFalse()
    }
}
