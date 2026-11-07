package sfz.net.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class MacAddressTest {
    @Test
    fun `Docker's random MACs are locally administered unicast`() {
        val mac = MacAddress.parse("EE:02:07:41:4D:8C")      // client in env/net.yml, as ip link showed it
        assertThat(mac.toString()).isEqualTo("ee:02:07:41:4d:8c")
        assertThat(mac.isLocallyAdministered).`as`("U/L bit of 0xee").isTrue()
        assertThat(mac.isMulticast).`as`("I/G bit of 0xee").isFalse()
        assertThat(mac.isBroadcast).isFalse()
    }

    @Test
    fun `a burned-in vendor MAC is universally administered unicast`() {
        val mac = MacAddress.parse("3c:22:fb:00:00:01")       // 0x3c = 0011 1100: both low bits clear
        assertThat(mac.isLocallyAdministered).isFalse()
        assertThat(mac.isMulticast).isFalse()
    }

    @Test
    fun `IPv4 multicast MACs start with 01-00-5e and are group addresses`() {
        val mdns = MacAddress.parse("01:00:5e:00:00:fb")      // where 224.0.0.251 (mDNS) goes on Ethernet
        assertThat(mdns.isMulticast).isTrue()
        assertThat(mdns.isBroadcast).isFalse()
        assertThat(mdns.isLocallyAdministered).isFalse()
    }

    @Test
    fun `broadcast is the one all-ones address and counts as multicast`() {
        assertThat(MacAddress.BROADCAST.isBroadcast).isTrue()
        assertThat(MacAddress.BROADCAST.isMulticast).isTrue()
        assertThat(MacAddress.parse("ff:ff:ff:ff:ff:fe").isBroadcast).isFalse()
        assertThat(MacAddress.ZERO.isBroadcast).isFalse()
    }
}
