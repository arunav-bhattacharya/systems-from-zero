package sfz.enc.l04.demo

import io.grpc.ServerServiceDefinition
import io.grpc.Status
import io.grpc.StatusRuntimeException
import io.grpc.inprocess.InProcessChannelBuilder
import io.grpc.inprocess.InProcessServerBuilder
import io.grpc.stub.ServerCalls
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger
import kotlin.random.Random

/**
 * 1,000 payments. For 30% of them the reply to the first attempt is lost after the card was charged.
 * The same server, four client behaviours. The server dedupes on the idempotency key when one arrives.
 */

private enum class Client { NO_RETRY, RETRY_NO_KEY, RETRY_NEW_KEY_EACH_TIME, RETRY_ONE_KEY }

private class Run(val charges: Int, val duplicates: Int, val reportedFailed: Int)

private fun run(mode: Client): Run {
    val unlucky = Random(42).let { rnd -> (1..1000).filter { rnd.nextDouble() < 0.30 }.map { "pay-$it" }.toSet() }
    val charges = ConcurrentHashMap<String, AtomicInteger>()
    val seenKeys = ConcurrentHashMap<String, String>()
    val arrived = ConcurrentHashMap<String, AtomicInteger>()
    val m = method("payments.v1.Charges", "Charge")
    val def = ServerServiceDefinition.builder(m.serviceName!!).addMethod(m, ServerCalls.asyncUnaryCall { req, reply ->
        val (paymentId, key) = req.split("|")
        val attempt = arrived.computeIfAbsent(paymentId) { AtomicInteger() }.incrementAndGet()
        val chargeId = if (key.isNotEmpty() && seenKeys.containsKey(key)) {
            seenKeys.getValue(key) // a replay: no new charge
        } else {
            charges.computeIfAbsent(paymentId) { AtomicInteger() }.incrementAndGet()
            "ch_$paymentId".also { if (key.isNotEmpty()) seenKeys[key] = it }
        }
        if (attempt == 1 && paymentId in unlucky) {
            reply.onError(Status.UNAVAILABLE.withDescription("reply lost").asRuntimeException())
        } else {
            reply.onNext(chargeId); reply.onCompleted()
        }
    }).build()
    val name = InProcessServerBuilder.generateName()
    val server = InProcessServerBuilder.forName(name).directExecutor().addService(def).build().start()
    val channel = InProcessChannelBuilder.forName(name).directExecutor().build()

    var failed = 0
    for (i in 1..1000) {
        val paymentId = "pay-$i"
        val oneKey = UUID.randomUUID().toString()
        var done = false
        for (attempt in 1..(if (mode == Client.NO_RETRY) 1 else 3)) {
            val key = when (mode) {
                Client.RETRY_ONE_KEY -> oneKey
                Client.RETRY_NEW_KEY_EACH_TIME -> UUID.randomUUID().toString()
                else -> ""
            }
            try { call(channel, m, "$paymentId|$key"); done = true; break } catch (e: StatusRuntimeException) { }
        }
        if (!done) failed++
    }
    channel.shutdownNow(); server.shutdownNow()
    val total = charges.values.sumOf { it.get() }
    return Run(total, total - charges.size, failed)
}

fun main() {
    println("%-26s %8s %11s %16s".format("client", "charges", "duplicates", "reported failed"))
    for (mode in Client.entries) {
        val r = run(mode)
        println("%-26s %8d %11d %16d".format(mode.name.lowercase().replace('_', ' '), r.charges, r.duplicates, r.reportedFailed))
    }
}
