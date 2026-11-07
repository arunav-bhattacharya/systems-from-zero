package sfz.net.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.net.support.Hex

/** Real ICMP errors, captured on client in env/net.yml (see the comments in each resource file). */
class IcmpReportTest {
    private fun report(name: String) = IcmpReport.parse(Hex.resource("sfz/net/l04/$name.txt"))

    @Test
    fun `hop 1, Time Exceeded from the router, about the probe to port 33434`() {
        val r = report("time-exceeded-hop1")
        assertThat(Ip.format(r.from)).isEqualTo("10.10.1.2")
        assertThat(r.type to r.code).isEqualTo(11 to 0)
        assertThat(r.probeTtl).isEqualTo(1)
        assertThat(Ip.format(r.probeDst)).isEqualTo("10.10.4.40")
        assertThat(r.probeDstPort).isEqualTo(33434)
        assertThat(r.mtu).isZero()
    }

    @Test
    fun `hop 2, the probe left with TTL 2 and reached router2 with TTL 1`() {
        val r = report("time-exceeded-hop2")
        assertThat(Ip.format(r.from)).isEqualTo("10.10.3.3")
        assertThat(r.type).isEqualTo(Icmp.TIME_EXCEEDED)
        assertThat(r.probeTtl).isEqualTo(1)
        assertThat(r.probeDstPort).isEqualTo(33435)
    }

    @Test
    fun `the destination answers with Port Unreachable`() {
        val r = report("port-unreachable")
        assertThat(Ip.format(r.from)).isEqualTo("10.10.4.40")
        assertThat(r.type to r.code).isEqualTo(Icmp.DEST_UNREACHABLE to Icmp.PORT_UNREACHABLE)
        assertThat(r.probeDstPort).isEqualTo(33436)
    }

    @Test
    fun `Fragmentation Needed carries the next link's MTU and quotes a ping, which has no port`() {
        val r = report("frag-needed")
        assertThat(Ip.format(r.from)).isEqualTo("10.10.1.2")
        assertThat(r.type to r.code).isEqualTo(Icmp.DEST_UNREACHABLE to Icmp.FRAG_NEEDED)
        assertThat(r.mtu).isEqualTo(1400)
        assertThat(Ip.format(r.probeDst)).isEqualTo("10.10.4.40")
        assertThat(r.probeTtl).isEqualTo(64)
        assertThat(r.probeDstPort).isNull()
    }
}
