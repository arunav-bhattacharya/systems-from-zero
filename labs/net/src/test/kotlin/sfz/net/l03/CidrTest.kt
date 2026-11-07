package sfz.net.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class CidrTest {
    private fun dotted(addr: Int) = Ipv4.format(addr)

    @Test
    fun `a slash-24 has a 255-255-255-0 mask, a broadcast at dot 255 and 256 addresses`() {
        val lan = Cidr.parse("10.10.1.0/24")
        assertThat(dotted(lan.mask)).isEqualTo("255.255.255.0")
        assertThat(dotted(lan.network)).isEqualTo("10.10.1.0")
        assertThat(dotted(lan.broadcast)).isEqualTo("10.10.1.255")
        assertThat(lan.size).isEqualTo(256)
    }

    @Test
    fun `parse clears the host bits of an interface address`() {
        // what `ip addr` printed for the lab box's eth0
        val box = Cidr.parse("172.20.0.2/16")
        assertThat(box.toString()).isEqualTo("172.20.0.0/16")
        assertThat(dotted(box.broadcast)).isEqualTo("172.20.255.255")
        assertThat(box.size).isEqualTo(65_536)
    }

    @Test
    fun `a prefix that does not end on a dot still works bit by bit`() {
        val block = Cidr.parse("10.42.17.130/26")
        assertThat(dotted(block.mask)).isEqualTo("255.255.255.192")
        assertThat(dotted(block.network)).isEqualTo("10.42.17.128")
        assertThat(dotted(block.broadcast)).isEqualTo("10.42.17.191")
        assertThat(block.size).isEqualTo(64)
        assertThat(ip("10.42.17.190") in block).isTrue()
        assertThat(ip("10.42.17.200") in block).isFalse()
    }

    @Test
    fun `contains compares network bits, so the third octet can differ inside a slash-16`() {
        val box = Cidr.parse("172.20.0.0/16")
        assertThat(ip("172.20.200.9") in box).isTrue()
        assertThat(ip("172.21.0.1") in box).isFalse()
    }

    @Test
    fun `contains works for addresses that are negative as an Int`() {
        val home = Cidr.parse("192.168.0.0/16")              // 0xC0A80000 is a negative Int
        assertThat(ip("192.168.1.23") in home).isTrue()
        assertThat(ip("192.169.0.1") in home).isFalse()
        assertThat(ip("10.0.0.1") in home).isFalse()
        val top = Cidr.parse("128.0.0.0/1")
        assertThat(ip("255.255.255.255") in top).isTrue()
        assertThat(ip("127.255.255.255") in top).isFalse()
    }

    @Test
    fun `slash-0 is every address, which is what a default route means`() {
        val all = Cidr.parse("0.0.0.0/0")
        assertThat(all.mask).isZero()
        assertThat(all.size).isEqualTo(4_294_967_296L)
        assertThat(ip("8.8.8.8") in all).isTrue()
        assertThat(ip("255.255.255.255") in all).isTrue()
        assertThat(dotted(all.broadcast)).isEqualTo("255.255.255.255")
    }

    @Test
    fun `slash-32 is one host and slash-31 is a two-address link`() {
        val one = Cidr.parse("10.10.2.20/32")
        assertThat(one.size).isEqualTo(1)
        assertThat(dotted(one.mask)).isEqualTo("255.255.255.255")
        assertThat(ip("10.10.2.20") in one).isTrue()
        assertThat(ip("10.10.2.21") in one).isFalse()
        assertThat(Cidr.parse("10.0.0.0/31").size).isEqualTo(2)
    }

    @Test
    fun `private, shared and special blocks are told apart`() {
        assertThat(AddressKind.of(ip("10.10.1.10"))).isEqualTo(AddressKind.PRIVATE)
        assertThat(AddressKind.of(ip("172.20.0.2"))).isEqualTo(AddressKind.PRIVATE)
        assertThat(AddressKind.of(ip("172.31.255.255"))).isEqualTo(AddressKind.PRIVATE)
        assertThat(AddressKind.of(ip("172.32.0.1"))).`as`("172.16.0.0/12 stops at 172.31").isEqualTo(AddressKind.PUBLIC)
        assertThat(AddressKind.of(ip("192.168.1.23"))).isEqualTo(AddressKind.PRIVATE)
        assertThat(AddressKind.of(ip("100.64.0.1"))).isEqualTo(AddressKind.SHARED)
        assertThat(AddressKind.of(ip("100.127.255.254"))).isEqualTo(AddressKind.SHARED)
        assertThat(AddressKind.of(ip("100.128.0.1"))).isEqualTo(AddressKind.PUBLIC)
        assertThat(AddressKind.of(ip("127.0.0.1"))).isEqualTo(AddressKind.LOOPBACK)
        assertThat(AddressKind.of(ip("169.254.169.254"))).isEqualTo(AddressKind.LINK_LOCAL)
        assertThat(AddressKind.of(ip("104.20.23.154"))).isEqualTo(AddressKind.PUBLIC)   // example.com, lesson 1
    }
}
