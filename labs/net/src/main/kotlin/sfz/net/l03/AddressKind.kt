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
        fun of(addr: Int): AddressKind {
            TODO("check the blocks listed on each constant; anything else is PUBLIC")
        }
    }
}
