package sfz.stream.l02

import org.apache.avro.Schema
import org.apache.avro.SchemaCompatibility
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.stream.l02.FieldType.DOUBLE
import sfz.stream.l02.FieldType.INT
import sfz.stream.l02.FieldType.LONG
import sfz.stream.l02.FieldType.STRING

/**
 * Your registry checks. The messages follow the error types Schema Registry 8.4 printed in this lesson's Try-it,
 * and the last test compares your reader rule with Avro's own on many pairs of schemas.
 */
class CompatibilityCheckerTest {
    private val v1 = RecordSchema("Payment", listOf(Field("id", STRING), Field("account", STRING), Field("amount", LONG)))
    private val withCurrency = RecordSchema("Payment", v1.fields + Field("currency", STRING, hasDefault = true))
    private val withMerchant = RecordSchema("Payment", v1.fields + Field("merchantId", STRING))

    @Test
    fun `adding a field with a default is backward compatible`() {
        assertThat(CompatibilityChecker.check(Mode.BACKWARD, withCurrency, listOf(v1))).isEmpty()
    }

    @Test
    fun `adding a field without a default is not, because old records don't have it`() {
        assertThat(CompatibilityChecker.check(Mode.BACKWARD, withMerchant, listOf(v1)))
            .containsExactly("READER_FIELD_MISSING_DEFAULT_VALUE: merchantId")
    }

    @Test
    fun `removing a field is backward compatible, and forward compatible only if it had a default`() {
        val noAmount = RecordSchema("Payment", v1.fields.filter { it.name != "amount" })
        assertThat(CompatibilityChecker.check(Mode.BACKWARD, noAmount, listOf(v1))).isEmpty()
        // old consumers still expect amount, and v1 gave it no default
        assertThat(CompatibilityChecker.check(Mode.FORWARD, noAmount, listOf(v1)))
            .containsExactly("READER_FIELD_MISSING_DEFAULT_VALUE: amount")
        val noCurrency = v1
        assertThat(CompatibilityChecker.check(Mode.FORWARD, noCurrency, listOf(withCurrency))).isEmpty()
    }

    @Test
    fun `a type may widen for readers but not narrow`() {
        val intAmount = RecordSchema("Payment", listOf(Field("id", STRING), Field("account", STRING), Field("amount", INT)))
        val doubleAmount = RecordSchema("Payment", listOf(Field("id", STRING), Field("account", STRING), Field("amount", DOUBLE)))
        assertThat(CompatibilityChecker.readProblems(reader = v1, writer = intAmount)).isEmpty()       // int read as long
        assertThat(CompatibilityChecker.readProblems(reader = doubleAmount, writer = v1)).isEmpty()    // long read as double
        assertThat(CompatibilityChecker.readProblems(reader = intAmount, writer = v1))
            .containsExactly("TYPE_MISMATCH: amount (writer LONG, reader INT)")
        assertThat(CompatibilityChecker.check(Mode.BACKWARD, intAmount, listOf(v1)))
            .containsExactly("TYPE_MISMATCH: amount (writer LONG, reader INT)")
    }

    @Test
    fun `FULL needs both directions`() {
        assertThat(CompatibilityChecker.check(Mode.FULL, withCurrency, listOf(v1))).isEmpty()
        val stringAmount = RecordSchema("Payment", listOf(Field("id", STRING), Field("account", STRING), Field("amount", STRING)))
        assertThat(CompatibilityChecker.check(Mode.FULL, stringAmount, listOf(v1))).containsExactly(
            "TYPE_MISMATCH: amount (writer LONG, reader STRING)",   // backward: the new reader, old data
            "TYPE_MISMATCH: amount (writer STRING, reader LONG)",   // forward: the old reader, new data
        )
    }

    @Test
    fun `the transitive modes check every version, the others only the latest`() {
        val currencyRequired = RecordSchema("Payment", v1.fields + Field("currency", STRING))
        val history = listOf(v1, withCurrency) // v2 added currency with a default
        // v3 drops the default: fine against v2, whose records all have currency, but not against v1's records
        assertThat(CompatibilityChecker.check(Mode.BACKWARD, currencyRequired, history)).isEmpty()
        assertThat(CompatibilityChecker.check(Mode.BACKWARD_TRANSITIVE, currencyRequired, history))
            .containsExactly("READER_FIELD_MISSING_DEFAULT_VALUE: currency")
    }

    @Test
    fun `the first version is always accepted, NONE accepts anything, and names must match`() {
        assertThat(CompatibilityChecker.check(Mode.FULL_TRANSITIVE, withMerchant, emptyList())).isEmpty()
        assertThat(CompatibilityChecker.check(Mode.NONE, withMerchant, listOf(v1))).isEmpty()
        val refund = RecordSchema("Refund", v1.fields)
        assertThat(CompatibilityChecker.readProblems(reader = refund, writer = v1)).containsExactly("NAME_MISMATCH: writer Payment, reader Refund")
    }

    @Test
    fun `your reader rule agrees with Avro's own on every pair of these schemas`() {
        val types = FieldType.entries
        val schemas = buildList {
            add(v1); add(withCurrency); add(withMerchant)
            for (t in types) add(RecordSchema("Payment", listOf(Field("id", STRING), Field("amount", t))))
            for (t in types) add(RecordSchema("Payment", listOf(Field("id", STRING), Field("amount", t, hasDefault = true), Field("note", t, hasDefault = true))))
        }
        for (reader in schemas) for (writer in schemas) {
            val avro = SchemaCompatibility.checkReaderWriterCompatibility(toAvro(reader), toAvro(writer)).type
            val ours = CompatibilityChecker.readProblems(reader, writer)
            assertThat(ours.isEmpty()).describedAs("reader $reader, writer $writer: Avro says $avro, you say $ours")
                .isEqualTo(avro == SchemaCompatibility.SchemaCompatibilityType.COMPATIBLE)
        }
    }

    private fun toAvro(s: RecordSchema): Schema {
        val fields = s.fields.joinToString(",") { f ->
            val type = f.type.name.lowercase()
            val default = when (f.type) {
                INT, LONG -> "0"
                FieldType.FLOAT, DOUBLE -> "0.0"
                STRING -> "\"\""
                FieldType.BOOLEAN -> "false"
            }
            """{"name":"${f.name}","type":"$type"${if (f.hasDefault) ",\"default\":$default" else ""}}"""
        }
        return Schema.Parser().parse("""{"type":"record","name":"${s.name}","fields":[$fields]}""")
    }
}
