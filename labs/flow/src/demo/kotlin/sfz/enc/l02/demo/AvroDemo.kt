package sfz.enc.l02.demo

import org.apache.avro.AvroTypeException
import org.apache.avro.Schema
import org.apache.avro.file.DataFileWriter
import org.apache.avro.generic.GenericData
import org.apache.avro.generic.GenericDatumReader
import org.apache.avro.generic.GenericDatumWriter
import org.apache.avro.generic.GenericRecord
import org.apache.avro.io.DecoderFactory
import org.apache.avro.io.EncoderFactory
import sfz.enc.l02.demo.DemoSchemas.hex
import java.io.ByteArrayOutputStream

fun avro(fields: String): Schema = Schema.Parser().parse(
    """{"type": "record", "name": "Authorization", "namespace": "sfz.payments", "fields": [$fields]}"""
)

val V1_FIELDS = """
    {"name": "paymentId", "type": "long"},
    {"name": "merchant", "type": "string"},
    {"name": "amountMinor", "type": "long"},
    {"name": "currency", "type": "string"},
    {"name": "tags", "type": {"type": "array", "items": "string"}}"""

/** The authorization in Avro: no names and no numbers in the bytes, so the reader needs the writer's schema. */
fun main() {
    val writer = avro(V1_FIELDS)
    val rec = GenericData.Record(writer).apply {
        put("paymentId", 1849204436731904017L); put("merchant", "Fern Bakery"); put("amountMinor", 4000L)
        put("currency", "EUR"); put("tags", listOf("card", "3ds"))
    }
    val out = ByteArrayOutputStream()
    val enc = EncoderFactory.get().binaryEncoder(out, null)
    GenericDatumWriter<GenericRecord>(writer).write(rec, enc)
    enc.flush()
    val bytes = out.toByteArray()
    println("Avro: ${bytes.size} bytes")
    println(hex(bytes))

    // a newer reader adds a field with a default: Avro matches fields by name and fills the gap
    val readerWithDefault = avro("$V1_FIELDS, {\"name\": \"channel\", \"type\": \"string\", \"default\": \"card\"}")
    val r = GenericDatumReader<GenericRecord>(writer, readerWithDefault)
        .read(null, DecoderFactory.get().binaryDecoder(bytes, null))
    println("reader with channel (default card): $r")

    // the same field without a default: there is nothing to fill it with
    val readerNoDefault = avro("$V1_FIELDS, {\"name\": \"channel\", \"type\": \"string\"}")
    try {
        GenericDatumReader<GenericRecord>(writer, readerNoDefault).read(null, DecoderFactory.get().binaryDecoder(bytes, null))
    } catch (e: AvroTypeException) {
        println("reader with channel, no default: ${e.message}")
    }

    // decoding with the wrong writer schema: the bytes say nothing about their own layout
    val wrongWriter = avro("""{"name": "paymentId", "type": "long"}, {"name": "amountMinor", "type": "long"}""")
    val garbage = GenericDatumReader<GenericRecord>(wrongWriter).read(null, DecoderFactory.get().binaryDecoder(bytes, null))
    println("read with the wrong writer schema: $garbage")

    // an object container file puts the writer's schema in the header, once for all records
    val file = ByteArrayOutputStream()
    DataFileWriter(GenericDatumWriter<GenericRecord>(writer)).use { w ->
        w.create(writer, file)
        repeat(1000) { w.append(rec) }
    }
    val f = file.toByteArray()
    println("container file with 1000 records: ${f.size} bytes, starts ${hex(f.copyOfRange(0, 4))} (\"Obj\" 1), " +
        "schema in header: ${String(f, Charsets.ISO_8859_1).contains("\"name\":\"merchant\"")}")
}
