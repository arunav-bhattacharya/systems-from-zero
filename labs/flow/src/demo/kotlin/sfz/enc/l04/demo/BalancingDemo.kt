package sfz.enc.l04.demo

import io.grpc.EquivalentAddressGroup
import io.grpc.ManagedChannel
import io.grpc.NameResolver
import io.grpc.NameResolverProvider
import io.grpc.NameResolverRegistry
import io.grpc.netty.shaded.io.grpc.netty.NettyChannelBuilder
import io.grpc.netty.shaded.io.grpc.netty.NettyServerBuilder
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketAddress
import java.net.URI
import java.util.concurrent.atomic.AtomicInteger
import kotlin.concurrent.thread

/**
 * Three replicas of a gRPC service on 127.0.0.1. 300 calls reach them three ways: through an L4 proxy that picks
 * a backend per TCP connection, through the same proxy from three channels, and with client-side round_robin.
 */

/** An L4 load balancer: picks the next backend for each new TCP connection, then only copies bytes. */
class L4Proxy(private val backends: List<Int>) : AutoCloseable {
    private val socket = ServerSocket(0)
    private val next = AtomicInteger()
    val port: Int get() = socket.localPort

    init {
        thread(isDaemon = true) {
            while (!socket.isClosed) {
                val client = try { socket.accept() } catch (e: Exception) { break }
                val backend = Socket("127.0.0.1", backends[next.getAndIncrement() % backends.size])
                pipe(client, backend); pipe(backend, client)
            }
        }
    }

    private fun pipe(from: Socket, to: Socket) = thread(isDaemon = true) {
        try { from.getInputStream().transferTo(to.getOutputStream()) } catch (e: Exception) { }
        runCatching { to.close() }; runCatching { from.close() }
    }

    override fun close() = socket.close()
}

/** A name that resolves to every replica's address, the way a headless Kubernetes Service does in DNS. */
class StaticResolver(private val addresses: List<SocketAddress>) : NameResolverProvider() {
    override fun isAvailable() = true
    override fun priority() = 5
    override fun getDefaultScheme() = "static"
    override fun newNameResolver(targetUri: URI, args: NameResolver.Args): NameResolver? =
        if (targetUri.scheme != "static") null else object : NameResolver() {
            override fun getServiceAuthority() = "charges"
            override fun start(listener: Listener2) {
                listener.onResult(
                    ResolutionResult.newBuilder().setAddressesOrError(
                        io.grpc.StatusOr.fromValue(addresses.map { EquivalentAddressGroup(it) }),
                    ).build(),
                )
            }
            override fun shutdown() {}
        }
}

fun main() {
    val m = method("payments.v1.Charges", "Charge")
    val counts = List(3) { AtomicInteger() }
    val servers = (0..2).map { i ->
        NettyServerBuilder.forAddress(InetSocketAddress("127.0.0.1", 0))
            .addService(service(m) { counts[i].incrementAndGet(); "ok from replica-${i + 1}" })
            .build().start()
    }
    fun report(label: String) {
        println("%-38s %s".format(label, counts.mapIndexed { i, c -> "replica-${i + 1}=${c.getAndSet(0)}" }.joinToString("  ")))
    }
    fun ManagedChannel.send(n: Int) = repeat(n) { call(this, m, "pay-$it") }

    L4Proxy(servers.map { it.port }).use { proxy ->
        val one = NettyChannelBuilder.forAddress("127.0.0.1", proxy.port).usePlaintext().build()
        one.send(300)
        report("one channel through the L4 proxy")
        one.shutdownNow()

        val three = List(3) { NettyChannelBuilder.forAddress("127.0.0.1", proxy.port).usePlaintext().build() }
        three.forEach { it.send(100) }
        report("three channels through the L4 proxy")
        three.forEach { it.shutdownNow() }
    }

    NameResolverRegistry.getDefaultRegistry().register(StaticResolver(servers.map { InetSocketAddress("127.0.0.1", it.port) }))
    val rr = NettyChannelBuilder.forTarget("static:///charges").defaultLoadBalancingPolicy("round_robin").usePlaintext().build()
    rr.send(300)
    report("one channel, client-side round_robin")
    rr.shutdownNow()

    servers.forEach { it.shutdownNow() }
}
