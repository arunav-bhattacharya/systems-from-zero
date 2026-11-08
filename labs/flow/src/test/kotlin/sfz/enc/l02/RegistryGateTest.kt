package sfz.enc.l02

import org.apache.avro.AvroTypeException
import org.apache.avro.Schema
import org.apache.avro.generic.GenericData
import org.apache.avro.generic.GenericDatumReader
import org.apache.avro.generic.GenericDatumWriter
import org.apache.avro.generic.GenericRecord
import org.apache.avro.io.DecoderFactory
import org.apache.avro.io.EncoderFactory
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import java.io.ByteArrayOutputStream

/** A registry's compatibility gate, on Avro schemas for a payment event. */
class RegistryGateTest {
    private fun schema(vararg fields: String): Schema = Schema.Parser().parse(
        """{"type": "record", "name": "Payment", "namespace": "sfz.payments", "fields": [${fields.joinToString(",")}]}"""
    )

    private val id = """{"name": "paymentId", "type": "long"}"""
    private val amountInt = """{"name": "amount", "type": "int"}"""
    private val currency = """{"name": "currency", "type": "string"}"""
    private val channelWithDefault = """{"name": "channel", "type": "string", "default": "card"}"""
    private val channelNoDefault = """{"name": "channel", "type": "string"}"""
    private val amountString = """{"name": "amount", "type": "string", "default": ""}"""

    private val v1 = schema(id, amountInt, currency)

    @Test
    fun `canRead follows Avro's resolution rules`() {
        assertThat(RegistryGate.canRead(schema(id, amountInt, currency, channelWithDefault), v1)).isTrue() // default fills the gap
        assertThat(RegistryGate.canRead(schema(id, amountInt, currency, channelNoDefault), v1)).isFalse() // nothing to fill it with
        assertThat(RegistryGate.canRead(schema(id, currency), v1)).isTrue() // the reader ignores the writer's extra field
    }

    @Test
    fun `adding a field with a default passes every mode`() {
        val v2 = schema(id, amountInt, currency, channelWithDefault)
        for (mode in Mode.entries) assertThat(RegistryGate.isCompatible(v2, listOf(v1), mode)).describedAs(mode.name).isTrue()
    }

    @Test
    fun `adding a field without a default fails BACKWARD and passes FORWARD`() {
        val v2 = schema(id, amountInt, currency, channelNoDefault)
        assertThat(RegistryGate.isCompatible(v2, listOf(v1), Mode.BACKWARD)).isFalse()
        assertThat(RegistryGate.isCompatible(v2, listOf(v1), Mode.FORWARD)).isTrue()
        assertThat(RegistryGate.isCompatible(v2, listOf(v1), Mode.FULL)).isFalse()
        assertThat(RegistryGate.isCompatible(v2, listOf(v1), Mode.NONE)).isTrue()
    }

    @Test
    fun `removing a field that has no default fails FORWARD and passes BACKWARD`() {
        val v2 = schema(id, amountInt) // currency is gone, and v1 readers have no default for it
        assertThat(RegistryGate.isCompatible(v2, listOf(v1), Mode.BACKWARD)).isTrue()
        assertThat(RegistryGate.isCompatible(v2, listOf(v1), Mode.FORWARD)).isFalse()
        assertThat(RegistryGate.isCompatible(v2, listOf(v1), Mode.FULL)).isFalse()
    }

    @Test
    fun `the first version is always accepted`() {
        assertThat(RegistryGate.isCompatible(v1, emptyList(), Mode.FULL_TRANSITIVE)).isTrue()
    }

    @Test
    fun `the non-transitive trap - each step passes BACKWARD, but v3 cannot read v1`() {
        val v2 = schema(id, currency)               // amount removed
        val v3 = schema(id, currency, amountString) // amount is back, as a string
        assertThat(RegistryGate.isCompatible(v2, listOf(v1), Mode.BACKWARD)).isTrue()
        assertThat(RegistryGate.isCompatible(v3, listOf(v1, v2), Mode.BACKWARD)).isTrue()             // only checked against v2
        assertThat(RegistryGate.isCompatible(v3, listOf(v1, v2), Mode.BACKWARD_TRANSITIVE)).isFalse() // v1 is checked too

        // and it's real: a v3 reader fails on a v1 record still sitting in the topic or the table
        val record = GenericData.Record(v1).apply { put("paymentId", 7L); put("amount", 4000); put("currency", "EUR") }
        val out = ByteArrayOutputStream()
        val enc = EncoderFactory.get().binaryEncoder(out, null)
        GenericDatumWriter<GenericRecord>(v1).write(record, enc)
        enc.flush()
        assertThatThrownBy {
            GenericDatumReader<GenericRecord>(v1, v3).read(null, DecoderFactory.get().binaryDecoder(out.toByteArray(), null))
        }.isInstanceOf(AvroTypeException::class.java)
    }

    @Test
    fun `FORWARD_TRANSITIVE protects the oldest readers still running`() {
        val v2 = schema(id, currency, """{"name": "amount", "type": "int", "default": 0}""") // amount gets a default
        val v3 = schema(id, currency)                                                       // then amount goes
        // v2 readers fall back to amount = 0, so FORWARD (latest only) accepts v3; v1 readers have no default
        assertThat(RegistryGate.isCompatible(v3, listOf(v1, v2), Mode.FORWARD)).isTrue()
        assertThat(RegistryGate.isCompatible(v3, listOf(v1, v2), Mode.FORWARD_TRANSITIVE)).isFalse()
        assertThat(RegistryGate.isCompatible(v3, listOf(v1, v2), Mode.FULL_TRANSITIVE)).isFalse()
    }
}
