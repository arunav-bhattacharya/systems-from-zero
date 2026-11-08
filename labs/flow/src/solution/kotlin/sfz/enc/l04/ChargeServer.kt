package sfz.enc.l04

import io.grpc.Context
import io.grpc.ServerServiceDefinition
import io.grpc.Status
import io.grpc.stub.ServerCalls
import io.grpc.stub.StreamObserver
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger

// Finished: the card issuer, a network that loses or delays replies on purpose, and the gRPC service.
// You don't change this file.

/** The card issuer. Every call to [charge] takes money; it has no idea whether it has seen the request before. */
class Issuer(private val workMillis: Long = 0) {
    private val charges = ConcurrentHashMap<String, AtomicInteger>()
    private val next = AtomicInteger()

    fun charge(r: ChargeRequest): ChargeReply {
        if (workMillis > 0) Thread.sleep(workMillis)
        charges.computeIfAbsent(r.paymentId) { AtomicInteger() }.incrementAndGet()
        return ChargeReply("ch_${next.incrementAndGet()}", r.amountCents)
    }

    /** How many times the card was charged for this payment. More than 1 is a duplicate charge. */
    fun chargesFor(paymentId: String): Int = charges[paymentId]?.get() ?: 0

    fun totalCharges(): Int = charges.values.sumOf { it.get() }
}

/**
 * What the network does to replies. For the payments in [loseReply], the reply to each listed attempt
 * (1 = the first request that arrives for that payment) is lost after the charge went through: the client
 * sees UNAVAILABLE. For the payments in [slowReply], the reply to the first attempt arrives [slowMillis] late.
 */
class Faults(
    val loseReply: Map<String, Set<Int>> = emptyMap(),
    val slowReply: Set<String> = emptySet(),
    val slowMillis: Long = 500,
) {
    companion object {
        val NONE = Faults()
    }
}

/**
 * The `payments.v1.Charges` service. With a [keys] store, a request that carries an idempotency key runs
 * through [IdempotencyStore.once]; without one, every request that arrives charges the card.
 */
class ChargeService(
    private val issuer: Issuer,
    private val keys: IdempotencyStore?,
    private val faults: Faults = Faults.NONE,
) {
    private val arrived = ConcurrentHashMap<String, AtomicInteger>()
    private val keysSeen = ConcurrentHashMap<String, MutableSet<String>>()

    /** How many requests arrived for this payment: first attempt plus retries. */
    fun requestsFor(paymentId: String): Int = arrived[paymentId]?.get() ?: 0

    /** The idempotency keys that arrived for this payment. A good client sends one key, however often it retries. */
    fun keysFor(paymentId: String): Set<String> = keysSeen[paymentId] ?: emptySet()

    fun definition(): ServerServiceDefinition = ServerServiceDefinition.builder(ChargeRpc.SERVICE)
        .addMethod(ChargeRpc.CHARGE, ServerCalls.asyncUnaryCall { request, reply -> handle(request, reply) })
        .build()

    private fun handle(r: ChargeRequest, reply: StreamObserver<ChargeReply>) {
        val attempt = arrived.computeIfAbsent(r.paymentId) { AtomicInteger() }.incrementAndGet()
        keysSeen.computeIfAbsent(r.paymentId) { ConcurrentHashMap.newKeySet() }.add(r.idempotencyKey)
        if (r.amountCents <= 0) {
            reply.onError(Status.INVALID_ARGUMENT.withDescription("amount must be positive").asRuntimeException())
            return
        }
        val result = try {
            if (keys == null || r.idempotencyKey.isEmpty()) {
                issuer.charge(r)
            } else {
                keys.once(r.idempotencyKey, "${r.paymentId}|${r.amountCents}") { issuer.charge(r) }
            }
        } catch (e: KeyReusedException) {
            reply.onError(Status.INVALID_ARGUMENT.withDescription(e.message).asRuntimeException())
            return
        }
        if (attempt in faults.loseReply[r.paymentId].orEmpty()) {
            // the card was charged; the reply dies on the way back
            reply.onError(Status.UNAVAILABLE.withDescription("connection reset before the reply got out").asRuntimeException())
            return
        }
        if (attempt == 1 && r.paymentId in faults.slowReply) Thread.sleep(faults.slowMillis)
        if (Context.current().isCancelled) return // the client's deadline passed; nobody is listening
        reply.onNext(result)
        reply.onCompleted()
    }
}
