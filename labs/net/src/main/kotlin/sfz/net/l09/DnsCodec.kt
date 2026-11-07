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
        TODO("one length byte and the label's bytes per label, then a zero byte")
    }

    /**
     * A standard query for [name] and [type], the way `dig +noedns +noadflag` sends it: the header
     * with [id], flags `0x0100` (only RD: "please recurse for me"), one question and no records,
     * then the question: the name, the type, class 1.
     */
    fun encodeQuery(id: Int, name: String, type: Int): ByteArray {
        TODO("12-byte header, then encodeName(name), type, class 1")
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
        TODO("labels until 0; on a pointer jump there, and remember where the name ended here")
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
        TODO("header and counts; questions; three lists of records, each with its RDATA decoded by type")
    }
}
