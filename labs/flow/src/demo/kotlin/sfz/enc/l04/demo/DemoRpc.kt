package sfz.enc.l04.demo

import io.grpc.CallOptions
import io.grpc.Channel
import io.grpc.MethodDescriptor
import io.grpc.ServerServiceDefinition
import io.grpc.StatusRuntimeException
import io.grpc.stub.ClientCalls
import io.grpc.stub.ServerCalls
import java.io.ByteArrayInputStream
import java.io.InputStream

// Shared by the lesson 4 demos: one unary method whose request and reply are plain UTF-8 strings.
// (The lab encodes real Protobuf messages by hand; a string is enough to measure and route calls.)

object Text : MethodDescriptor.Marshaller<String> {
    override fun stream(value: String): InputStream = ByteArrayInputStream(value.toByteArray())
    override fun parse(stream: InputStream): String = stream.readBytes().decodeToString()
}

fun method(service: String, name: String): MethodDescriptor<String, String> =
    MethodDescriptor.newBuilder(Text, Text)
        .setType(MethodDescriptor.MethodType.UNARY)
        .setFullMethodName(MethodDescriptor.generateFullMethodName(service, name))
        .build()

/** A service with one method that answers every request with [handler]'s result. */
fun service(m: MethodDescriptor<String, String>, handler: (String) -> String): ServerServiceDefinition =
    ServerServiceDefinition.builder(m.serviceName!!)
        .addMethod(m, ServerCalls.asyncUnaryCall { request, reply ->
            try {
                reply.onNext(handler(request))
                reply.onCompleted()
            } catch (e: StatusRuntimeException) {
                reply.onError(e) // pass a failed downstream call on as this call's status
            }
        })
        .build()

fun call(channel: Channel, m: MethodDescriptor<String, String>, request: String, options: CallOptions = CallOptions.DEFAULT): String =
    ClientCalls.blockingUnaryCall(channel, m, options, request)
