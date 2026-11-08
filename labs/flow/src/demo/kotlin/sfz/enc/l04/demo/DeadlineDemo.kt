package sfz.enc.l04.demo

import io.grpc.CallOptions
import io.grpc.Context
import io.grpc.StatusRuntimeException
import io.grpc.inprocess.InProcessChannelBuilder
import io.grpc.inprocess.InProcessServerBuilder
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * checkout -> payments -> issuer. The checkout sets a 300 ms deadline. Payments spends 120 ms on its own work,
 * then calls the issuer without setting any deadline. The issuer takes 500 ms. Who notices what, and when?
 */

private fun millisLeft(): String =
    Context.current().deadline?.let { "${it.timeRemaining(TimeUnit.MILLISECONDS)} ms left" } ?: "no deadline"

private fun since(t0: Long) = (System.nanoTime() - t0) / 1_000_000

fun main() {
    val pool = Executors.newCachedThreadPool()
    var t0 = System.nanoTime()

    // the issuer: slow today
    val authorize = method("issuer.v1.Cards", "Authorize")
    val issuerName = InProcessServerBuilder.generateName()
    val issuer = InProcessServerBuilder.forName(issuerName).executor(pool).addService(service(authorize) { request ->
        if (request == "warm-up") return@service "ok"
        println("%4d ms  issuer   got %s, %s".format(since(t0), request, millisLeft()))
        val ctx = Context.current()
        repeat(50) { if (!ctx.isCancelled) Thread.sleep(10) }
        println("%4d ms  issuer   %s".format(since(t0), if (ctx.isCancelled) "sees the call cancelled, stops" else "done"))
        "approved"
    }).build().start()
    val toIssuer = InProcessChannelBuilder.forName(issuerName).executor(pool).build()

    // payments: 120 ms of its own work, then the issuer, with no deadline of its own
    val charge = method("payments.v1.Charges", "Charge")
    val paymentsName = InProcessServerBuilder.generateName()
    val payments = InProcessServerBuilder.forName(paymentsName).executor(pool).addService(service(charge) { request ->
        if (request == "warm-up") return@service call(toIssuer, authorize, request)
        println("%4d ms  payments got %s, %s".format(since(t0), request, millisLeft()))
        Thread.sleep(120)
        try {
            call(toIssuer, authorize, request) // grpc-java passes the remaining deadline on by itself
        } catch (e: StatusRuntimeException) {
            println("%4d ms  payments issuer call ended: %s".format(since(t0), e.status.code))
            throw e
        }
    }).build().start()
    val toPayments = InProcessChannelBuilder.forName(paymentsName).build()

    call(toPayments, charge, "warm-up") // load the classes and open the channels first
    t0 = System.nanoTime()
    println("%4d ms  checkout calls payments with a 300 ms deadline".format(since(t0)))
    try {
        call(toPayments, charge, "pay-1", CallOptions.DEFAULT.withDeadlineAfter(300, TimeUnit.MILLISECONDS))
    } catch (e: StatusRuntimeException) {
        println("%4d ms  checkout gets %s".format(since(t0), e.status.code))
    }
    Thread.sleep(150) // let the issuer print what it saw

    toIssuer.shutdownNow(); toPayments.shutdownNow(); issuer.shutdownNow(); payments.shutdownNow(); pool.shutdownNow()
}
