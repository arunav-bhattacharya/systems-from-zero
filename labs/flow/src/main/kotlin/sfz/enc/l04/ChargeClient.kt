package sfz.enc.l04

import io.grpc.CallOptions
import io.grpc.Channel
import io.grpc.Status
import io.grpc.StatusRuntimeException
import io.grpc.stub.ClientCalls
import java.time.Duration
import java.util.UUID
import java.util.concurrent.TimeUnit
import kotlin.random.Random

/** The reply, and how many attempts it took to get it. */
data class ChargeResult(val reply: ChargeReply, val attempts: Int)

/**
 * A client for `payments.v1.Charges/Charge` that survives a network that loses replies.
 *
 * [charge] does this:
 *
 * 1. Make ONE idempotency key for the payment with [newKey], before the first attempt, and send the same
 *    key on every attempt. (A new key per attempt makes every retry look like a new payment.)
 * 2. Give every attempt its own deadline of [deadline]:
 *    `CallOptions.DEFAULT.withDeadlineAfter(deadline.toMillis(), TimeUnit.MILLISECONDS)`.
 *    gRPC sets no deadline unless you do, and a call without one can wait forever.
 * 3. Make the call with `ClientCalls.blockingUnaryCall(channel, ChargeRpc.CHARGE, options, request)`.
 *    A failure arrives as a `StatusRuntimeException`; its `status.code` says what kind.
 * 4. Retry only the codes in [RETRYABLE], at most [maxAttempts] attempts in all, waiting a random time
 *    between 0 and `backoff * 2^(attempt - 1)` milliseconds between attempts (full jitter, as in the
 *    Networking track's lesson on retries). Any other code, or the last failed attempt, throws its exception.
 */
class ChargeClient(
    private val channel: Channel,
    private val deadline: Duration = Duration.ofMillis(200),
    private val maxAttempts: Int = 4,
    private val backoff: Duration = Duration.ofMillis(10),
    private val newKey: () -> String = { UUID.randomUUID().toString() },
) {
    companion object {
        /**
         * The codes worth another attempt. UNAVAILABLE: the request or its reply never made it.
         * DEADLINE_EXCEEDED: no answer in time, the outcome is unknown. Both are safe to retry only
         * because the request carries an idempotency key.
         */
        val RETRYABLE: Set<Status.Code> = setOf(Status.Code.UNAVAILABLE, Status.Code.DEADLINE_EXCEEDED)
    }

    fun charge(paymentId: String, amountCents: Long): ChargeResult {
        TODO("one key, then a loop: a fresh deadline per attempt, retry RETRYABLE codes with backoff, give up after maxAttempts")
    }
}
