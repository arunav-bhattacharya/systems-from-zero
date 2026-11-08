package sfz.enc.l02

import com.google.protobuf.DynamicMessage
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** The Authorization message on the wire, by hand, against protobuf-java. */
class ProtoCodecTest {
    private fun hex(b: ByteArray) = b.joinToString(" ") { "%02x".format(it) }

    @Test
    fun `keys put the field number above the wire type`() {
        assertThat(ProtoCodec.key(1, ProtoCodec.VARINT)).isEqualTo(0x08)
        assertThat(ProtoCodec.key(2, ProtoCodec.LEN)).isEqualTo(0x12)
        assertThat(ProtoCodec.key(5, ProtoCodec.LEN)).isEqualTo(0x2a)
        assertThat(ProtoCodec.key(16, ProtoCodec.VARINT)).isEqualTo(0x80) // field 16 needs a two-byte key
    }

    @Test
    fun `the authorization takes 42 bytes, the same bytes protobuf-java writes`() {
        val mine = ProtoCodec.encode(Authorization.SAMPLE)
        assertThat(mine).hasSize(42)
        assertThat(hex(mine)).isEqualTo(hex(ProtoSchemas.encode(Authorization.SAMPLE)))
        assertThat(hex(mine.copyOfRange(10, 23))).isEqualTo("12 0b 46 65 72 6e 20 42 61 6b 65 72 79") // field 2, 11 bytes, "Fern Bakery"
        assertThat(hex(mine.copyOfRange(23, 26))).isEqualTo("18 a0 1f") // field 3, 4000
    }

    @Test
    fun `a zero or empty field is not written, as in proto3`() {
        val free = Authorization(77, "", 0, "EUR", emptyList())
        val mine = ProtoCodec.encode(free)
        assertThat(hex(mine)).isEqualTo("08 4d 22 03 45 55 52")
        assertThat(hex(mine)).isEqualTo(hex(ProtoSchemas.encode(free)))
    }

    @Test
    fun `decode reads protobuf-java's bytes`() {
        assertThat(ProtoCodec.decode(ProtoSchemas.encode(Authorization.SAMPLE))).isEqualTo(Authorization.SAMPLE)
        val many = Authorization(1, "Zoë's Café", 123456789, "JPY", listOf("a", "", "c"))
        assertThat(ProtoCodec.decode(ProtoSchemas.encode(many))).isEqualTo(many)
    }

    @Test
    fun `protobuf-java reads the hand-written bytes`() {
        val msg = DynamicMessage.parseFrom(ProtoSchemas.v1, ProtoCodec.encode(Authorization.SAMPLE))
        assertThat(msg.getField(ProtoSchemas.v1.findFieldByName("payment_id"))).isEqualTo(1849204436731904017L)
        assertThat(msg.getField(ProtoSchemas.v1.findFieldByName("merchant"))).isEqualTo("Fern Bakery")
        assertThat(msg.unknownFields.asMap()).isEmpty()
    }

    @Test
    fun `old code skips fields added by a newer writer`() {
        // version 2 added risk_score = 6 and device_id = 7; this decoder only knows 1 to 5
        val v2bytes = ProtoSchemas.encode(Authorization.SAMPLE, ProtoSchemas.v2, mapOf("risk_score" to 87L, "device_id" to "pos-17"))
        assertThat(v2bytes.size).isGreaterThan(42)
        assertThat(ProtoCodec.decode(v2bytes)).isEqualTo(Authorization.SAMPLE)
    }

    @Test
    fun `new code fills in defaults for fields an older writer never sent`() {
        val old = byteArrayOf(0x08, 0x4d) // only field 1, payment_id = 77
        assertThat(ProtoCodec.decode(old)).isEqualTo(Authorization(77, "", 0, "", emptyList()))
    }

    @Test
    fun `a known field number with an unexpected wire type is skipped too`() {
        // field 3 arrives as LEN ("4000" as text) instead of VARINT: protobuf-java treats it as unknown
        val odd = ProtoCodec.encode(Authorization(77, "", 0, "EUR", emptyList())) + byteArrayOf(0x1a, 0x04) + "4000".toByteArray()
        assertThat(ProtoCodec.decode(odd).amountMinor).isZero()
        assertThat(ProtoCodec.decode(odd).currency).isEqualTo("EUR")
    }
}
