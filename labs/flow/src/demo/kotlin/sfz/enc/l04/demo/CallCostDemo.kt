package sfz.enc.l04.demo

import io.grpc.inprocess.InProcessChannelBuilder
import io.grpc.inprocess.InProcessServerBuilder
import io.grpc.netty.shaded.io.grpc.netty.NettyChannelBuilder
import io.grpc.netty.shaded.io.grpc.netty.NettyServerBuilder
import java.net.InetSocketAddress

/**
 * The same "authorize" work three ways: a local function call, a gRPC call inside one JVM
 * (in-process transport, no sockets), and a gRPC call over TCP on 127.0.0.1 (HTTP/2, Netty).
 */

private fun authorize(request: String): String = if (request.length < 64) "approved" else "declined"

private fun percentile(sortedNanos: LongArray, p: Double): Double = sortedNanos[((sortedNanos.size - 1) * p).toInt()] / 1000.0

private fun measure(label: String, n: Int, once: () -> String) {
    repeat(n) { once() } // warm up: let the JIT compile the path, open connections
    val times = LongArray(n)
    for (i in 0 until n) {
        val t0 = System.nanoTime()
        once()
        times[i] = System.nanoTime() - t0
    }
    times.sort()
    println("%-32s median %8.2f us   p99 %8.2f us".format(label, percentile(times, 0.5), percentile(times, 0.99)))
}

fun main() {
    val m = method("payments.v1.Authorizer", "Authorize")

    // 1. a local call: too fast to time one by one, so time 10 million and divide
    val requests = Array(1024) { "pay-$it" }
    var sink = 0
    repeat(10_000_000) { sink += authorize(requests[it and 1023]).length } // warm up
    val t0 = System.nanoTime()
    repeat(10_000_000) { sink += authorize(requests[it and 1023]).length }
    val perCallNanos = (System.nanoTime() - t0) / 10_000_000.0
    if (sink == -1) println("unreachable") // uses sink, so the JIT can't throw the loop away
    println("%-32s about %.1f ns per call".format("local function call", perCallNanos))

    // 2. gRPC inside one JVM: encoding, the gRPC call machinery and a thread hop, but no network
    val name = InProcessServerBuilder.generateName()
    val inProc = InProcessServerBuilder.forName(name).addService(service(m, ::authorize)).build().start()
    val inProcChannel = InProcessChannelBuilder.forName(name).build()
    measure("gRPC, in-process transport", 20_000) { call(inProcChannel, m, "pay-1") }

    // 3. gRPC over TCP on loopback: HTTP/2 frames through the kernel's network stack
    val tcp = NettyServerBuilder.forAddress(InetSocketAddress("127.0.0.1", 0)).addService(service(m, ::authorize)).build().start()
    val tcpChannel = NettyChannelBuilder.forAddress("127.0.0.1", tcp.port).usePlaintext().build()
    measure("gRPC, HTTP/2 over 127.0.0.1", 20_000) { call(tcpChannel, m, "pay-1") }

    inProcChannel.shutdownNow(); tcpChannel.shutdownNow(); inProc.shutdownNow(); tcp.shutdownNow()
}
