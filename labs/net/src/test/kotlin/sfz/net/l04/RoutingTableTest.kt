package sfz.net.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class RoutingTableTest {
    // client's table after the Try it adds 10.10.0.0/16
    private val client = RoutingTable.of(
        "default via 10.10.1.1 dev eth0",
        "10.10.0.0/16 via 10.10.1.2 dev eth0",
        "10.10.1.0/24 dev eth0",
    )

    @Test
    fun `the most specific matching route wins`() {
        assertThat(client.lookup(ip("10.10.1.20"))?.prefix).`as`("/24 beats /16 and /0").isEqualTo(Prefix.parse("10.10.1.0/24"))
        assertThat(client.lookup(ip("10.10.4.40"))?.prefix).`as`("/16 beats /0").isEqualTo(Prefix.parse("10.10.0.0/16"))
        assertThat(client.lookup(ip("1.1.1.1"))?.prefix).`as`("only the default matches").isEqualTo(Prefix.parse("default"))
    }

    @Test
    fun `an on-link route has no via, a route through a router does`() {
        assertThat(client.lookup(ip("10.10.1.20"))?.via).isNull()
        assertThat(client.lookup(ip("10.10.4.40"))?.via).isEqualTo(ip("10.10.1.2"))
        assertThat(client.lookup(ip("8.8.8.8"))?.via).isEqualTo(ip("10.10.1.1"))
    }

    @Test
    fun `the order of the lines does not matter`() {
        val reversed = RoutingTable(client.routes.reversed())
        for (dst in listOf("10.10.1.20", "10.10.4.40", "1.1.1.1", "10.10.255.255")) {
            assertThat(reversed.lookup(ip(dst))).`as`(dst).isEqualTo(client.lookup(ip(dst)))
        }
    }

    @Test
    fun `a host route beats everything`() {
        val table = RoutingTable(client.routes + Route.parse("10.10.1.20 via 10.10.1.2 dev eth0"))
        assertThat(table.lookup(ip("10.10.1.20"))?.prefix?.length).isEqualTo(32)
        assertThat(table.lookup(ip("10.10.1.21"))?.prefix?.length).isEqualTo(24)
    }

    @Test
    fun `without a default route an unknown destination has no route at all`() {
        val server = RoutingTable.of("10.10.2.0/24 dev eth0")
        assertThat(server.lookup(ip("10.10.2.2"))).isNotNull()
        assertThat(server.lookup(ip("10.10.1.10"))).isNull()
    }

    @Test
    fun `addresses above 128_0_0_0 match too, although they are negative Ints`() {
        val table = RoutingTable.of("default via 10.10.1.1 dev eth0", "192.168.0.0/16 via 10.10.1.2 dev eth0")
        assertThat(table.lookup(ip("192.168.7.1"))?.via).isEqualTo(ip("10.10.1.2"))
        assertThat(table.lookup(ip("200.1.1.1"))?.via).isEqualTo(ip("10.10.1.1"))
    }
}
