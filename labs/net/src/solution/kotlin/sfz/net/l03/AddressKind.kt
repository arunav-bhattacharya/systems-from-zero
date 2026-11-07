package sfz.net.l03

/** What kind of IPv4 address something is, which decides whether it can cross the internet. */
enum class AddressKind {
    /** RFC 1918: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16. Yours to use inside; never routed on the internet. */
    PRIVATE,

    /** RFC 6598: 100.64.0.0/10, the shared space a carrier uses behind its own NAT (CGNAT). */
    SHARED,

    /** 127.0.0.0/8: this host. Packets never leave the machine. */
    LOOPBACK,

    /** 169.254.0.0/16: link-local, valid on one link only (cloud metadata lives at 169.254.169.254). */
    LINK_LOCAL,

    /** Everything else, for this lab. Real registries reserve a few more blocks. */
    PUBLIC;

    companion object {
        /** Classifies [addr]. Use [Cidr] blocks rather than comparing octets by hand. */
        private val privateBlocks = listOf("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16").map(Cidr::parse)
        private val shared = Cidr.parse("100.64.0.0/10")
        private val loopback = Cidr.parse("127.0.0.0/8")
        private val linkLocal = Cidr.parse("169.254.0.0/16")

        fun of(addr: Int): AddressKind = when {
            privateBlocks.any { addr in it } -> PRIVATE          // 172.16/12 is 172.16 to 172.31, not all of 172.x
            addr in shared -> SHARED
            addr in loopback -> LOOPBACK
            addr in linkLocal -> LINK_LOCAL
            else -> PUBLIC
        }
    }
}
