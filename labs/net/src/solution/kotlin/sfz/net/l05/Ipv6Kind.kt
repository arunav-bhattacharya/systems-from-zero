package sfz.net.l05

/** What an IPv6 address is for, read from its first bits (RFC 4291, RFC 4193). Checked in this order. */
enum class Ipv6Kind {
    /** `::`, all zeros: "no address yet". A host uses it as the source while it checks a new address. */
    UNSPECIFIED,

    /** `::1`, this host. The IPv6 twin of 127.0.0.1. */
    LOOPBACK,

    /** `::ffff:0:0/96`: an IPv4 address in IPv6 clothing, as a dual-stack socket shows an IPv4 client. */
    IPV4_MAPPED,

    /** `fe80::/10`: link-local, valid on one link only. Every IPv6 interface has one, made by the host itself. */
    LINK_LOCAL,

    /** `fc00::/7` (in practice `fd00::/8`): unique local addresses, IPv6's version of RFC 1918 private space. */
    UNIQUE_LOCAL,

    /** `ff00::/8`: multicast. IPv6 has no broadcast; `ff02::1` (every node on the link) does that job. */
    MULTICAST,

    /** Everything else, for this lab: global unicast, routed on the internet (in practice `2000::/3`). */
    GLOBAL,
}
