package sfz.enc.l02.demo

import com.google.protobuf.DescriptorProtos.DescriptorProto
import com.google.protobuf.DescriptorProtos.FieldDescriptorProto
import com.google.protobuf.DescriptorProtos.FieldDescriptorProto.Type
import com.google.protobuf.DescriptorProtos.FileDescriptorProto
import com.google.protobuf.Descriptors
import com.google.protobuf.DynamicMessage

/** The Authorization message built in code, the way protoc would build it from a .proto file. */
object DemoSchemas {
    fun field(name: String, number: Int, type: Type, repeated: Boolean = false): FieldDescriptorProto =
        FieldDescriptorProto.newBuilder().setName(name).setNumber(number).setType(type)
            .setLabel(if (repeated) FieldDescriptorProto.Label.LABEL_REPEATED else FieldDescriptorProto.Label.LABEL_OPTIONAL)
            .build()

    fun message(file: String, fields: List<FieldDescriptorProto>): Descriptors.Descriptor {
        val msg = DescriptorProto.newBuilder().setName("Authorization").addAllField(fields).build()
        val proto = FileDescriptorProto.newBuilder().setName(file).setPackage("sfz.payments")
            .setSyntax("proto3").addMessageType(msg).build()
        return Descriptors.FileDescriptor.buildFrom(proto, emptyArray()).findMessageTypeByName("Authorization")
    }

    val base = listOf(
        field("payment_id", 1, Type.TYPE_INT64),
        field("merchant", 2, Type.TYPE_STRING),
        field("amount_minor", 3, Type.TYPE_INT64),
        field("currency", 4, Type.TYPE_STRING),
        field("tags", 5, Type.TYPE_STRING, repeated = true),
    )

    /** syntax = "proto3"; message Authorization { int64 payment_id = 1; ... repeated string tags = 5; } */
    val v1 = message("authorization_v1.proto", base)

    /** v2 adds int64 risk_score = 6. */
    val v2 = message("authorization_v2.proto", base + field("risk_score", 6, Type.TYPE_INT64))

    fun build(d: Descriptors.Descriptor, values: Map<String, Any>): DynamicMessage {
        val b = DynamicMessage.newBuilder(d)
        for ((name, v) in values) {
            val f = d.findFieldByName(name)
            if (v is List<*>) v.forEach { b.addRepeatedField(f, it) } else b.setField(f, v)
        }
        return b.build()
    }

    val sample = mapOf(
        "payment_id" to 1849204436731904017L, "merchant" to "Fern Bakery", "amount_minor" to 4000L,
        "currency" to "EUR", "tags" to listOf("card", "3ds"),
    )

    fun hex(b: ByteArray) = b.joinToString(" ") { "%02x".format(it) }
}
