package sfz.net.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.net.support.ManualClock

class ArpCacheTest {
    private val clock = ManualClock()

    // the cache under test belongs to peer, 10.10.1.20, on the lan of env/net.yml
    private val peerMac = MacAddress.parse("4a:9d:40:b1:a5:9e")
    private val cache = ArpCache("10.10.1.20", peerMac, ttlMillis = 30_000, clock = clock)

    private val clientMac = MacAddress.parse("ee:02:07:41:4d:8c")
    private val routerMac = MacAddress.parse("a6:c2:bc:96:ec:aa")
    private val newRouterMac = MacAddress.parse("02:00:00:00:00:99")

    @Test
    fun `a request for my IP gets a reply with my MAC, sent back to the asker`() {
        val reply = cache.receive(ArpPacket.request(clientMac, "10.10.1.10", "10.10.1.20"))
        assertThat(reply).isEqualTo(ArpPacket(ArpPacket.REPLY, peerMac, "10.10.1.20", clientMac, "10.10.1.10"))
    }

    @Test
    fun `the target learns the asker from the request itself`() {
        cache.receive(ArpPacket.request(clientMac, "10.10.1.10", "10.10.1.20"))
        assertThat(cache.lookup("10.10.1.10")).isEqualTo(clientMac)
    }

    @Test
    fun `a request for someone else from a stranger is ignored`() {
        val reply = cache.receive(ArpPacket.request(clientMac, "10.10.1.10", "10.10.1.2"))
        assertThat(reply).isNull()
        assertThat(cache.lookup("10.10.1.10")).`as`("no entry for a host we never talked to").isNull()
    }

    @Test
    fun `a reply to my own request fills the cache and needs no answer`() {
        val reply = cache.receive(ArpPacket(ArpPacket.REPLY, routerMac, "10.10.1.2", peerMac, "10.10.1.20"))
        assertThat(reply).isNull()
        assertThat(cache.lookup("10.10.1.2")).isEqualTo(routerMac)
    }

    @Test
    fun `a known host is updated by any ARP it sends, even one meant for someone else`() {
        cache.receive(ArpPacket(ArpPacket.REPLY, routerMac, "10.10.1.2", peerMac, "10.10.1.20"))
        // the router's IP moves to a new card, which announces itself (a gratuitous ARP: sender IP = target IP)
        val reply = cache.receive(ArpPacket.request(newRouterMac, "10.10.1.2", "10.10.1.2"))
        assertThat(reply).isNull()
        assertThat(cache.lookup("10.10.1.2")).isEqualTo(newRouterMac)
    }

    @Test
    fun `an entry is trusted for the TTL and not a millisecond longer`() {
        cache.receive(ArpPacket(ArpPacket.REPLY, routerMac, "10.10.1.2", peerMac, "10.10.1.20"))
        clock.advance(29_999)
        assertThat(cache.lookup("10.10.1.2")).isEqualTo(routerMac)
        clock.advance(1)
        assertThat(cache.lookup("10.10.1.2")).`as`("30 s old: ask again").isNull()
    }

    @Test
    fun `hearing from a host again restarts its timer`() {
        cache.receive(ArpPacket(ArpPacket.REPLY, routerMac, "10.10.1.2", peerMac, "10.10.1.20"))
        clock.advanceSeconds(20)
        cache.receive(ArpPacket.request(routerMac, "10.10.1.2", "10.10.1.20"))
        clock.advanceSeconds(20)
        assertThat(cache.lookup("10.10.1.2")).isEqualTo(routerMac)
    }

    @Test
    fun `an old entry is still in the table, so its host's broadcasts refresh it`() {
        cache.receive(ArpPacket(ArpPacket.REPLY, routerMac, "10.10.1.2", peerMac, "10.10.1.20"))
        clock.advanceSeconds(45)
        assertThat(cache.lookup("10.10.1.2")).isNull()
        // the router asks the lan about someone else; we are not the target, but we know the router
        cache.receive(ArpPacket.request(routerMac, "10.10.1.2", "10.10.1.10"))
        assertThat(cache.lookup("10.10.1.2")).isEqualTo(routerMac)
    }
}
