package sfz.enc.l01

import com.fasterxml.jackson.module.kotlin.readValue
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import java.io.ByteArrayInputStream
import java.io.ObjectInputStream

/** One record, four encodings: what each one costs in bytes, and what it puts on the wire. */
class FormatsTest {
    private val auth = Authorization.SAMPLE

    private fun hex(bytes: ByteArray, n: Int) = bytes.take(n).joinToString(" ") { "%02x".format(it) }

    @Test
    fun `JSON spells out every field name and takes 116 bytes`() {
        val bytes = Formats.encode(auth, Format.JSON)
        assertThat(String(bytes)).isEqualTo(
            """{"paymentId":1849204436731904017,"merchant":"Fern Bakery","amountMinor":4000,"currency":"EUR","tags":["card","3ds"]}"""
        )
        assertThat(bytes).hasSize(116)
    }

    @Test
    fun `CBOR and MessagePack keep the names and pack the values, 85 and 84 bytes`() {
        val cbor = Formats.encode(auth, Format.CBOR)
        val msgpack = Formats.encode(auth, Format.MESSAGEPACK)
        assertThat(cbor).hasSize(85)
        assertThat(msgpack).hasSize(84)
        // MessagePack: 0x85 is "a map of 5 entries", 0xa9 "a string of 9 bytes", then "paymentId"
        assertThat(hex(msgpack, 11)).isEqualTo("85 a9 70 61 79 6d 65 6e 74 49 64")
        // then 0xcf, "an unsigned 64-bit integer", and the id in 8 bytes, big-endian
        assertThat(hex(msgpack.copyOfRange(11, 20), 9)).isEqualTo("cf 19 a9 b1 a3 40 7b 40 11")
        // CBOR: Jackson starts a map of unknown length (0xbf) and ends it with a break byte (0xff)
        assertThat(cbor.first()).isEqualTo(0xbf.toByte())
        assertThat(cbor.last()).isEqualTo(0xff.toByte())
    }

    @Test
    fun `Java serialization starts with ac ed 00 05 and carries the class name`() {
        val bytes = Formats.encode(auth, Format.JAVA)
        assertThat(hex(bytes, 4)).isEqualTo("ac ed 00 05")
        assertThat(String(bytes, Charsets.ISO_8859_1)).contains("sfz.enc.l01.Authorization", "paymentId", "amountMinor")
        assertThat(bytes.size).isGreaterThan(250)
    }

    @Test
    fun `dropping the field names saves more than any binary encoding of them`() {
        val values = Formats.positional(auth)
        assertThat(values).containsExactly(1849204436731904017L, "Fern Bakery", 4000L, "EUR", listOf("card", "3ds"))
        assertThat(Formats.encode(values, Format.JSON)).hasSize(61)
        assertThat(Formats.encode(values, Format.MESSAGEPACK)).hasSize(39)
    }

    @Test
    fun `every encoding decodes back to the same record`() {
        assertThat(Formats.json.readValue<Authorization>(Formats.encode(auth, Format.JSON))).isEqualTo(auth)
        assertThat(Formats.cbor.readValue<Authorization>(Formats.encode(auth, Format.CBOR))).isEqualTo(auth)
        assertThat(Formats.messagePack.readValue<Authorization>(Formats.encode(auth, Format.MESSAGEPACK))).isEqualTo(auth)
        val back = ObjectInputStream(ByteArrayInputStream(Formats.encode(auth, Format.JAVA))).use { it.readObject() }
        assertThat(back).isEqualTo(auth)
    }
}
