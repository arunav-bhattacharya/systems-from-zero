package sfz.enc.l02.demo

import com.google.protobuf.DescriptorProtos.FieldDescriptorProto.Type
import com.google.protobuf.DiscardUnknownFieldsParser
import com.google.protobuf.DynamicMessage
import sfz.enc.l02.demo.DemoSchemas.hex

/** What old code does with a field it has never heard of, and what a reused field number does. */
fun main() {
    val v1 = DemoSchemas.v1
    val v2 = DemoSchemas.v2

    // a v2 service writes an authorization with the new field
    val fromV2 = DemoSchemas.build(v2, DemoSchemas.sample + ("risk_score" to 87L)).toByteArray()
    println("v2 wrote ${fromV2.size} bytes, ending in ${hex(fromV2.copyOfRange(fromV2.size - 2, fromV2.size))}")

    // a v1 service reads it, changes the amount and writes it back
    val read = DynamicMessage.parseFrom(v1, fromV2)
    println("v1 sees unknown fields: ${read.unknownFields.asMap().keys}")
    val updated = read.toBuilder().setField(v1.findFieldByName("amount_minor"), 4500L).build().toByteArray()
    val back = DynamicMessage.parseFrom(v2, updated)
    println("after v1's update, v2 reads risk_score = ${back.getField(v2.findFieldByName("risk_score"))}")

    // the same with a parser that throws unknown fields away (what proto3 did before 3.5.0)
    val discarding = DiscardUnknownFieldsParser.wrap(DynamicMessage.getDefaultInstance(v1).parserForType)
    val lossy = discarding.parseFrom(fromV2).toBuilder()
        .setField(v1.findFieldByName("amount_minor"), 4500L).build().toByteArray()
    println("with DiscardUnknownFieldsParser, v2 reads risk_score = " +
        DynamicMessage.parseFrom(v2, lossy).getField(v2.findFieldByName("risk_score")))

    // v3 deletes amount_minor and reuses number 3 for a new field, fee_minor
    val v3 = DemoSchemas.message(
        "authorization_v3.proto",
        DemoSchemas.base.filter { it.number != 3 } + DemoSchemas.field("fee_minor", 3, Type.TYPE_INT64) +
            DemoSchemas.field("amount_minor", 8, Type.TYPE_INT64),
    )
    val fromV3 = DemoSchemas.build(v3, DemoSchemas.sample + ("fee_minor" to 150L)).toByteArray()
    val misread = DynamicMessage.parseFrom(v1, fromV3)
    println("v3 wrote amount 4000 and fee 150; v1 reads amount_minor = " +
        misread.getField(v1.findFieldByName("amount_minor")))
}
