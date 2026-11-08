package sfz.enc.l02.demo

import com.google.protobuf.CodedInputStream
import com.google.protobuf.CodedOutputStream
import com.google.protobuf.WireFormat
import sfz.enc.l02.demo.DemoSchemas.hex

/** Encodes the authorization with protobuf-java and walks the bytes field by field. */
fun main() {
    val bytes = DemoSchemas.build(DemoSchemas.v1, DemoSchemas.sample).toByteArray()
    println("Protobuf: ${bytes.size} bytes")
    println(hex(bytes))
    println()

    // walk the bytes the way any reader does: key, then a value whose size the wire type tells
    val input = CodedInputStream.newInstance(bytes)
    while (!input.isAtEnd) {
        val start = input.totalBytesRead
        val key = input.readTag()
        val field = WireFormat.getTagFieldNumber(key)
        val type = WireFormat.getTagWireType(key)
        val value = when (type) {
            WireFormat.WIRETYPE_VARINT -> input.readInt64().toString()
            WireFormat.WIRETYPE_LENGTH_DELIMITED -> "\"" + input.readStringRequireUtf8() + "\""
            else -> { input.skipField(key); "(skipped)" }
        }
        val raw = bytes.copyOfRange(start, input.totalBytesRead)
        println("key %02x = field %d, wire type %d  %-24s %s".format(key, field, type, value, hex(raw)))
    }
    println()

    // the cost of a number depends on its type, not just its value
    val id = 1849204436731904017L
    println("payment id as int64:   ${CodedOutputStream.computeInt64Size(1, id)} bytes with its key")
    println("payment id as fixed64: ${CodedOutputStream.computeFixed64Size(1, id)} bytes with its key")
    println("-1 as int64:           ${CodedOutputStream.computeInt64Size(3, -1)} bytes with its key")
    println("-1 as sint64:          ${CodedOutputStream.computeSInt64Size(3, -1)} bytes with its key")
}
