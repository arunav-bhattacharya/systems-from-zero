package sfz.net.l02

import java.nio.ByteBuffer

/**
 * An ARP packet for Ethernet and IPv4 (RFC 826): 28 bytes inside a frame with EtherType 0x0806.
 *
 * ```text
 * offset  size  field
 *  0      2     hardware type        1 = Ethernet
 *  2      2     protocol type        0x0800 = IPv4
 *  4      1     hardware addr length 6
 *  5      1     protocol addr length 4
 *  6      2     operation            1 = request, 2 = reply
 *  8      6     sender MAC
 * 14      4     sender IP
 * 18      6     target MAC           all zeros in a request: that is the question
 * 24      4     target IP
 * ```
 *
 * [encode] is written for you. Write [decode] as its mirror image.
 */
data class ArpPacket(
    val op: Int,
    val senderMac: MacAddress,
    val senderIp: String,
    val targetMac: MacAddress,
    val targetIp: String,
) {
    fun encode(): ByteArray = ByteBuffer.allocate(28)
        .putShort(1)                    // hardware type: Ethernet
        .putShort(0x0800)               // protocol type: IPv4, the same number as its EtherType
        .put(6)                         // a MAC is 6 bytes
        .put(4)                         // an IPv4 address is 4 bytes
        .putShort(op.toShort())
        .put(senderMac.toBytes()).put(ipv4ToBytes(senderIp))
        .put(targetMac.toBytes()).put(ipv4ToBytes(targetIp))
        .array()

    /** The same words tcpdump uses. */
    override fun toString(): String =
        if (op == REQUEST) "Request who-has $targetIp tell $senderIp" else "Reply $senderIp is-at $senderMac"

    companion object {
        const val REQUEST = 1
        const val REPLY = 2

        /** A who-has for [targetIp]. It goes out in a frame addressed to ff:ff:ff:ff:ff:ff. */
        fun request(senderMac: MacAddress, senderIp: String, targetIp: String) =
            ArpPacket(REQUEST, senderMac, senderIp, MacAddress.ZERO, targetIp)

        /**
         * Reads the 28 bytes [encode] writes. Throw IllegalArgumentException unless the hardware type
         * is 1, the protocol type is 0x0800 and the two lengths are 6 and 4: any other ARP is not
         * Ethernet-and-IPv4 and the offsets above would be wrong.
         */
        fun decode(bytes: ByteArray): ArpPacket {
            TODO("check the four type and length fields, then read op, sender MAC and IP, target MAC and IP")
        }
    }
}

/** `"10.10.1.10"` to its four bytes. */
fun ipv4ToBytes(dotted: String): ByteArray {
    val parts = dotted.split('.')
    require(parts.size == 4) { "not an IPv4 address: $dotted" }
    return ByteArray(4) { i -> parts[i].toInt().also { require(it in 0..255) }.toByte() }
}

/** Four bytes starting at [offset] to `"10.10.1.10"`. */
fun ipv4FromBytes(bytes: ByteArray, offset: Int = 0): String =
    (offset until offset + 4).joinToString(".") { (bytes[it].toInt() and 0xff).toString() }
