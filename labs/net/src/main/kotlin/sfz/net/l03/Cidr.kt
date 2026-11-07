package sfz.net.l03

/**
 * A CIDR block such as `10.10.1.0/24`: the first [prefixLength] bits name the network,
 * the remaining `32 - prefixLength` bits name a host inside it.
 *
 * [network] always has its host bits cleared, so `Cidr.parse("172.20.0.2/16")` is `172.20.0.0/16`,
 * the same block `ip addr` means when it prints `172.20.0.2/16` for an interface.
 */
data class Cidr(val network: Int, val prefixLength: Int) {
    init {
        require(prefixLength in 0..32) { "prefix length must be 0 to 32, got $prefixLength" }
    }

    /** The netmask: [prefixLength] one-bits followed by zeros. /24 is 255.255.255.0. */
    val mask: Int get() = maskOf(prefixLength)

    /** The last address in the block, all host bits set. For a LAN this is the broadcast address. */
    val broadcast: Int
        get() = TODO("set every host bit of network")

    /** How many addresses the block holds, the network and broadcast addresses included. */
    val size: Long
        get() = TODO("2 to the power of the host bits; a /0 holds 4,294,967,296")

    /** True when [addr] is inside this block: its network bits equal [network]. */
    operator fun contains(addr: Int): Boolean {
        TODO("compare with the mask; do not compare with < and > on signed Ints")
    }

    override fun toString(): String = "${Ipv4.format(network)}/$prefixLength"

    companion object {
        /**
         * The mask for a prefix length. Careful at /0: on the JVM a shift by 32 is a shift by 0,
         * so `-1 shl 32` is still -1 (all ones), not 0.
         */
        fun maskOf(prefixLength: Int): Int {
            TODO("prefixLength one-bits from the top; handle 0 on its own")
        }

        /** Reads `"10.10.1.0/24"` or an interface address like `"172.20.0.2/16"` (host bits are cleared). */
        fun parse(text: String): Cidr {
            TODO("split on '/', parse both parts, clear the host bits with the mask")
        }
    }
}
