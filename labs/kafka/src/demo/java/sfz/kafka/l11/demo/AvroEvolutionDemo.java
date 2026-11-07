package sfz.kafka.l11.demo;

import org.apache.avro.Schema;
import org.apache.avro.SchemaCompatibility;
import org.apache.avro.generic.GenericData;
import org.apache.avro.generic.GenericDatumReader;
import org.apache.avro.generic.GenericDatumWriter;
import org.apache.avro.generic.GenericRecord;
import org.apache.avro.io.BinaryEncoder;
import org.apache.avro.io.DecoderFactory;
import org.apache.avro.io.EncoderFactory;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.util.HexFormat;

/**
 * One payment, written with version 1 of its Avro schema and read back with three reader schemas: the same one,
 * one that adds a field with a default, and one that adds a field without a default. No broker, no registry.
 */
public class AvroEvolutionDemo {
    static final String V1 = """
            {"type": "record", "name": "Payment", "fields": [
              {"name": "id", "type": "string"},
              {"name": "account", "type": "string"},
              {"name": "amount", "type": "long"}]}""";
    static final String V2 = """
            {"type": "record", "name": "Payment", "fields": [
              {"name": "id", "type": "string"},
              {"name": "account", "type": "string"},
              {"name": "amount", "type": "long"},
              {"name": "currency", "type": "string", "default": "EUR"}]}""";
    static final String V3 = """
            {"type": "record", "name": "Payment", "fields": [
              {"name": "id", "type": "string"},
              {"name": "account", "type": "string"},
              {"name": "amount", "type": "long"},
              {"name": "merchantId", "type": "string"}]}""";

    public static void main(String[] args) throws Exception {
        Schema v1 = new Schema.Parser().parse(V1), v2 = new Schema.Parser().parse(V2), v3 = new Schema.Parser().parse(V3);

        // the producer's side: a v1 payment, encoded as Avro binary
        GenericRecord payment = new GenericData.Record(v1);
        payment.put("id", "pay-1");
        payment.put("account", "acct-17");
        payment.put("amount", 4000L);
        var out = new ByteArrayOutputStream();
        BinaryEncoder encoder = EncoderFactory.get().binaryEncoder(out, null);
        new GenericDatumWriter<GenericRecord>(v1).write(payment, encoder);
        encoder.flush();
        byte[] avro = out.toByteArray();
        System.out.println("v1 payment as Avro binary, " + avro.length + " bytes: " + HexFormat.ofDelimiter(" ").formatHex(avro));

        // what a registry-aware serializer sends: magic byte 0, the schema id (say 1) as 4 bytes, then the Avro bytes
        byte[] framed = ByteBuffer.allocate(5 + avro.length).put((byte) 0).putInt(1).put(avro).array();
        System.out.println("with the 5-byte registry prefix, " + framed.length + " bytes: " + HexFormat.ofDelimiter(" ").formatHex(framed, 0, 5) + " | ...");

        // the consumer's side: the writer schema comes with the data (by id), the reader schema is the consumer's own
        for (var reader : new Schema[]{v1, v2, v3}) {
            String name = reader == v1 ? "v1" : reader == v2 ? "v2" : "v3";
            try {
                var decoder = DecoderFactory.get().binaryDecoder(avro, null);
                GenericRecord read = new GenericDatumReader<GenericRecord>(v1, reader).read(null, decoder);
                System.out.println("reader " + name + " reads it: " + read);
            } catch (Exception e) {
                System.out.println("reader " + name + " fails:    " + e.getClass().getSimpleName() + ": " + e.getMessage());
            }
        }
        // Avro's own check, the one a registry runs before it accepts a new version
        System.out.println("can v2 read v1 data? " + SchemaCompatibility.checkReaderWriterCompatibility(v2, v1).getType());
        System.out.println("can v3 read v1 data? " + SchemaCompatibility.checkReaderWriterCompatibility(v3, v1).getType());
    }
}
