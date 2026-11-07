package sfz.net.l01

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.net.support.Hex

class DecapsulateTest {
    // both frames come from one real capture of `curl http://example.com/` in the lab box
    private val get = Hex.resource("sfz/net/l01/http-get.txt")
    private val syn = Hex.resource("sfz/net/l01/syn.txt")

    @Test
    fun `Ethernet gives both MAC addresses and the EtherType`() {
        assertThat(get).`as`("the captured frame, as tcpdump printed it").hasSize(140)
        val eth = parseEthernet(get)
        assertThat(eth.dst).isEqualTo("22:d2:d5:a2:32:a3")   // the default gateway, not example.com
        assertThat(eth.src).isEqualTo("b6:99:4a:b0:80:7f")   // the lab box
        assertThat(eth.etherType).isEqualTo(0x0800)
        assertThat(eth.payload).hasSize(126)
        assertThat(eth.payload[0]).isEqualTo(0x45.toByte())
    }

    @Test
    fun `IPv4 gives addresses, lengths, TTL and protocol`() {
        val ip = parseIpv4(parseEthernet(get).payload)
        assertThat(ip.version).isEqualTo(4)
        assertThat(ip.headerLength).isEqualTo(20)
        assertThat(ip.totalLength).isEqualTo(126)
        assertThat(ip.dontFragment).isTrue()
        assertThat(ip.ttl).isEqualTo(64)
        assertThat(ip.protocol).isEqualTo(6)
        assertThat(ip.headerChecksum).isEqualTo(0xcae1)
        assertThat(ip.src).isEqualTo("172.20.0.2")
        assertThat(ip.dst).isEqualTo("104.20.23.154")
        assertThat(ip.payload).hasSize(106)
    }

    @Test
    fun `IPv4 payload ends at the total length, not at the end of the frame`() {
        // Ethernet pads short frames with zeros; those bytes belong to no packet
        val padded = get + ByteArray(6)
        val ip = parseIpv4(parseEthernet(padded).payload)
        assertThat(ip.payload).hasSize(106)
        assertThat(parseTcp(ip.payload).payload).hasSize(74)
    }

    @Test
    fun `IPv4 header length comes from the IHL field`() {
        // the same packet with 4 bytes of options (four NOPs) inserted: IHL 6, total 130
        val original = parseEthernet(get).payload
        val withOptions = original.copyOfRange(0, 20) + byteArrayOf(1, 1, 1, 1) + original.copyOfRange(20, original.size)
        withOptions[0] = 0x46
        withOptions[3] = 130.toByte()
        val ip = parseIpv4(withOptions)
        assertThat(ip.headerLength).isEqualTo(24)
        assertThat(ip.totalLength).isEqualTo(130)
        assertThat(ip.dst).isEqualTo("104.20.23.154")
        assertThat(parseTcp(ip.payload).dstPort).isEqualTo(80)
    }

    @Test
    fun `TCP gives ports and sequence numbers as unsigned values`() {
        val tcp = parseTcp(parseIpv4(parseEthernet(get).payload).payload)
        assertThat(tcp.srcPort).isEqualTo(57236)          // above 32767: a signed short would be negative
        assertThat(tcp.dstPort).isEqualTo(80)
        assertThat(tcp.seq).isEqualTo(3_030_484_348L)      // above 2^31: a signed int would be negative
        assertThat(tcp.ack).isEqualTo(2_979_058_731L)
        assertThat(tcp.window).isEqualTo(502)
        assertThat(tcp.flags).containsExactlyInAnyOrder(TcpFlag.PSH, TcpFlag.ACK)
    }

    @Test
    fun `TCP payload starts after the options`() {
        val tcp = parseTcp(parseIpv4(parseEthernet(get).payload).payload)
        assertThat(tcp.headerLength).isEqualTo(32)         // 20 fixed + 12 of options (two NOPs and a timestamp)
        assertThat(tcp.payload).hasSize(74)
        assertThat(String(tcp.payload, Charsets.US_ASCII)).startsWith("GET / HTTP/1.1\r\nHost: example.com\r\n")
    }

    @Test
    fun `a SYN has options and no payload`() {
        val tcp = parseTcp(parseIpv4(parseEthernet(syn).payload).payload)
        assertThat(tcp.flags).containsExactly(TcpFlag.SYN)
        assertThat(tcp.headerLength).isEqualTo(40)         // mss, sackOK, timestamps, nop, window scale
        assertThat(tcp.seq).isEqualTo(3_030_484_347L)      // one less than the GET: the SYN uses up one number
        assertThat(tcp.ack).isZero()
        assertThat(tcp.payload).isEmpty()
    }

    @Test
    fun `the checksum you compute matches the one the kernel wrote`() {
        val header = parseEthernet(get).payload.copyOfRange(0, 20)
        assertThat(ipv4Checksum(header)).isEqualTo(0xcae1)
        val synHeader = parseEthernet(syn).payload.copyOfRange(0, 20)
        assertThat(ipv4Checksum(synHeader)).isEqualTo(0xcb25)
    }

    @Test
    fun `a router that lowers the TTL must write a new checksum`() {
        val header = parseEthernet(get).payload.copyOfRange(0, 20)
        header[8] = 63                                       // one hop later
        assertThat(ipv4Checksum(header)).isEqualTo(0xcbe1)
    }

    @Test
    fun `decapsulate peels all three headers off the frame`() {
        val layers = decapsulate(get)
        assertThat(layers.ethernet.etherType).isEqualTo(0x0800)
        assertThat(layers.ip.protocol).isEqualTo(6)
        assertThat(layers.tcp.dstPort).isEqualTo(80)
        assertThat(String(layers.application, Charsets.US_ASCII)).endsWith("Accept: */*\r\n\r\n")
    }

    @Test
    fun `decapsulate refuses a frame that is not IPv4`() {
        val arp = get.copyOf().also { it[12] = 0x08; it[13] = 0x06 }   // EtherType 0x0806: ARP
        assertThatThrownBy { decapsulate(arp) }.isInstanceOf(IllegalArgumentException::class.java)
    }

    @Test
    fun `decapsulate refuses a packet that is not TCP`() {
        val udp = get.copyOf().also { it[14 + 9] = 17 }                 // IP protocol 17: UDP
        assertThatThrownBy { decapsulate(udp) }.isInstanceOf(IllegalArgumentException::class.java)
    }
}
