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

data class ChargeResult(val reply: ChargeReply, val attempts: Int)

class ChargeClient(
    private val channel: Channel,
    private val deadline: Duration = Duration.ofMillis(200),
    private val maxAttempts: Int = 4,
    private val backoff: Duration = Duration.ofMillis(10),
    private val newKey: () -> String = { UUID.randomUUID().toString() },
) {
    companion object {
        val RETRYABLE: Set<Status.Code> = setOf(Status.Code.UNAVAILABLE, Status.Code.DEADLINE_EXCEEDED)
    }

    fun charge(paymentId: String, amountCents: Long): ChargeResult {
        // one key for the payment, made before the first attempt: every retry carries it
        val request = ChargeRequest(paymentId, amountCents, newKey())
        var attempt = 0
        while (true) {
            attempt++
            // a fresh deadline per attempt; without one, a lost reply means waiting forever
            val options = CallOptions.DEFAULT.withDeadlineAfter(deadline.toMillis(), TimeUnit.MILLISECONDS)
            try {
                return ChargeResult(ClientCalls.blockingUnaryCall(channel, ChargeRpc.CHARGE, options, request), attempt)
            } catch (e: StatusRuntimeException) {
                // a rejected request comes back the same every time; and every retry has a limit
                if (e.status.code !in RETRYABLE || attempt >= maxAttempts) throw e
                val ceiling = backoff.toMillis() shl (attempt - 1)
                Thread.sleep(Random.nextLong(0, ceiling + 1)) // full jitter
            }
        }
    }
}
