package sfz.net.l09

/** The record types this lab reads (RFC 1035, plus AAAA from RFC 3596). */
object RecordType {
    const val A = 1
    const val NS = 2
    const val CNAME = 5
    const val SOA = 6
    const val AAAA = 28
}

/** Response codes, the low 4 bits of the flags. */
object Rcode {
    const val NOERROR = 0
    const val SERVFAIL = 2
    const val NXDOMAIN = 3
}

/**
 * A name is kept as dotted text without the final dot: `"example.com"`. The root is `""`.
 * [dnsClass] is 1 (IN, the internet) for everything you will meet.
 */
data class Question(val name: String, val type: Int, val dnsClass: Int = 1)

/** The data part of a record, already decoded. */
sealed interface RData {
    /** A record: four bytes of IPv4 address, as dotted text. */
    data class Address(val ip: String) : RData

    /** CNAME and NS records: one domain name (it may be compressed on the wire). */
    data class Name(val name: String) : RData

    /** SOA: the zone's primary server, its admin's mailbox, then five 32-bit numbers. */
    data class Soa(
        val mname: String,
        val rname: String,
        val serial: Long,
        val refresh: Long,
        val retry: Long,
        val expire: Long,
        val minimum: Long,
    ) : RData

    /** Any other type, kept as raw bytes. */
    class Raw(val bytes: ByteArray) : RData {
        override fun equals(other: Any?) = other is Raw && bytes.contentEquals(other.bytes)
        override fun hashCode() = bytes.contentHashCode()
        override fun toString() = "Raw(${bytes.size} bytes)"
    }
}

/** One resource record: owner name, type, class, TTL in seconds, and data. */
data class ResourceRecord(val name: String, val type: Int, val dnsClass: Int, val ttl: Long, val data: RData)

/**
 * One DNS message, query or response. The 16 bits of [flags] are, from the top: QR (1 = response),
 * the 4-bit opcode, AA (authoritative answer), TC (truncated), RD (recursion desired), RA
 * (recursion available), three bits we don't use here, and the 4-bit response code.
 */
data class DnsMessage(
    val id: Int,
    val flags: Int,
    val questions: List<Question>,
    val answers: List<ResourceRecord>,
    val authority: List<ResourceRecord>,
    val additional: List<ResourceRecord>,
) {
    val isResponse: Boolean get() = flags and 0x8000 != 0
    val authoritative: Boolean get() = flags and 0x0400 != 0
    val recursionDesired: Boolean get() = flags and 0x0100 != 0
    val recursionAvailable: Boolean get() = flags and 0x0080 != 0
    val rcode: Int get() = flags and 0x000F
}
