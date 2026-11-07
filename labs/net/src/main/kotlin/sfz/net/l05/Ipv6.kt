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
        TODO("find the longest run of zero groups (length 2 or more, first one wins), join the rest with ':'")
    }

    /** What this address is for, from its first bits. The checks on [Ipv6Kind] say which bits. */
    val kind: Ipv6Kind
        get() = TODO("check the prefixes in the order the enum lists them")

    /**
     * The solicited-node multicast address a host joins for this address: `ff02::1:ff` followed by the
     * low 24 bits of this address. IPv6 neighbor discovery sends "who has X?" there instead of to every
     * card on the link, so in practice only X's owner wakes up. `fd00:10:6::20` gives `ff02::1:ff00:20`.
     */
    fun solicitedNode(): Ipv6 {
        TODO("ff02:0:0:0:0:1:ff00:0 plus the low 24 bits of this address")
    }

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
            TODO("split around '::', parse each side's groups, fill the gap with zeros")
        }

        /**
         * The address SLAAC gives a host: the first 64 bits of [prefix], then a 64-bit interface ID made
         * from the card's 48-bit [mac] the classic way (modified EUI-64, RFC 4291 appendix A): flip the
         * U/L bit (0x02 of the first byte) and put `ff:fe` in the middle.
         * `fe80::` and `12:fc:01:3b:eb:52` give `fe80::10fc:1ff:fe3b:eb52`.
         */
        fun fromMac(prefix: Ipv6, mac: String): Ipv6 {
            TODO("six MAC bytes -> first byte xor 2, insert ff fe -> four groups after the prefix's first four")
        }

        fun fromBytes(bytes: ByteArray): Ipv6 {
            require(bytes.size == 16) { "an IPv6 address is 16 bytes" }
            return Ipv6(List(8) { i -> ((bytes[2 * i].toInt() and 0xff) shl 8) or (bytes[2 * i + 1].toInt() and 0xff) })
        }
    }
}
