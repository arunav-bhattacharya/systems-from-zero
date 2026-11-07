package sfz.net.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class RouterTest {
    private val router = LabNetwork.router()
    private val router2 = LabNetwork.router2()

    private fun ping(dst: String, ttl: Int = 64, size: Int = 84, src: String = "10.10.1.10") =
        Packet(ip(src), ip(dst), ttl, size, Echo(id = 7, seq = 1))

    @Test
    fun `a router forwards a copy with the TTL one lower, to the next hop of the best route`() {
        val action = router.handle(ping("10.10.4.40", ttl = 64))
        assertThat(action).isEqualTo(Forward(ping("10.10.4.40", ttl = 63), "eth2", ip("10.10.3.3")))
    }

    @Test
    fun `on the last link the next hop is the destination itself`() {
        val action = router2.handle(ping("10.10.4.40", ttl = 63))
        assertThat(action).isEqualTo(Forward(ping("10.10.4.40", ttl = 62), "eth1", ip("10.10.4.40")))
    }

    @Test
    fun `a packet for the router itself is delivered, even with TTL 1`() {
        assertThat(router.handle(ping("10.10.3.2", ttl = 1))).isEqualTo(Deliver(ping("10.10.3.2", ttl = 1)))
    }

    @Test
    fun `TTL 1 may not cross another link, and the sender hears Time Exceeded`() {
        val action = router.handle(ping("10.10.4.40", ttl = 1)) as Reply
        val error = action.error.body as IcmpError
        assertThat(error.type).isEqualTo(Icmp.TIME_EXCEEDED)
        assertThat(error.code).isEqualTo(0)
        assertThat(error.original).`as`("the packet, quoted as it arrived").isEqualTo(ping("10.10.4.40", ttl = 1))
        assertThat(action.error.dst).isEqualTo(ip("10.10.1.10"))
        assertThat(action.error.ttl).isEqualTo(Icmp.DEFAULT_TTL)
    }

    @Test
    fun `an ICMP error comes from the address on the route back to the sender`() {
        val fromRouter = router.handle(ping("10.10.4.40", ttl = 1)) as Reply
        assertThat(Ip.format(fromRouter.error.src)).isEqualTo("10.10.1.2")
        val fromRouter2 = router2.handle(ping("10.10.4.40", ttl = 1)) as Reply
        assertThat(Ip.format(fromRouter2.error.src)).`as`("router2's tunnel side, toward lan").isEqualTo("10.10.3.3")
    }

    @Test
    fun `no route at all means Net Unreachable`() {
        val server = Node("server-as-router", listOf(Interface.of("eth0", "10.10.2.20")), RoutingTable.of("10.10.2.0/24 dev eth0"))
        val action = server.handle(ping("10.10.9.9", src = "10.10.2.2")) as Reply
        val error = action.error.body as IcmpError
        assertThat(error.type to error.code).isEqualTo(Icmp.DEST_UNREACHABLE to Icmp.NET_UNREACHABLE)
    }

    @Test
    fun `too big for the next link means Fragmentation Needed, with that link's MTU`() {
        val action = router.handle(ping("10.10.4.40", size = 1500)) as Reply
        val error = action.error.body as IcmpError
        assertThat(error.type to error.code).isEqualTo(Icmp.DEST_UNREACHABLE to Icmp.FRAG_NEEDED)
        assertThat(error.mtu).isEqualTo(1400)
        assertThat(router.handle(ping("10.10.4.40", size = 1400))).`as`("exactly 1400 fits").isInstanceOf(Forward::class.java)
        assertThat(router.handle(ping("10.10.2.20", size = 1500))).`as`("wan has MTU 1500").isInstanceOf(Forward::class.java)
    }

    @Test
    fun `the TTL check comes before the route lookup`() {
        val action = router.handle(ping("10.10.4.40", ttl = 0, size = 1500)) as Reply
        assertThat((action.error.body as IcmpError).type).isEqualTo(Icmp.TIME_EXCEEDED)
    }

    @Test
    fun `a host drops packets that are not for it`() {
        assertThat(LabNetwork.ledger().handle(ping("10.10.1.20"))).isEqualTo(Drop)
    }

    @Test
    fun `nobody answers an ICMP error with another ICMP error`() {
        val lostError = Packet(ip("10.10.4.40"), ip("10.10.1.10"), 1, Icmp.ERROR_SIZE,
            IcmpError(Icmp.DEST_UNREACHABLE, Icmp.PORT_UNREACHABLE, ping("10.10.4.40")))
        assertThat(router2.handle(lostError)).isEqualTo(Drop)
    }

    @Test
    fun `a router that sends no ICMP errors drops silently`() {
        val silent = LabNetwork.router(sendsIcmpErrors = false)
        assertThat(silent.handle(ping("10.10.4.40", ttl = 1))).isEqualTo(Drop)
        assertThat(silent.handle(ping("10.10.4.40", ttl = 2))).`as`("it still forwards").isInstanceOf(Forward::class.java)
    }
}
