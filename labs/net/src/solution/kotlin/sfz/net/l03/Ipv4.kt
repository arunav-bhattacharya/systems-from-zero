package sfz.net.l03

/**
 * IPv4 addresses as plain 32-bit numbers, the way the kernel and every router see them.
 * `172.20.0.2` is the Int `0xAC140002`: one byte per dotted part, the first part on top.
 *
 * Kotlin's Int is signed, so every address from 128.0.0.0 up is a negative Int. That is fine for
 * masks and `and`/`or`/`xor`, which only look at bits. It is wrong for `<` and `>`: compare with
 * masks, or convert with [unsigned] first.
 *
 * This file is complete. Your work is in Cidr.kt, AddressKind.kt and NatTable.kt.
 */
object Ipv4 {
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

    /** The address as a non-negative Long, safe for `<` and `>`. */
    fun unsigned(addr: Int): Long = addr.toLong() and 0xffff_ffffL
}

/** Shorthand for tests and the REPL: `ip("10.10.1.10")`. */
fun ip(dotted: String): Int = Ipv4.parse(dotted)
