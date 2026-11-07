package sfz.net.l02

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.net.support.Hex

class ArpPacketTest {
    // two real frames from env/net.yml: client asks for peer, peer answers
    private val requestFrame = Hex.resource("sfz/net/l02/arp-request.txt")
    private val replyFrame = Hex.resource("sfz/net/l02/arp-reply.txt")

    private val client = MacAddress.parse("ee:02:07:41:4d:8c")
    private val peer = MacAddress.parse("4a:9d:40:b1:a5:9e")

    // the ARP packet starts after the 14-byte Ethernet header
    private fun arpOf(frame: ByteArray) = frame.copyOfRange(14, frame.size)

    @Test
    fun `the request goes to the broadcast MAC and asks who has peer's IP`() {
        assertThat(MacAddress.of(requestFrame, 0).isBroadcast).`as`("Ethernet destination").isTrue()
        val arp = ArpPacket.decode(arpOf(requestFrame))
        assertThat(arp.op).isEqualTo(ArpPacket.REQUEST)
        assertThat(arp.senderMac).isEqualTo(client)
        assertThat(arp.senderIp).isEqualTo("10.10.1.10")
        assertThat(arp.targetMac).`as`("unknown yet, so all zeros").isEqualTo(MacAddress.ZERO)
        assertThat(arp.targetIp).isEqualTo("10.10.1.20")
    }

    @Test
    fun `the reply comes straight back to the asker with the answer in the sender fields`() {
        assertThat(MacAddress.of(replyFrame, 0)).`as`("Ethernet destination").isEqualTo(client)
        val arp = ArpPacket.decode(arpOf(replyFrame))
        assertThat(arp.op).isEqualTo(ArpPacket.REPLY)
        assertThat(arp.senderMac).isEqualTo(peer)
        assertThat(arp.senderIp).isEqualTo("10.10.1.20")
        assertThat(arp.targetMac).isEqualTo(client)
        assertThat(arp.targetIp).isEqualTo("10.10.1.10")
    }

    @Test
    fun `decode reads back exactly what encode wrote`() {
        val who = ArpCache("10.10.1.10", client).requestFor("10.10.1.2")
        assertThat(ArpPacket.decode(who.encode())).isEqualTo(who)
        val answer = ArpPacket(ArpPacket.REPLY, peer, "10.10.1.20", client, "10.10.1.10")
        assertThat(ArpPacket.decode(answer.encode())).isEqualTo(answer)
        assertThat(answer.encode()).isEqualTo(arpOf(replyFrame))
    }

    @Test
    fun `decode refuses ARP for anything but Ethernet and IPv4`() {
        val notEthernet = arpOf(requestFrame).also { it[1] = 6 }      // hardware type 6: IEEE 802
        assertThatThrownBy { ArpPacket.decode(notEthernet) }.isInstanceOf(IllegalArgumentException::class.java)
        val notIpv4 = arpOf(requestFrame).also { it[2] = 0x86.toByte(); it[3] = 0xdd.toByte() }
        assertThatThrownBy { ArpPacket.decode(notIpv4) }.isInstanceOf(IllegalArgumentException::class.java)
    }
}
