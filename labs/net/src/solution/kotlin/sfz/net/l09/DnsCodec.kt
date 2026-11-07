package sfz.net.l09

import java.nio.ByteBuffer

/**
 * Turns DNS messages into bytes and back (RFC 1035, section 4). Everything is big-endian.
 *
 * The header is 12 bytes: ID, flags, then four 16-bit counts: questions, answers, authority
 * records, additional records. Then come the questions, then the three lists of records.
 *
 * A name on the wire is a list of labels, each one length byte and that many characters, ended by
 * a zero byte: `example.com` is `07 example 03 com 00`. A length byte whose top two bits are set
 * (`c0` and up) is a compression pointer instead: it and the next byte form a 14-bit offset from
 * the start of the message, where the rest of the name continues. `c0 0c` means "the name at
 * offset 12", which is where the question's name always starts.
 */
object DnsCodec {
    /** `"example.com"` becomes `07 example 03 com 00`. Labels longer than 63 bytes are illegal. */
    fun encodeName(name: String): ByteArray {
        val out = java.io.ByteArrayOutputStream()
        for (label in name.split('.').filter { it.isNotEmpty() }) {
            val bytes = label.toByteArray(Charsets.US_ASCII)
            require(bytes.size <= 63) { "label longer than 63 bytes: $label" }   // the top two bits mean "pointer"
            out.write(bytes.size)
            out.write(bytes)
        }
        out.write(0)                                                    // the root ends every name
        return out.toByteArray()
    }

    /**
     * A standard query for [name] and [type], the way `dig +noedns +noadflag` sends it: the header
     * with [id], flags `0x0100` (only RD: "please recurse for me"), one question and no records,
     * then the question: the name, the type, class 1.
     */
    fun encodeQuery(id: Int, name: String, type: Int): ByteArray {
        val qname = encodeName(name)
        return ByteBuffer.allocate(12 + qname.size + 4)
            .putShort(id.toShort())
            .putShort(0x0100.toShort())                                 // RD
            .putShort(1).putShort(0).putShort(0).putShort(0)            // one question, no records
            .put(qname)
            .putShort(type.toShort())
            .putShort(1)                                                // class IN
            .array()
    }

    /**
     * Reads the name that starts at [offset] in [msg] and returns it with the offset of the first
     * byte after it, in the place you started reading. A name that ends in a pointer is 2 bytes long
     * there, however long the name it points to is.
     *
     * Follow pointers, but only backwards: a pointer must point before the pointer itself. A message
     * from the network can be hostile, and a pointer to itself would loop forever. Throw
     * [IllegalArgumentException] for one that doesn't point backwards.
     */
    fun readName(msg: ByteArray, offset: Int): Pair<String, Int> {
        val labels = mutableListOf<String>()
        var at = offset
        var end = -1                                                    // where the name ends where we started
        while (true) {
            val length = msg[at].toInt() and 0xff
            when {
                length == 0 -> {
                    if (end < 0) end = at + 1
                    return labels.joinToString(".") to end
                }
                length and 0xc0 == 0xc0 -> {                            // a compression pointer
                    val target = ((length and 0x3f) shl 8) or (msg[at + 1].toInt() and 0xff)
                    require(target < at) { "compression pointer at $at does not point backwards ($target)" }
                    if (end < 0) end = at + 2                           // the pointer is the last 2 bytes here
                    at = target
                }
                else -> {
                    labels += String(msg, at + 1, length, Charsets.US_ASCII)
                    at += 1 + length
                }
            }
        }
    }

    /**
     * Decodes a whole message: the header, every question, then the answer, authority and additional
     * records. Each record is a name, then type (16 bits), class (16), TTL (32, unsigned), RDLENGTH
     * (16) and RDLENGTH bytes of data. Decode the data by type: A is 4 address bytes; CNAME and NS
     * are one name; SOA is two names and five 32-bit numbers. The names inside data may be
     * compressed too, so read them with [readName] on the whole message. Keep anything else as
     * [RData.Raw]. Always move on by RDLENGTH, whatever the type.
     */
    fun decode(msg: ByteArray): DnsMessage {
        val b = ByteBuffer.wrap(msg)
        fun u16(at: Int) = b.getShort(at).toInt() and 0xffff
        fun u32(at: Int) = b.getInt(at).toLong() and 0xFFFF_FFFFL

        val counts = List(4) { u16(4 + 2 * it) }                        // QD, AN, NS, AR
        var at = 12
        val questions = List(counts[0]) {
            val (name, next) = readName(msg, at)
            at = next + 4
            Question(name, u16(next), u16(next + 2))
        }
        fun record(): ResourceRecord {
            val (name, next) = readName(msg, at)
            val type = u16(next)
            val rdLength = u16(next + 8)
            val rd = next + 10                                          // where the data starts
            val data = when (type) {
                RecordType.A -> RData.Address((0 until 4).joinToString(".") { (msg[rd + it].toInt() and 0xff).toString() })
                RecordType.CNAME, RecordType.NS -> RData.Name(readName(msg, rd).first)
                RecordType.SOA -> {
                    val (mname, afterM) = readName(msg, rd)
                    val (rname, afterR) = readName(msg, afterM)
                    RData.Soa(mname, rname, u32(afterR), u32(afterR + 4), u32(afterR + 8), u32(afterR + 12), u32(afterR + 16))
                }
                else -> RData.Raw(msg.copyOfRange(rd, rd + rdLength))
            }
            at = rd + rdLength                                          // RDLENGTH, never the decoded size
            return ResourceRecord(name, type, u16(next + 2), u32(next + 4), data)
        }
        val answers = List(counts[1]) { record() }
        val authority = List(counts[2]) { record() }
        val additional = List(counts[3]) { record() }
        return DnsMessage(u16(0), u16(2), questions, answers, authority, additional)
    }
}
