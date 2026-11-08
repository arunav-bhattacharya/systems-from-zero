package sfz.stream.l02.demo

import org.apache.avro.Schema
import org.apache.avro.SchemaCompatibility
import org.apache.avro.generic.GenericData
import org.apache.avro.generic.GenericDatumReader
import org.apache.avro.generic.GenericDatumWriter
import org.apache.avro.generic.GenericRecord
import org.apache.avro.io.DecoderFactory
import org.apache.avro.io.EncoderFactory
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.util.HexFormat

private const val V1 = """
{"type": "record", "name": "Payment", "fields": [
  {"name": "id", "type": "string"},
  {"name": "account", "type": "string"},
  {"name": "amount", "type": "long"}]}"""
private const val V2 = """
{"type": "record", "name": "Payment", "fields": [
  {"name": "id", "type": "string"},
  {"name": "account", "type": "string"},
  {"name": "amount", "type": "long"},
  {"name": "currency", "type": "string", "default": "EUR"}]}"""
private const val V3 = """
{"type": "record", "name": "Payment", "fields": [
  {"name": "id", "type": "string"},
  {"name": "account", "type": "string"},
  {"name": "amount", "type": "long"},
  {"name": "merchantId", "type": "string"}]}"""

/**
 * One payment, written with version 1 of its Avro schema and read back with three reader schemas: the same one,
 * one that adds a field with a default, and one that adds a field without a default. No broker, no registry.
 */
fun main() {
    val v1 = Schema.Parser().parse(V1)
    val v2 = Schema.Parser().parse(V2)
    val v3 = Schema.Parser().parse(V3)

    // the producer's side: a v1 payment, encoded as Avro binary
    val payment = GenericData.Record(v1).apply { put("id", "pay-1"); put("account", "acct-17"); put("amount", 4000L) }
    val out = ByteArrayOutputStream()
    val encoder = EncoderFactory.get().binaryEncoder(out, null)
    GenericDatumWriter<GenericRecord>(v1).write(payment, encoder)
    encoder.flush()
    val avro = out.toByteArray()
    println("v1 payment as Avro binary, ${avro.size} bytes: ${HexFormat.ofDelimiter(" ").formatHex(avro)}")

    // what a registry-aware serializer sends: magic byte 0, the schema id (say 1) as 4 bytes, then the Avro bytes
    val framed = ByteBuffer.allocate(5 + avro.size).put(0).putInt(1).put(avro).array()
    println("with the 5-byte registry prefix, ${framed.size} bytes: ${HexFormat.ofDelimiter(" ").formatHex(framed, 0, 5)} | ...")

    // the consumer's side: the writer schema comes with the data (by id), the reader schema is the consumer's own
    for ((name, reader) in listOf("v1" to v1, "v2" to v2, "v3" to v3)) {
        try {
            val read = GenericDatumReader<GenericRecord>(v1, reader).read(null, DecoderFactory.get().binaryDecoder(avro, null))
            println("reader $name reads it: $read")
        } catch (e: Exception) {
            println("reader $name fails:    ${e.javaClass.simpleName}: ${e.message}")
        }
    }
    // Avro's own check, the one a registry runs before it accepts a new version
    println("can v2 read v1 data? ${SchemaCompatibility.checkReaderWriterCompatibility(v2, v1).type}")
    println("can v3 read v1 data? ${SchemaCompatibility.checkReaderWriterCompatibility(v3, v1).type}")
}
