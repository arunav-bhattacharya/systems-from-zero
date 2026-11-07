package sfz.net.l04

/**
 * The hosts and routers of env/net.yml that lesson 4 uses, with the routes the Try its end up with:
 *
 *   client 10.10.1.10 -- lan -- router -- tunnel (MTU 1400) -- router2 -- dc -- ledger 10.10.4.40
 *                                  |
 *                                 wan -- server 10.10.2.20
 *
 * Docker's own gateway on lan (10.10.1.1) is here too, because a packet with no better route ends up
 * there. It sends its traffic on to the internet, which this network doesn't have, so it is lost.
 */
object LabNetwork {
    fun client() = Node(
        "client", listOf(Interface.of("eth0", "10.10.1.10")),
        RoutingTable.of(
            "default via 10.10.1.1 dev eth0",
            "10.10.0.0/16 via 10.10.1.2 dev eth0",
            "10.10.1.0/24 dev eth0",
            "10.10.2.0/24 via 10.10.1.2 dev eth0",
        ),
        forwarding = false,
    )

    /** [knowsDc] false is the router as compose starts it: no route to 10.10.4.0/24 yet. */
    fun router(knowsDc: Boolean = true, sendsIcmpErrors: Boolean = true) = Node(
        "router",
        listOf(Interface.of("eth0", "10.10.1.2"), Interface.of("eth1", "10.10.2.2"), Interface.of("eth2", "10.10.3.2", mtu = 1400)),
        RoutingTable.of(
            *listOfNotNull(
                "default via 10.10.1.1 dev eth0",
                "10.10.1.0/24 dev eth0",
                "10.10.2.0/24 dev eth1",
                "10.10.3.0/24 dev eth2",
                if (knowsDc) "10.10.4.0/24 via 10.10.3.3 dev eth2" else null,
            ).toTypedArray(),
        ),
        sendsIcmpErrors = sendsIcmpErrors,
    )

    fun router2(sendsIcmpErrors: Boolean = true) = Node(
        "router2",
        listOf(Interface.of("eth0", "10.10.3.3", mtu = 1400), Interface.of("eth1", "10.10.4.3")),
        RoutingTable.of(
            "default via 10.10.4.1 dev eth1",
            "10.10.1.0/24 via 10.10.3.2 dev eth0",
            "10.10.3.0/24 dev eth0",
            "10.10.4.0/24 dev eth1",
        ),
        sendsIcmpErrors = sendsIcmpErrors,
    )

    fun ledger() = Node(
        "ledger", listOf(Interface.of("eth0", "10.10.4.40")),
        RoutingTable.of("default via 10.10.4.3 dev eth0", "10.10.4.0/24 dev eth0"),
        forwarding = false,
    )

    /** [routeBack] false is the server as compose starts it: no default route, nothing for lan. */
    fun server(routeBack: Boolean = false) = Node(
        "server", listOf(Interface.of("eth0", "10.10.2.20")),
        RoutingTable.of(*listOfNotNull("10.10.2.0/24 dev eth0", if (routeBack) "10.10.1.0/24 via 10.10.2.2 dev eth0" else null).toTypedArray()),
        forwarding = false,
    )

    fun dockerGateway() = Node(
        "docker", listOf(Interface.of("eth0", "10.10.1.1")),
        RoutingTable.of("default via 192.168.65.1 dev eth0", "10.10.1.0/24 dev eth0"),
    )

    fun build(router: Node = router(), router2: Node = router2(), server: Node = server()) =
        Network(listOf(client(), router, router2, ledger(), server, dockerGateway()))
}
