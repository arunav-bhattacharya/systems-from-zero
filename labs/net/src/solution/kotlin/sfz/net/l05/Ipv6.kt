package sfz.net.l05

/**
 * An IPv6 address: 128 bits, held as eight 16-bit groups, the way the text form writes them.
 * `fd00:10:6::20` is the groups `fd00 0010 0006 0000 0000 0000 0000 0020`.
 */
data class Ipv6(val groups: List<Int>) {
    init {
        require(groups.size == 8) { "an IPv6 address has 8 groups, got ${groups.size}" }
        require(groups.all { it in 0..0xffff }) { "every group is 16 bits: $groups" }
    }

    /** The 16 bytes, high byte of each group first, as they sit in a packet header. */
    fun toBytes(): ByteArray = ByteArray(16) { i -> (groups[i / 2] shr (if (i % 2 == 0) 8 else 0)).toByte() }

    /** Every group in full, 4 hex digits each: `fd00:0010:0006:0000:0000:0000:0000:0020`. */
    fun exploded(): String = groups.joinToString(":") { "%04x".format(it) }

    override fun toString(): String = format()

    /**
     * The one canonical text form, RFC 5952, so that the same address always prints the same way:
     *
     * 1. Lower-case hex, and no leading zeros in a group (`0010` is `10`, `0000` is `0`).
     * 2. The longest run of two or more all-zero groups becomes `::`. A single zero group stays `0`.
     *    When two runs are equally long, shorten the first one.
     * 3. An IPv4-mapped address ([Ipv6Kind.IPV4_MAPPED]) ends in dotted IPv4: `::ffff:10.10.6.10`.
     */
    fun format(): String {
        if (kind == Ipv6Kind.IPV4_MAPPED) {
            val v4 = listOf(groups[6] shr 8, groups[6] and 0xff, groups[7] shr 8, groups[7] and 0xff)
            return "::ffff:" + v4.joinToString(".")
        }
        // find the longest run of zero groups; a later run must be strictly longer to win
        var bestStart = -1
        var bestLen = 0
        var i = 0
        while (i < 8) {
            if (groups[i] != 0) { i++; continue }
            val start = i
            while (i < 8 && groups[i] == 0) i++
            if (i - start > bestLen) { bestStart = start; bestLen = i - start }
        }
        val hex = groups.map { it.toString(16) }                  // lower case, no leading zeros
        if (bestLen < 2) return hex.joinToString(":")              // never :: for a single zero group
        val left = hex.subList(0, bestStart).joinToString(":")
        val right = hex.subList(bestStart + bestLen, 8).joinToString(":")
        return "$left::$right"                                     // "::1", "fe80::...", "1::" all fall out
    }

    /** What this address is for, from its first bits. The checks on [Ipv6Kind] say which bits. */
    val kind: Ipv6Kind
        get() = when {
            groups.all { it == 0 } -> Ipv6Kind.UNSPECIFIED
            groups.take(7).all { it == 0 } && groups[7] == 1 -> Ipv6Kind.LOOPBACK
            groups.take(5).all { it == 0 } && groups[5] == 0xffff -> Ipv6Kind.IPV4_MAPPED
            groups[0] and 0xffc0 == 0xfe80 -> Ipv6Kind.LINK_LOCAL    // first 10 bits 1111 1110 10
            groups[0] and 0xfe00 == 0xfc00 -> Ipv6Kind.UNIQUE_LOCAL  // first 7 bits 1111 110
            groups[0] and 0xff00 == 0xff00 -> Ipv6Kind.MULTICAST     // first 8 bits all ones
            else -> Ipv6Kind.GLOBAL
        }

    /**
     * The solicited-node multicast address a host joins for this address: `ff02::1:ff` followed by the
     * low 24 bits of this address. IPv6 neighbor discovery sends "who has X?" there instead of to every
     * card on the link, so in practice only X's owner wakes up. `fd00:10:6::20` gives `ff02::1:ff00:20`.
     */
    fun solicitedNode(): Ipv6 =
        Ipv6(listOf(0xff02, 0, 0, 0, 0, 1, 0xff00 or (groups[6] and 0xff), groups[7]))

    companion object {
        /**
         * Reads any valid text form: `fd00:10:6::20`, `FD00:0010:0006:0000:0000:0000:0000:0020`,
         * `0:0:0:0:0:0:0:1` (how the JVM prints `::1`), `::`, `::ffff:10.10.6.10`.
         *
         * `::` stands for as many zero groups as it takes to make 8, and may appear only once. Each group
         * is 1 to 4 hex digits. The last 32 bits may be written as dotted IPv4. Throw
         * IllegalArgumentException for anything else, including a zone ID such as `%eth0` (it names a
         * network card, it is not part of the address).
         */
        fun parse(text: String): Ipv6 {
            val t = text.trim()
            require('%' !in t) { "a zone ID is not part of the address: $text" }
            val halves = t.split("::")
            require(halves.size <= 2) { ":: may appear only once: $text" }
            val left = groupsOf(halves[0], text)
            val right = if (halves.size == 2) groupsOf(halves[1], text) else emptyList()
            val missing = 8 - left.size - right.size
            if (halves.size == 2) require(missing >= 1) { "too many groups around ::: $text" }
            else require(missing == 0) { "an address without :: needs 8 groups: $text" }
            return Ipv6(left + List(missing) { 0 } + right)        // :: is the gap, filled with zeros
        }

        // "fd00:10:6" -> [0xfd00, 0x10, 0x6]; a dotted tail "10.10.6.10" counts as two groups
        private fun groupsOf(part: String, text: String): List<Int> {
            if (part.isEmpty()) return emptyList()
            val pieces = part.split(':')
            val out = mutableListOf<Int>()
            for ((i, p) in pieces.withIndex()) {
                if ('.' in p && i == pieces.lastIndex) {
                    val octets = p.split('.').map { it.toIntOrNull() ?: -1 }
                    require(octets.size == 4 && octets.all { it in 0..255 }) { "bad IPv4 tail in: $text" }
                    out += (octets[0] shl 8) or octets[1]
                    out += (octets[2] shl 8) or octets[3]
                } else {
                    require(p.length in 1..4 && p.all { it in '0'..'9' || it.lowercaseChar() in 'a'..'f' }) { "bad group '$p' in: $text" }
                    out += p.toInt(16)
                }
            }
            return out
        }

        /**
         * The address SLAAC gives a host: the first 64 bits of [prefix], then a 64-bit interface ID made
         * from the card's 48-bit [mac] the classic way (modified EUI-64, RFC 4291 appendix A): flip the
         * U/L bit (0x02 of the first byte) and put `ff:fe` in the middle.
         * `fe80::` and `12:fc:01:3b:eb:52` give `fe80::10fc:1ff:fe3b:eb52`.
         */
        fun fromMac(prefix: Ipv6, mac: String): Ipv6 {
            val m = mac.split(':').map { it.toInt(16) }
            require(m.size == 6) { "not a MAC address: $mac" }
            val id = listOf(m[0] xor 0x02, m[1], m[2], 0xff, 0xfe, m[3], m[4], m[5])   // flip U/L, insert ff:fe
            val idGroups = List(4) { i -> (id[2 * i] shl 8) or id[2 * i + 1] }
            return Ipv6(prefix.groups.take(4) + idGroups)
        }

        fun fromBytes(bytes: ByteArray): Ipv6 {
            require(bytes.size == 16) { "an IPv6 address is 16 bytes" }
            return Ipv6(List(8) { i -> ((bytes[2 * i].toInt() and 0xff) shl 8) or (bytes[2 * i + 1].toInt() and 0xff) })
        }
    }
}
