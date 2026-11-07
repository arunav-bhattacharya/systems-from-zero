package sfz.net.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.net.support.ManualClock

class NatTableTest {
    private val clock = ManualClock()

    // the router of env/net.yml: lan behind it, its wan address 10.10.2.2 is the "public" one
    private val routerWan = ip("10.10.2.2")
    private val nat = NatTable(routerWan, ports = 40_000..40_002, idleTimeoutMillis = 120_000, clock = clock)

    private val clientToServer = Flow.of("10.10.1.10", 41000, "10.10.2.20", 8080)
    private val peerToServer = Flow.of("10.10.1.20", 41000, "10.10.2.20", 8080)

    /** The server's answer to whatever [out] looked like when it left the router. */
    private fun replyTo(out: Flow) = Flow(out.dstIp, out.dstPort, out.srcIp, out.srcPort)

    @Test
    fun `outbound rewrites the source to the router's address and a port from the range`() {
        val out = nat.outbound(clientToServer)!!
        assertThat(Ipv4.format(out.srcIp)).isEqualTo("10.10.2.2")
        assertThat(out.srcPort).isBetween(40_000, 40_002)
        assertThat(Ipv4.format(out.dstIp)).`as`("destination untouched").isEqualTo("10.10.2.20")
        assertThat(out.dstPort).isEqualTo(8080)
    }

    @Test
    fun `every packet of one connection uses the same public port`() {
        val first = nat.outbound(clientToServer)!!
        clock.advanceSeconds(5)
        assertThat(nat.outbound(clientToServer)).isEqualTo(first)
        assertThat(nat.activeMappings()).isEqualTo(1)
    }

    @Test
    fun `two inside hosts with the same source port get different public ports`() {
        val a = nat.outbound(clientToServer)!!
        val b = nat.outbound(peerToServer)!!
        assertThat(a.srcPort).isNotEqualTo(b.srcPort)
        assertThat(nat.activeMappings()).isEqualTo(2)
    }

    @Test
    fun `a reply is translated back to the inside host that started the connection`() {
        nat.outbound(clientToServer)
        val out = nat.outbound(peerToServer)!!
        val back = nat.inbound(replyTo(out))
        assertThat(back).isEqualTo(Flow.of("10.10.2.20", 8080, "10.10.1.20", 41000))
    }

    @Test
    fun `nothing gets in that nobody inside asked for`() {
        assertThat(nat.inbound(Flow.of("10.10.2.20", 8080, "10.10.2.2", 40_000))).isNull()
        assertThat(nat.inbound(Flow.of("10.10.2.66", 5555, "10.10.2.2", 22))).isNull()
    }

    @Test
    fun `a mapped port only accepts the remote it was opened to`() {
        val out = nat.outbound(clientToServer)!!
        val stranger = Flow.of("10.10.2.66", 8080, "10.10.2.2", out.srcPort)
        assertThat(nat.inbound(stranger)).isNull()
        val otherPortSameHost = Flow.of("10.10.2.20", 9090, "10.10.2.2", out.srcPort)
        assertThat(nat.inbound(otherPortSameHost)).isNull()
        val wrongAddress = Flow(ip("10.10.2.20"), 8080, ip("10.10.2.3"), out.srcPort)
        assertThat(nat.inbound(wrongAddress)).isNull()
    }

    @Test
    fun `an idle mapping expires, its replies are dropped, and its port is reused`() {
        val out = nat.outbound(clientToServer)!!
        clock.advanceSeconds(119)
        assertThat(nat.activeMappings()).isEqualTo(1)
        clock.advanceSeconds(1)
        assertThat(nat.activeMappings()).`as`("120 s idle").isZero()
        assertThat(nat.inbound(replyTo(out))).`as`("the server answers too late").isNull()
        val next = nat.outbound(peerToServer)!!
        assertThat(next.srcPort).`as`("the lowest free port again").isEqualTo(out.srcPort)
    }

    @Test
    fun `traffic in either direction keeps a mapping alive`() {
        val out = nat.outbound(clientToServer)!!
        clock.advanceSeconds(100)
        assertThat(nat.inbound(replyTo(out))).isNotNull()     // the server pushes data
        clock.advanceSeconds(100)
        assertThat(nat.inbound(replyTo(out))).`as`("200 s after the last outbound packet").isNotNull()
    }

    @Test
    fun `a full table drops new connections but keeps the old ones working`() {
        val outs = (1..3).map { n -> nat.outbound(Flow.of("10.10.1.${10 + n}", 50_000, "10.10.2.20", 8080))!! }
        assertThat(outs.map { it.srcPort }).containsExactlyInAnyOrder(40_000, 40_001, 40_002)
        assertThat(nat.outbound(clientToServer)).`as`("no port left").isNull()
        assertThat(nat.inbound(replyTo(outs[1]))).isNotNull()
    }
}
