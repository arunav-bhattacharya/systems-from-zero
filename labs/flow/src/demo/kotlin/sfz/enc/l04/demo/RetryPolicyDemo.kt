package sfz.enc.l04.demo

import io.grpc.CallOptions
import io.grpc.ServerServiceDefinition
import io.grpc.Status
import io.grpc.netty.shaded.io.grpc.netty.NettyChannelBuilder
import io.grpc.netty.shaded.io.grpc.netty.NettyServerBuilder
import io.grpc.stub.ServerCalls
import java.net.InetSocketAddress
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/**
 * gRPC's own retry policy, set in the channel's service config. The server loses the reply to every
 * first attempt after charging. The channel retries by itself; the application never sees the failure.
 */
fun main() {
    val charge = method("payments.v1.Charges", "Charge")
    val arrived = AtomicInteger()
    val charged = AtomicInteger()
    val def = ServerServiceDefinition.builder(charge.serviceName!!).addMethod(charge, ServerCalls.asyncUnaryCall { req, reply ->
        val n = arrived.incrementAndGet()
        charged.incrementAndGet() // this server has no key store: every arrival charges
        if (n % 2 == 1) reply.onError(Status.UNAVAILABLE.withDescription("reply lost").asRuntimeException())
        else { reply.onNext("ch_$n"); reply.onCompleted() }
    }).build()
    val server = NettyServerBuilder.forAddress(InetSocketAddress("127.0.0.1", 0)).addService(def).build().start()

    // 1. the policy: which method, how many attempts in all, the backoff, and which codes to retry
    val serviceConfig = mapOf(
        "methodConfig" to listOf(
            mapOf(
                "name" to listOf(mapOf("service" to "payments.v1.Charges", "method" to "Charge")),
                "retryPolicy" to mapOf(
                    "maxAttempts" to 4.0, // the JSON numbers of a service config are doubles
                    "initialBackoff" to "0.05s",
                    "maxBackoff" to "1s",
                    "backoffMultiplier" to 2.0,
                    "retryableStatusCodes" to listOf("UNAVAILABLE"),
                ),
            ),
        ),
    )
    // 2. the channel uses it
    val channel = NettyChannelBuilder.forAddress("127.0.0.1", server.port).usePlaintext()
        .defaultServiceConfig(serviceConfig)
        .enableRetry()
        .build()

    // 3. one deadline for the whole call, retries included
    repeat(5) { i ->
        val reply = call(channel, charge, "pay-$i", CallOptions.DEFAULT.withDeadlineAfter(2, TimeUnit.SECONDS))
        println("pay-$i -> $reply")
    }
    println("requests that arrived: ${arrived.get()}, cards charged: ${charged.get()} for 5 payments")
    channel.shutdownNow(); server.shutdownNow()
}
