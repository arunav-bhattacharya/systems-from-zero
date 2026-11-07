package sfz.net.l02

/**
 * A 48-bit Ethernet MAC address, kept in the low 48 bits of a Long.
 *
 * The first octet as you write it ("ee" in `ee:02:07:41:4d:8c`) is the first byte on the wire and
 * the top byte here: bits 40 to 47 of [bits]. Its two lowest bits carry meaning:
 *
 * - bit 0, I/G (individual/group): 1 means a group address, which every listening card accepts:
 *   multicast, or the broadcast address ff:ff:ff:ff:ff:ff.
 * - bit 1, U/L (universal/local): 1 means the address was made up locally (Docker, VMs, phones with
 *   private Wi-Fi addresses). 0 means a vendor burned it in, and the first three octets are its OUI.
 */
@JvmInline
value class MacAddress(val bits: Long) {
    init {
        require(bits in 0L..0xffff_ffff_ffffL) { "a MAC address has 48 bits" }
    }

    /** The first octet, 0 to 255: `0xee` for `ee:02:07:41:4d:8c`. */
    val firstOctet: Int get() = ((bits shr 40) and 0xff).toInt()

    /** True only for ff:ff:ff:ff:ff:ff. */
    val isBroadcast: Boolean
        get() = bits == 0xffff_ffff_ffffL

    /** True when the I/G bit (lowest bit of the first octet) is set. Broadcast counts as multicast. */
    val isMulticast: Boolean
        get() = firstOctet and 0x01 != 0          // I/G bit: the first bit a card receives

    /** True when the U/L bit (second-lowest bit of the first octet) is set. */
    val isLocallyAdministered: Boolean
        get() = firstOctet and 0x02 != 0          // U/L bit

    /** The six bytes in wire order. */
    fun toBytes(): ByteArray = ByteArray(6) { i -> (bits shr (40 - 8 * i)).toByte() }

    /** Lower-case hex pairs joined by colons, the way `ip link` and tcpdump print it. */
    override fun toString(): String =
        (0 until 6).joinToString(":") { i -> "%02x".format((bits shr (40 - 8 * i)) and 0xff) }

    companion object {
        val BROADCAST = MacAddress(0xffff_ffff_ffffL)

        /** 00:00:00:00:00:00, what an ARP request puts in the target MAC field: "I don't know yet". */
        val ZERO = MacAddress(0L)

        /** Reads `ee:02:07:41:4d:8c` (or with dashes, any case). */
        fun parse(text: String): MacAddress {
            val parts = text.split(':', '-')
            require(parts.size == 6) { "not a MAC address: $text" }
            return MacAddress(parts.fold(0L) { acc, p -> (acc shl 8) or p.toLong(16) })
        }

        /** Reads six bytes starting at [offset]. */
        fun of(bytes: ByteArray, offset: Int = 0): MacAddress =
            MacAddress((0 until 6).fold(0L) { acc, i -> (acc shl 8) or (bytes[offset + i].toLong() and 0xff) })
    }
}
