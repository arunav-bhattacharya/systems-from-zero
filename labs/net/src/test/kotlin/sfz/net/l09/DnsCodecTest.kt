package sfz.net.l09

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.net.support.Hex

/** Real queries and answers from the third Try it, captured in the lab box against 1.1.1.1. */
class DnsCodecTest {
    @Test
    fun `a name is length-prefixed labels and a zero byte`() {
        assertThat(Hex.format(DnsCodec.encodeName("example.com"))).isEqualTo("076578616d706c6503636f6d00")
        assertThat(Hex.format(DnsCodec.encodeName(""))).`as`("the root").isEqualTo("00")
    }

    @Test
    fun `a label longer than 63 bytes is rejected`() {
        assertThatThrownBy { DnsCodec.encodeName("a".repeat(64) + ".example") }.isInstanceOf(IllegalArgumentException::class.java)
    }

    @Test
    fun `your query is byte for byte the one dig sent`() {
        val dig = dnsPayload("example-query")
        assertThat(Hex.format(DnsCodec.encodeQuery(39300, "example.com", RecordType.A))).isEqualTo(Hex.format(dig))
        assertThat(dig).hasSize(29)
    }

    @Test
    fun `the header and question of the answer from 1-1-1-1`() {
        val m = DnsCodec.decode(dnsPayload("example-answer"))
        assertThat(m.id).`as`("the same ID as the query").isEqualTo(39300)
        assertThat(m.flags).isEqualTo(0x8180)
        assertThat(m.isResponse).isTrue()
        assertThat(m.recursionDesired).isTrue()
        assertThat(m.recursionAvailable).isTrue()
        assertThat(m.authoritative).`as`("a recursive resolver answers from its cache, not as the owner").isFalse()
        assertThat(m.rcode).isEqualTo(Rcode.NOERROR)
        assertThat(m.questions).containsExactly(Question("example.com", RecordType.A))
    }

    @Test
    fun `two A records, each named with a pointer back to the question`() {
        val m = DnsCodec.decode(dnsPayload("example-answer"))
        assertThat(m.answers).containsExactly(
            ResourceRecord("example.com", RecordType.A, 1, 30, RData.Address("172.66.147.243")),
            ResourceRecord("example.com", RecordType.A, 1, 30, RData.Address("104.20.23.154")),
        )
        assertThat(m.authority).isEmpty()
        assertThat(m.additional).isEmpty()
    }

    @Test
    fun `readName returns where the name ends, and a pointer takes 2 bytes`() {
        val msg = dnsPayload("example-answer")
        assertThat(DnsCodec.readName(msg, 12)).isEqualTo("example.com" to 25)
        assertThat(DnsCodec.readName(msg, 29)).`as`("c0 0c at offset 29").isEqualTo("example.com" to 31)
    }

    @Test
    fun `a CNAME chain, with a pointer inside the CNAME's data and a pointer to that data`() {
        val m = DnsCodec.decode(dnsPayload("cname-answer"))
        assertThat(m.answers).containsExactly(
            ResourceRecord("www.wikipedia.org", RecordType.CNAME, 1, 86222, RData.Name("dyna.wikimedia.org")),
            ResourceRecord("dyna.wikimedia.org", RecordType.A, 1, 2, RData.Address("198.35.26.224")),
        )
    }

    @Test
    fun `NXDOMAIN with the zone's SOA, whose names are compressed twice over`() {
        val m = DnsCodec.decode(dnsPayload("nxdomain-answer"))
        assertThat(m.rcode).isEqualTo(Rcode.NXDOMAIN)
        assertThat(m.answers).isEmpty()
        assertThat(m.authority).containsExactly(
            ResourceRecord(
                "iana.org", RecordType.SOA, 1, 3600,
                RData.Soa("sns.dns.icann.org", "noc.dns.icann.org", 2026110301, 7200, 3600, 1209600, 3600),
            ),
        )
    }

    @Test
    fun `a pointer that doesn't point backwards is rejected instead of looping forever`() {
        // header, then a name at offset 12 that is a pointer to offset 12: itself
        val hostile = Hex.parse("1234 0100 0001 0000 0000 0000  c00c 0001 0001")
        assertThatThrownBy { DnsCodec.decode(hostile) }.isInstanceOf(IllegalArgumentException::class.java)
    }

    @Test
    fun `decoding your own query gives back the question`() {
        val m = DnsCodec.decode(DnsCodec.encodeQuery(7, "ledger.pay.test", RecordType.AAAA))
        assertThat(m.id).isEqualTo(7)
        assertThat(m.isResponse).isFalse()
        assertThat(m.recursionDesired).isTrue()
        assertThat(m.questions).containsExactly(Question("ledger.pay.test", RecordType.AAAA))
    }
}

/** The UDP payload, that is the DNS message, of one captured frame in src/test/resources/sfz/net/l09/. */
fun dnsPayload(name: String): ByteArray {
    val frame = Hex.resource("sfz/net/l09/$name.txt")
    val udp = 14 + (frame[14].toInt() and 0x0f) * 4
    val udpLength = ((frame[udp + 4].toInt() and 0xff) shl 8) or (frame[udp + 5].toInt() and 0xff)
    return frame.copyOfRange(udp + 8, udp + udpLength)
}
