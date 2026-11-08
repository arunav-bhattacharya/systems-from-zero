package sfz.enc.l04

import com.google.protobuf.CodedInputStream
import com.google.protobuf.CodedOutputStream
import io.grpc.MethodDescriptor
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.InputStream

// Finished: the contract of one gRPC method, written by hand instead of generated from a .proto file.
// You don't change this file. In a .proto file it would read:
//
//   package payments.v1;
//   service Charges { rpc Charge(ChargeRequest) returns (ChargeReply); }
//   message ChargeRequest { string payment_id = 1; int64 amount_cents = 2; string idempotency_key = 3; }
//   message ChargeReply   { string charge_id = 1; int64 amount_cents = 2; }

data class ChargeRequest(val paymentId: String, val amountCents: Long, val idempotencyKey: String = "")

data class ChargeReply(val chargeId: String, val amountCents: Long)

/** Protobuf encoding by hand (lesson 2 of this track): a tag per field, then the value. Unknown tags are skipped. */
object Wire {
    fun encode(r: ChargeRequest): ByteArray = bytes { out ->
        out.writeString(1, r.paymentId)
        out.writeInt64(2, r.amountCents)
        if (r.idempotencyKey.isNotEmpty()) out.writeString(3, r.idempotencyKey)
    }

    fun encode(r: ChargeReply): ByteArray = bytes { out ->
        out.writeString(1, r.chargeId)
        out.writeInt64(2, r.amountCents)
    }

    fun decodeRequest(input: InputStream): ChargeRequest {
        val cin = CodedInputStream.newInstance(input)
        var id = ""; var cents = 0L; var key = ""
        while (true) {
            when (val tag = cin.readTag()) {
                0 -> return ChargeRequest(id, cents, key)
                (1 shl 3) or 2 -> id = cin.readString()
                (2 shl 3) or 0 -> cents = cin.readInt64()
                (3 shl 3) or 2 -> key = cin.readString()
                else -> cin.skipField(tag)
            }
        }
    }

    fun decodeReply(input: InputStream): ChargeReply {
        val cin = CodedInputStream.newInstance(input)
        var id = ""; var cents = 0L
        while (true) {
            when (val tag = cin.readTag()) {
                0 -> return ChargeReply(id, cents)
                (1 shl 3) or 2 -> id = cin.readString()
                (2 shl 3) or 0 -> cents = cin.readInt64()
                else -> cin.skipField(tag)
            }
        }
    }

    private fun bytes(write: (CodedOutputStream) -> Unit): ByteArray {
        val buffer = ByteArrayOutputStream()
        val out = CodedOutputStream.newInstance(buffer)
        write(out)
        out.flush()
        return buffer.toByteArray()
    }
}

object ChargeRpc {
    const val SERVICE = "payments.v1.Charges"

    private val requests = object : MethodDescriptor.Marshaller<ChargeRequest> {
        override fun stream(value: ChargeRequest): InputStream = ByteArrayInputStream(Wire.encode(value))
        override fun parse(stream: InputStream): ChargeRequest = Wire.decodeRequest(stream)
    }
    private val replies = object : MethodDescriptor.Marshaller<ChargeReply> {
        override fun stream(value: ChargeReply): InputStream = ByteArrayInputStream(Wire.encode(value))
        override fun parse(stream: InputStream): ChargeReply = Wire.decodeReply(stream)
    }

    /** One unary method. On the wire it is an HTTP/2 POST to `/payments.v1.Charges/Charge`. */
    val CHARGE: MethodDescriptor<ChargeRequest, ChargeReply> = MethodDescriptor.newBuilder(requests, replies)
        .setType(MethodDescriptor.MethodType.UNARY)
        .setFullMethodName(MethodDescriptor.generateFullMethodName(SERVICE, "Charge"))
        .build()
}
