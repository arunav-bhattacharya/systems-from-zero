package sfz.net.l04

import java.nio.ByteBuffer

/**
 * What traceroute and ping read out of one ICMP error, parsed from a real captured frame.
 *
 * [from] sent the error. [type], [code] and [mtu] come from the ICMP header ([mtu] is 0 unless the
 * error is Fragmentation Needed). The rest describe the packet that died, from the IP header the error
 * quotes: its TTL when that node received it, its destination, and its UDP destination port, which is
 * null when the quoted packet isn't UDP (a ping, for example).
 */
data class IcmpReport(
    val from: Int,
    val type: Int,
    val code: Int,
    val mtu: Int,
    val probeTtl: Int,
    val probeDst: Int,
    val probeDstPort: Int?,
) {
    companion object {
        /**
         * Parses an Ethernet frame that carries an ICMP error. Layout (offsets from the start of the frame):
         *
         * - 0: Ethernet, 14 bytes.
         * - 14: the outer IPv4 header. Its length is the low half of its first byte, in 4-byte words.
         *   The source address is at +12.
         * - ICMP starts after it: type (+0), code (+1), checksum (+2, 2 bytes), unused (+4, 2 bytes),
         *   next-hop MTU (+6, 2 bytes, Fragmentation Needed only), then the quoted packet at +8.
         * - The quoted IPv4 header: its own length (low half of its first byte), TTL at +8,
         *   protocol at +9 (17 is UDP), destination at +16.
         * - After the quoted IP header, the quoted UDP header: destination port at +2.
         *
         * Read unsigned values with `and 0xff` and `and 0xffff`.
         */
        fun parse(frame: ByteArray): IcmpReport {
            TODO("walk the offsets: outer IP, ICMP header, quoted IP header, quoted UDP ports")
        }
    }
}
