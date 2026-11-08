package sfz.enc.l02

import com.google.protobuf.CodedOutputStream
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import java.io.ByteArrayOutputStream
import kotlin.random.Random

/** Base-128 varints and ZigZag, checked byte for byte against protobuf-java's CodedOutputStream. */
class VarintTest {
    private fun hex(b: ByteArray) = b.joinToString(" ") { "%02x".format(it) }

    private fun protobufJava(v: Long): ByteArray {
        val out = ByteArrayOutputStream()
        val coded = CodedOutputStream.newInstance(out)
        coded.writeUInt64NoTag(v)
        coded.flush()
        return out.toByteArray()
    }

    @Test
    fun `numbers below 128 take one byte, and 150 and 4000 take two`() {
        assertThat(hex(Varint.encode(1))).isEqualTo("01")
        assertThat(hex(Varint.encode(127))).isEqualTo("7f")
        assertThat(hex(Varint.encode(128))).isEqualTo("80 01")
        assertThat(hex(Varint.encode(150))).isEqualTo("96 01")
        assertThat(hex(Varint.encode(4000))).isEqualTo("a0 1f")
        assertThat(hex(Varint.encode(0))).isEqualTo("00")
    }

    @Test
    fun `a negative int64 takes all ten bytes`() {
        assertThat(hex(Varint.encode(-1))).isEqualTo("ff ff ff ff ff ff ff ff ff 01")
    }

    @Test
    fun `the 64-bit payment id takes 9 bytes as a varint`() {
        // fixed64 would take 8: varints only win when the numbers are small
        assertThat(Varint.encode(Authorization.SAMPLE.paymentId)).hasSize(9)
    }

    @Test
    fun `encode matches protobuf-java for every size of number`() {
        val rnd = Random(42)
        val values = listOf(0L, 1L, 300L, Long.MAX_VALUE, Long.MIN_VALUE, -1L) + List(200) { rnd.nextLong() ushr rnd.nextInt(64) }
        for (v in values) assertThat(hex(Varint.encode(v))).describedAs("value %d", v).isEqualTo(hex(protobufJava(v)))
    }

    @Test
    fun `decode reads back what encode wrote and says where the next value starts`() {
        val bytes = Varint.encode(4000) + Varint.encode(-1) + Varint.encode(7)
        val first = Varint.decode(bytes, 0)
        assertThat(first).isEqualTo(Decoded(4000, 2))
        val second = Varint.decode(bytes, first.next)
        assertThat(second).isEqualTo(Decoded(-1, 12))
        assertThat(Varint.decode(bytes, second.next)).isEqualTo(Decoded(7, 13))
    }

    @Test
    fun `zigzag turns small negatives into small numbers that fit one byte`() {
        assertThat(listOf(0L, -1L, 1L, -2L, 2L).map { Varint.zigzag(it) }).containsExactly(0L, 1L, 2L, 3L, 4L)
        assertThat(Varint.encode(Varint.zigzag(-1))).hasSize(1)
        assertThat(Varint.encode(Varint.zigzag(-64))).hasSize(1)
        assertThat(Varint.encode(Varint.zigzag(-65))).hasSize(2)
        assertThat(Varint.zigzag(Long.MIN_VALUE)).isEqualTo(-1L) // all 64 bits set: the largest unsigned value
    }
}
