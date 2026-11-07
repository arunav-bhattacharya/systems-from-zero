package sfz.net.l05

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.net.support.Hex
import java.net.InetAddress

class Ipv6Test {
    private fun canonical(text: String) = Ipv6.parse(text).format()

    @Test
    fun `parse fills the gap that double colon stands for`() {
        assertThat(Ipv6.parse("fd00:10:6::20").exploded()).isEqualTo("fd00:0010:0006:0000:0000:0000:0000:0020")
        assertThat(Ipv6.parse("::1").groups).containsExactly(0, 0, 0, 0, 0, 0, 0, 1)
        assertThat(Ipv6.parse("::").groups).containsOnly(0)
        assertThat(Ipv6.parse("1::").groups).containsExactly(1, 0, 0, 0, 0, 0, 0, 0)
        assertThat(Ipv6.parse("2001:db8:0:0:1:0:0:1").groups).containsExactly(0x2001, 0xdb8, 0, 0, 1, 0, 0, 1)
    }

    @Test
    fun `parse reads upper case, leading zeros and a dotted IPv4 tail`() {
        assertThat(Ipv6.parse("FD00:0010:0006:0000:0000:0000:0000:0020")).isEqualTo(Ipv6.parse("fd00:10:6::20"))
        assertThat(Ipv6.parse("::ffff:10.10.6.10").groups).containsExactly(0, 0, 0, 0, 0, 0xffff, 0x0a0a, 0x060a)
    }

    @Test
    fun `parse rejects what is not an IPv6 address`() {
        for (bad in listOf("", ":::", "1::2::3", "12345::", "1:2:3:4:5:6:7:8:9", "1:2:3:4:5:6:7", "g::1", "1:2:3:4:5:6:7::8", "fe80::1%eth0", "::ffff:10.10.6.256")) {
            assertThatThrownBy { Ipv6.parse(bad) }.`as`(bad).isInstanceOf(IllegalArgumentException::class.java)
        }
    }

    @Test
    fun `format drops leading zeros and squeezes the longest zero run`() {
        assertThat(canonical("2001:db8:0:0:0:0:2:1")).isEqualTo("2001:db8::2:1")
        assertThat(canonical("fe80:0000:0000:0000:10fc:01ff:fe3b:eb52")).isEqualTo("fe80::10fc:1ff:fe3b:eb52")
        assertThat(canonical("2001:0:0:1:0:0:0:1")).`as`("the run of three wins").isEqualTo("2001:0:0:1::1")
        assertThat(canonical("::")).isEqualTo("::")
        assertThat(canonical("1:0:0:0:0:0:0:0")).isEqualTo("1::")
    }

    @Test
    fun `format never uses double colon for a single zero group`() {
        assertThat(canonical("2001:db8:0:1:1:1:1:1")).isEqualTo("2001:db8:0:1:1:1:1:1")
    }

    @Test
    fun `when two zero runs tie, the first one is shortened`() {
        assertThat(canonical("2001:db8:0:0:1:0:0:1")).isEqualTo("2001:db8::1:0:0:1")
    }

    @Test
    fun `format is lower case`() {
        assertThat(canonical("2001:DB8::ABCD")).isEqualTo("2001:db8::abcd")
    }

    @Test
    fun `an IPv4-mapped address ends in dotted IPv4`() {
        assertThat(canonical("0:0:0:0:0:ffff:a0a:60a")).isEqualTo("::ffff:10.10.6.10")
    }

    @Test
    fun `the JVM's long form becomes the form ip addr and your logs should show`() {
        // getHostAddress() prints every group: "fd00:10:6:0:0:0:0:20" and "0:0:0:0:0:0:0:1"
        val jvm = InetAddress.getByName("fd00:10:6::20").hostAddress
        assertThat(jvm).isEqualTo("fd00:10:6:0:0:0:0:20")
        assertThat(canonical(jvm)).isEqualTo("fd00:10:6::20")
        assertThat(canonical(InetAddress.getByName("::1").hostAddress)).isEqualTo("::1")
    }

    @Test
    fun `the first bits say what an address is for`() {
        assertThat(Ipv6.parse("::").kind).isEqualTo(Ipv6Kind.UNSPECIFIED)
        assertThat(Ipv6.parse("::1").kind).isEqualTo(Ipv6Kind.LOOPBACK)
        assertThat(Ipv6.parse("::ffff:10.10.6.10").kind).isEqualTo(Ipv6Kind.IPV4_MAPPED)
        assertThat(Ipv6.parse("fe80::10fc:1ff:fe3b:eb52").kind).isEqualTo(Ipv6Kind.LINK_LOCAL)
        assertThat(Ipv6.parse("febf::1").kind).`as`("fe80::/10 runs up to febf").isEqualTo(Ipv6Kind.LINK_LOCAL)
        assertThat(Ipv6.parse("fd00:10:6::10").kind).isEqualTo(Ipv6Kind.UNIQUE_LOCAL)
        assertThat(Ipv6.parse("fc00::1").kind).isEqualTo(Ipv6Kind.UNIQUE_LOCAL)
        assertThat(Ipv6.parse("ff02::1").kind).isEqualTo(Ipv6Kind.MULTICAST)
        assertThat(Ipv6.parse("2001:db8:6::1").kind).isEqualTo(Ipv6Kind.GLOBAL)
        assertThat(Ipv6.parse("::2").kind).isEqualTo(Ipv6Kind.GLOBAL)
    }

    @Test
    fun `a host builds its link-local address from its MAC`() {
        // app and api in env/net.yml: ip -br link and ip -6 addr agreed on these
        assertThat(Ipv6.fromMac(Ipv6.parse("fe80::"), "12:fc:01:3b:eb:52").format()).isEqualTo("fe80::10fc:1ff:fe3b:eb52")
        assertThat(Ipv6.fromMac(Ipv6.parse("fe80::"), "ea:cd:e9:43:37:ae").format()).isEqualTo("fe80::e8cd:e9ff:fe43:37ae")
        assertThat(Ipv6.fromMac(Ipv6.parse("fe80::"), "00:1b:21:3a:4f:5c").format()).`as`("a vendor MAC: U/L 0 becomes 1").isEqualTo("fe80::21b:21ff:fe3a:4f5c")
    }

    @Test
    fun `SLAAC puts the same interface ID behind the router's prefix`() {
        val prefix = Ipv6.parse("2001:db8:6::")
        assertThat(Ipv6.fromMac(prefix, "12:fc:01:3b:eb:52").format()).isEqualTo("2001:db8:6:0:10fc:1ff:fe3b:eb52")
    }

    @Test
    fun `a real neighbor solicitation goes to the target's solicited-node address`() {
        val frame = Hex.resource("sfz/net/l05/neighbor-solicitation.txt")
        val src = Ipv6.fromBytes(frame.copyOfRange(22, 38))
        val dst = Ipv6.fromBytes(frame.copyOfRange(38, 54))
        val target = Ipv6.fromBytes(frame.copyOfRange(62, 78))
        assertThat(src.format()).isEqualTo("fd00:10:6::10")
        assertThat(target.format()).isEqualTo("fd00:10:6::20")
        assertThat(dst.format()).isEqualTo("ff02::1:ff00:20")
        assertThat(target.solicitedNode()).isEqualTo(dst)
        assertThat(dst.kind).isEqualTo(Ipv6Kind.MULTICAST)
        // the Ethernet destination is 33:33 plus the low 32 bits of that multicast address
        assertThat(Hex.format(frame.copyOfRange(0, 6))).isEqualTo("3333" + Hex.format(dst.toBytes().copyOfRange(12, 16)))
    }

    @Test
    fun `the DAD probe for a SLAAC address goes to its own solicited-node group`() {
        val slaac = Ipv6.parse("2001:db8:6:0:10fc:1ff:fe3b:eb52")
        assertThat(slaac.solicitedNode().format()).isEqualTo("ff02::1:ff3b:eb52")
    }
}
