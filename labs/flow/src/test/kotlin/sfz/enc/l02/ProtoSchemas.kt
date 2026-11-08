package sfz.enc.l02

import com.google.protobuf.DescriptorProtos.DescriptorProto
import com.google.protobuf.DescriptorProtos.FieldDescriptorProto
import com.google.protobuf.DescriptorProtos.FileDescriptorProto
import com.google.protobuf.Descriptors
import com.google.protobuf.DynamicMessage

/**
 * The Authorization message built in code, as protoc would from a .proto file, so the tests can let
 * protobuf-java write and read the same bytes as ProtoCodec. No code generation needed.
 */
object ProtoSchemas {
    private fun field(name: String, number: Int, type: FieldDescriptorProto.Type, repeated: Boolean = false) =
        FieldDescriptorProto.newBuilder().setName(name).setNumber(number).setType(type)
            .setLabel(if (repeated) FieldDescriptorProto.Label.LABEL_REPEATED else FieldDescriptorProto.Label.LABEL_OPTIONAL)
            .build()

    private fun message(file: String, extra: List<FieldDescriptorProto>): Descriptors.Descriptor {
        val msg = DescriptorProto.newBuilder().setName("Authorization")
            .addField(field("payment_id", 1, FieldDescriptorProto.Type.TYPE_INT64))
            .addField(field("merchant", 2, FieldDescriptorProto.Type.TYPE_STRING))
            .addField(field("amount_minor", 3, FieldDescriptorProto.Type.TYPE_INT64))
            .addField(field("currency", 4, FieldDescriptorProto.Type.TYPE_STRING))
            .addField(field("tags", 5, FieldDescriptorProto.Type.TYPE_STRING, repeated = true))
            .addAllField(extra)
            .build()
        val proto = FileDescriptorProto.newBuilder().setName(file).setPackage("sfz.payments")
            .setSyntax("proto3").addMessageType(msg).build()
        return Descriptors.FileDescriptor.buildFrom(proto, emptyArray()).findMessageTypeByName("Authorization")
    }

    /** Version 1: the five fields of the lesson. */
    val v1: Descriptors.Descriptor = message("authorization_v1.proto", emptyList())

    /** Version 2 adds `int64 risk_score = 6` and `string device_id = 7`. */
    val v2: Descriptors.Descriptor = message(
        "authorization_v2.proto",
        listOf(
            field("risk_score", 6, FieldDescriptorProto.Type.TYPE_INT64),
            field("device_id", 7, FieldDescriptorProto.Type.TYPE_STRING),
        ),
    )

    /** protobuf-java's encoding of [a], written with the descriptor [d]; [extra] sets fields by name. */
    fun encode(a: Authorization, d: Descriptors.Descriptor = v1, extra: Map<String, Any> = emptyMap()): ByteArray {
        val b = DynamicMessage.newBuilder(d)
        b.setField(d.findFieldByName("payment_id"), a.paymentId)
        b.setField(d.findFieldByName("merchant"), a.merchant)
        b.setField(d.findFieldByName("amount_minor"), a.amountMinor)
        b.setField(d.findFieldByName("currency"), a.currency)
        a.tags.forEach { b.addRepeatedField(d.findFieldByName("tags"), it) }
        extra.forEach { (name, value) -> b.setField(d.findFieldByName(name), value) }
        return b.build().toByteArray()
    }
}
