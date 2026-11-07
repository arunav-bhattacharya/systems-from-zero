package sfz.net.l04

/**
 * IPv4 addresses as 32-bit Ints, and prefixes such as `10.10.0.0/16`. Lesson 3 of this track had you
 * build both; here they are finished so this lab can be about routing.
 *
 * This file is complete. Your work is in RoutingTable.kt, Router.kt, Traceroute.kt and IcmpReport.kt.
 */
object Ip {
    /** `"10.10.1.10"` to `0x0A0A010A`. */
    fun parse(dotted: String): Int {
        val parts = dotted.trim().split('.')
        require(parts.size == 4) { "not an IPv4 address: $dotted" }
        return parts.fold(0) { acc, p ->
            val octet = p.toIntOrNull() ?: throw IllegalArgumentException("not an IPv4 address: $dotted")
            require(octet in 0..255) { "not an IPv4 address: $dotted" }
            (acc shl 8) or octet
        }
    }

    /** `0x0A0A010A` to `"10.10.1.10"`. */
    fun format(addr: Int): String =
        listOf(24, 16, 8, 0).joinToString(".") { shift -> ((addr ushr shift) and 0xff).toString() }
}

/** Shorthand for tests: `ip("10.10.1.10")`. */
fun ip(dotted: String): Int = Ip.parse(dotted)

/** A block of addresses: the first [length] bits of [network] name it. `default` is `0.0.0.0/0`. */
data class Prefix(val network: Int, val length: Int) {
    init {
        require(length in 0..32) { "prefix length must be 0 to 32, got $length" }
    }

    /** [length] one-bits from the top. A /0 is 0: the JVM masks shift counts to 5 bits, so `-1 shl 32` is -1. */
    val mask: Int get() = if (length == 0) 0 else -1 shl (32 - length)

    /** True when [addr] starts with the same [length] bits as [network]. */
    operator fun contains(addr: Int): Boolean = addr and mask == network

    override fun toString(): String = if (length == 0) "default" else "${Ip.format(network)}/$length"

    companion object {
        /** `"10.10.0.0/16"`, `"10.10.1.2"` (a /32) or `"default"`. Host bits are cleared. */
        fun parse(text: String): Prefix {
            val t = text.trim()
            if (t == "default") return Prefix(0, 0)
            val parts = t.split('/')
            val length = if (parts.size == 2) parts[1].toInt() else 32
            val p = Prefix(0, length)
            return Prefix(Ip.parse(parts[0]) and p.mask, length)
        }
    }
}
